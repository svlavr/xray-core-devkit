"""Exercise real stdio reuse, generation changes, failure and process cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import time
import threading
from contextlib import ExitStack

from mcp_backend import Backend, PersistentBackend
from resource_guard import CancelledError


class PersistentTests(unittest.TestCase):
    def test_cancelled_call_reaps_its_generation_and_preserves_peer(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
            script=Path(directory)/'cancel-server.py'
            script.write_text('''import sys,json,os,time
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m:continue
 if m.get('method')=='blocked':
  print(json.dumps({'method':'started','params':{'pid':os.getpid()}}),flush=True)
  time.sleep(60)
 print(json.dumps({'id':m['id'],'result':{'pid':os.getpid()}}),flush=True)
''')
            started=threading.Event();cancelled=threading.Event();children=[]
            def factory(key,deadline=None,cancelled=None):
                backend=Backend([sys.executable,str(script)],directory,os.environ.copy(),
                    subprocess.DEVNULL,deadline=deadline,cancelled=cancelled,
                    notify=lambda message:started.set())
                children.append(backend.proc)
                return backend
            session=PersistentBackend(factory,deadline_factory=True)
            cleanup.callback(session.close)
            peer=Backend([sys.executable,str(script)],directory,os.environ.copy(),subprocess.DEVNULL)
            cleanup.callback(peer.close)
            peer_pid=peer.call({'id':1,'method':'ping'})['result']['pid']
            def cancel():
                if started.wait(4):cancelled.set()
            threading.Thread(target=cancel,daemon=True).start()
            tick=time.monotonic()
            with self.assertRaises(CancelledError):
                session.call('one',{'id':2,'method':'blocked'},cancelled=cancelled)
            self.assertLess(time.monotonic()-tick,3)
            self.assertIsNone(session.backend)
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(peer.call({'id':3,'method':'ping'})['result']['pid'],peer_pid)
            fresh=session.call('one',{'id':4,'method':'ping'})['result']['pid']
            self.assertNotEqual(fresh,peer_pid)
            self.assertEqual(len(children),2)

    def test_expired_initialization_budget_reaps_new_child(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TimeoutError,'already expired'):
                Backend([sys.executable,'-c','import time;time.sleep(60)'],directory,
                    os.environ.copy(),subprocess.DEVNULL,timeout=10,deadline=time.monotonic()-1)

    def test_generation_reuses_process_and_closes_replaced_process(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'server.py'
            script.write_text('''import sys,json,os
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m:continue
 if m['method']=='fail':sys.exit(2)
 print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'pid':os.getpid()}}),flush=True)
''', encoding='utf-8')
            children = []
            def factory(key):
                child = Backend([sys.executable, str(script)], directory,
                                os.environ.copy(), subprocess.DEVNULL, timeout=2)
                children.append(child.proc)
                return child
            session = PersistentBackend(factory)
            self.addCleanup(session.close)
            request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}
            first = session.call('a', request)
            self.assertEqual(first, session.call('a', request))
            self.assertEqual(len(children), 1)
            second = session.call('b', request)
            self.assertNotEqual(first['result']['pid'], second['result']['pid'])
            self.assertIsNotNone(children[0].poll())
            with self.assertRaisesRegex(RuntimeError, 'exited'):
                session.call('b', {**request, 'method': 'fail'})
            self.assertIsNone(session.backend)
            self.assertEqual(len(children), 2)
            session.call('b', request)
            session.close()
            self.assertEqual(len(children), 3)
            self.assertTrue(all(p.poll() is not None for p in children))


if __name__ == '__main__':
    unittest.main()

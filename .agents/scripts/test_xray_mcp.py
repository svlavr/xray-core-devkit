"""Real stdio gateway regressions with fake graph work, never live indexing."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import resource_guard as guard
from test_resource_guard import gone


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def launch(self,mode='normal',budget=45,delay=0,queue_budget=60,retire=15):
        cli=self.root/'gitnexus/node_modules/gitnexus/dist/cli/index.js'
        cli.parent.mkdir(parents=True)
        cli.write_text('''import sys,json,time,os
for line in sys.stdin:
 m=json.loads(line);method=m.get('method')
 if 'id' not in m:continue
 if method in ('initialize','tools/list'):time.sleep(DELAY)
 if method=='initialize':result={'pid':os.getpid(),'capabilities':{'tools':{'listChanged':True}}}
 elif method=='tools/list':result={'tools':[{'name':'query'}]}
 else:
  if m.get('params',{}).get('name')=='blocked':
   print(json.dumps({'method':'work-started','params':{'pid':os.getpid(),'id':m['id']}}),flush=True)
   time.sleep(60)
  print(json.dumps({'method':'notifications/tools/list_changed'}),flush=True)
  result={'pid':os.getpid(),'content':[{'type':'text','text':'answer'}]}
 print(json.dumps({'id':m['id'],'result':result}),flush=True)
'''.replace('DELAY',repr(delay)))
        adapter=self.root/'.agents/scripts/go_mcp.py';adapter.parent.mkdir(parents=True)
        adapter.write_text("import os,time,pathlib;pathlib.Path("+repr(str(self.root/'adapter-pid'))+").write_text(str(os.getpid()));time.sleep(60)")
        launcher=self.root/'launcher.py'
        launcher.write_text('''import sys,os,time,pathlib,json
sys.path.insert(0,SCRIPTS)
import xray_mcp as gateway
from resource_guard import check_cancelled
root=pathlib.Path(__ROOT__)
gateway.ROOT=root;gateway.TOOLS=root;gateway.node_executable=lambda:sys.executable
gateway.cache_root=lambda:root/'cache'
gateway.STARTUP_SECONDS=BUDGET
gateway.REQUEST_SECONDS=__QUEUE_TIMEOUT__
gateway.CANCEL_RETIRE_SECONDS=__RETIRE_TIMEOUT__
state={'repo':str(root),'head':'test-head','fingerprint':'test-fingerprint','coverage':'test','dirty':''}
manifest={**state,'registry_home':str(root/'registry'),'index':str(root/'index')}
def source(deadline=None,**kwargs):
 time.sleep(SOURCE_DELAY)
 gateway.remaining(deadline,'test source validation')
 return state
calls=0
def status(deadline=None,cancelled=None):
 global calls
 calls+=1;check_cancelled(cancelled)
 if MODE=='unresponsive' and calls>1:
  (root/'validation-started').write_text('started')
  time.sleep(60)
 if MODE=='bad_status' and calls==2:raise ValueError('bad manifest')
 if MODE=='refresh' and calls>1:return {'status':'MISSING','source':state}
 return {'status':'CURRENT','source':state,'manifest':manifest}
def refresh(deadline=None,cancelled=None):
 (root/'refresh-started').write_text('started')
 cancelled.wait(60);check_cancelled(cancelled)
 raise RuntimeError('cancel was not delivered')
gateway.source_state=source;gateway.graph_status=status;gateway.refresh_graph=refresh
gateway.main(['gopls' if MODE=='gopls' else 'gitnexus'])
'''.replace('SCRIPTS',repr(str(Path(guard.__file__).parent)))
            .replace('__ROOT__',repr(str(self.root)))
            .replace('BUDGET',repr(budget)).replace('SOURCE_DELAY',repr(delay))
            .replace('__QUEUE_TIMEOUT__',repr(queue_budget)).replace('__RETIRE_TIMEOUT__',repr(retire))
            .replace('MODE',repr(mode)))
        log=(self.root/'stderr.log').open('w');self.addCleanup(log.close)
        process=guard.ManagedProcess([sys.executable,str(launcher)],cwd=self.root,
            transient=self.root/'transient',stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=log,text=True,encoding='utf-8',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        inbox=queue.Queue()
        def read():
            for line in process.stdout:inbox.put(json.loads(line))
            inbox.put(None)
        threading.Thread(target=read,daemon=True).start()
        def cleanup():
            guard.stop(process);process.stdin.close();process.stdout.close()
        self.addCleanup(cleanup)
        self.process=process;self.inbox=inbox
        return process

    def send(self,message):self.process.stdin.write(json.dumps(message)+'\n');self.process.stdin.flush()

    def response(self,id,timeout=4):
        deadline=time.monotonic()+timeout
        while True:
            message=self.inbox.get(timeout=max(.001,deadline-time.monotonic()))
            if message is None:self.fail('Frontend exited: '+(self.root/'stderr.log').read_text())
            if message.get('id')==id:return message

    def initialize(self):
        self.send({'id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}})
        self.initial=self.response(1)
        self.assertIn('result',self.initial)
        self.send({'method':'notifications/initialized'})

    def test_exact_active_and_queued_cancel_preserve_reuse_and_notifications(self):
        self.launch();self.initialize()
        self.send({'id':2,'method':'tools/call','params':{'name':'blocked'}})
        while True:
            message=self.inbox.get(timeout=4)
            if message.get('method')=='work-started':old_pid=message['params']['pid'];break
        self.send({'method':'notifications/cancelled','params':{'requestId':999}})
        self.send({'id':90,'method':'ping'})
        self.assertEqual(self.response(90)['result'],{})
        self.assertFalse(gone(old_pid))
        self.send({'id':3,'method':'tools/call','params':{'name':'query'}})
        self.send({'method':'notifications/cancelled','params':{'requestId':3}})
        self.assertEqual(self.response(3)['error']['code'],-32800)
        self.assertFalse(gone(old_pid))
        tick=time.monotonic()
        self.send({'method':'notifications/cancelled','params':{'requestId':2}})
        self.assertEqual(self.response(2)['error']['code'],-32800)
        self.assertLess(time.monotonic()-tick,1)
        self.send({'id':4,'method':'tools/call','params':{'name':'query'}})
        answer=self.response(4)['result'];self.assertNotEqual(answer['pid'],old_pid)
        self.assertTrue(gone(old_pid))
        self.assertIn('xray_provenance',answer['content'][-1]['text'])
        self.send({'method':'notifications/cancelled','params':{'requestId':2}})
        self.send({'id':5,'method':'tools/call','params':{'name':'query'}})
        self.assertEqual(self.response(5)['result']['pid'],answer['pid'])
        self.send({'id':6,'method':'tools/list'})
        self.assertTrue(self.response(6)['result']['tools'][0]['annotations']['readOnlyHint'])

    def test_refresh_cancellation_reaches_only_active_operation(self):
        self.launch(mode='refresh');self.initialize()
        self.send({'id':2,'method':'tools/call','params':{'name':'query'}})
        deadline=time.monotonic()+4
        while not (self.root/'refresh-started').exists():
            if time.monotonic()>deadline:self.fail('Fake refresh did not start')
            time.sleep(.01)
        self.send({'method':'notifications/cancelled','params':{'requestId':2}})
        self.assertEqual(self.response(2)['error']['code'],-32800)
        self.send({'id':3,'method':'ping'})
        self.assertEqual(self.response(3)['result'],{})

    def test_queued_request_expires_while_active_operation_keeps_running(self):
        self.launch(queue_budget=.3);self.initialize()
        self.send({'id':2,'method':'tools/call','params':{'name':'blocked'}})
        while True:
            message=self.inbox.get(timeout=4)
            if message.get('method')=='work-started':pid=message['params']['pid'];break
        tick=time.monotonic()
        self.send({'id':3,'method':'tools/list','params':{'cursor':'uncached-page'}})
        answer=self.response(3)
        self.assertIn('while queued',answer['error']['message'])
        self.assertLess(time.monotonic()-tick,1)
        self.assertFalse(gone(pid))
        self.send({'method':'notifications/cancelled','params':{'requestId':2}})
        self.assertEqual(self.response(2)['error']['code'],-32800)
        self.send({'id':4,'method':'tools/call','params':{'name':'query'}})
        self.assertIn('result',self.response(4))

    def test_uncooperative_cancel_retires_only_owned_frontend_and_children(self):
        self.launch(mode='unresponsive',retire=.3);self.initialize()
        backend_pid=self.initial['result']['pid']
        peer=guard.ManagedProcess([sys.executable,'-c','import time;time.sleep(60)'],
            cwd=self.root,transient=self.root/'peer-transient',
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda:guard.stop(peer))
        self.send({'id':2,'method':'tools/call','params':{'name':'query'}})
        deadline=time.monotonic()+4
        while not (self.root/'validation-started').exists():
            if time.monotonic()>deadline:self.fail('Uncooperative fake validation did not start')
            time.sleep(.01)
        tick=time.monotonic()
        self.send({'method':'notifications/cancelled','params':{'requestId':2}})
        self.assertEqual(self.response(2)['error']['code'],-32800)
        self.process.wait(timeout=3)
        self.assertEqual(self.process.returncode,124)
        self.assertLess(time.monotonic()-tick,2)
        deadline=time.monotonic()+3
        while not gone(backend_pid):
            if time.monotonic()>deadline:self.fail('Owned backend survived frontend retirement')
            time.sleep(.02)
        self.assertIsNone(peer.poll())

    def test_unexpected_operation_error_releases_worker_slot(self):
        self.launch(mode='bad_status');self.initialize()
        self.send({'id':2,'method':'tools/call','params':{'name':'query'}})
        self.assertEqual(self.response(2)['error']['code'],-32603)
        self.send({'id':3,'method':'tools/call','params':{'name':'query'}})
        self.assertIn('result',self.response(3))

    def test_source_backend_and_catalogue_share_startup_budget(self):
        tick=time.monotonic()
        self.launch(budget=1.2,delay=.5)
        self.send({'id':1,'method':'initialize','params':{}})
        self.process.wait(timeout=4)
        self.assertLess(time.monotonic()-tick,2.5)
        self.assertNotEqual(self.process.returncode,0)

    def test_startup_watchdog_bounds_nested_gopls_adapter(self):
        self.launch(mode='gopls',budget=1.0)
        self.send({'id':1,'method':'initialize','params':{}})
        self.process.wait(timeout=4)
        self.assertEqual(self.process.returncode,124)
        pidfile=self.root/'adapter-pid';self.assertTrue(pidfile.exists())
        deadline=time.monotonic()+3
        while not gone(int(pidfile.read_text())):
            if time.monotonic()>deadline:self.fail('Owned adapter survived startup watchdog')
            time.sleep(.02)


if __name__=='__main__':unittest.main()

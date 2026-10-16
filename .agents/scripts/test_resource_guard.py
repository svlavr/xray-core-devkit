"""Real process/pipe/lease regressions for destructive lifecycle boundaries."""
import json
import io
import contextlib
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import resource_guard as guard


def gone(pid):
    try:
        guard.process_token(pid)
        return False
    except OSError:
        return True


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.base = self.root / 'transient'

    def wait_for(self, predicate):
        deadline = time.monotonic() + 8
        while not predicate():
            if time.monotonic() > deadline:
                self.fail('Owned process/file did not reach expected state')
            time.sleep(.03)

    def test_success_nonzero_preserve_cache_outputs_and_remove_scratch(self):
        output = self.root / 'evidence.txt'
        cache = self.root / 'cache'; cache.mkdir(); (cache / 'keep').write_text('keep')
        for code in [0, 3]:
            script = "import os,pathlib,sys; p=pathlib.Path(os.environ['GOTMPDIR']); (p/'go-build123').mkdir(); print(p); pathlib.Path(sys.argv[1]).write_text('evidence'); sys.exit(int(sys.argv[2]))"
            result = guard.run([sys.executable, '-c', script, str(output), str(code)],
                transient=self.base, env=dict(os.environ, GOCACHE=str(cache), GOMODCACHE=str(cache)),
                capture_output=True, text=True)
            self.assertEqual(result.returncode, code)
            self.assertFalse(Path(result.stdout.strip()).exists())
            self.assertEqual(output.read_text(), 'evidence')
            self.assertEqual((cache / 'keep').read_text(), 'keep')

    def child_script(self, holder=False):
        script = self.root / 'children.py'
        script.write_text("import subprocess,sys,time,pathlib,os\n"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid))\n"
            + ("sys.exit(0)\n" if holder else "time.sleep(60)\n"))
        return script

    def test_timeout_reaps_grandchild_and_pipe_holder(self):
        pid_file = self.root / 'pid'
        script = self.child_script()
        with self.assertRaises(subprocess.TimeoutExpired):
            guard.run([sys.executable, str(script), str(pid_file)], transient=self.base,
                capture_output=True, text=True, timeout=1)
        pid = int(pid_file.read_text())
        self.wait_for(lambda: gone(pid))
        self.assertFalse(list(self.base.glob('run-*/owner.json')))

    def test_normal_exit_reaps_descendant_holding_pipe(self):
        pid_file = self.root / 'pid'
        result = guard.run([sys.executable, str(self.child_script(True)), str(pid_file)],
            transient=self.base, capture_output=True, text=True, timeout=4)
        self.assertEqual(result.returncode, 0)
        self.wait_for(lambda: gone(int(pid_file.read_text())))

    def test_abrupt_owner_death_reaps_busy_tree_and_recovers_temp(self):
        pid_file = self.root / 'pid'
        owner = self.root / 'owner.py'
        owner.write_text("import sys,time\nsys.path.insert(0,sys.argv[1])\nimport resource_guard as g\n"
            "p=g.ManagedProcess([sys.executable,sys.argv[2],sys.argv[3]],transient=sys.argv[4])\ntime.sleep(60)\n")
        process = subprocess.Popen([sys.executable, str(owner), str(Path(guard.__file__).parent),
            str(self.child_script()), str(pid_file), str(self.base)])
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        self.wait_for(pid_file.exists)
        process.kill(); process.wait(timeout=4)
        self.wait_for(lambda: gone(int(pid_file.read_text())))
        self.wait_for(lambda: bool(guard.clean_stale(self.base)) or not list(self.base.glob('run-*/owner.json')))
        self.assertFalse(list(self.base.glob('run-*/owner.json')))

    def test_active_lease_foreign_directory_and_reparse_are_preserved(self):
        name = 'run-' + 'a' * 32
        self.base.mkdir(); folder=self.base/name; folder.mkdir()
        (folder/'owner.json').write_text(json.dumps({'schema':1,'run':name}))
        lease=self.base/(name+'.lock');lease.write_bytes(b'0')
        with lease.open('r+b') as handle:
            guard.lock_file(handle)
            self.assertEqual(guard.clean_stale(self.base), [])
        foreign=self.base/('run-'+'b'*32);foreign.mkdir();(foreign/'important').write_text('keep')
        self.assertEqual(guard.clean_stale(self.base), [name])
        self.assertTrue((foreign/'important').exists())
        if os.name=='nt':
            link=self.base/('run-'+'c'*32)
            result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.root)],capture_output=True)
            if result.returncode:self.skipTest('Junction creation unavailable')
        else:
            link=self.base/('run-'+'c'*32);link.symlink_to(self.root,target_is_directory=True)
        try:
            self.assertEqual(guard.clean_stale(self.base), [])
            self.assertTrue((foreign/'important').exists())
        finally:
            link.rmdir() if os.name=='nt' else link.unlink()

    def test_spawn_failure_cleans_scoped_temp_and_does_not_fallback(self):
        result=guard.run([str(self.root/'missing-executable')],transient=self.base,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(list(self.base.glob('run-*/owner.json')))

    def test_nonreading_backend_pipe_send_has_deadline(self):
        process=guard.ManagedProcess([sys.executable,'-c','import time;time.sleep(60)'],
            transient=self.base,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,text=True)
        try:
            started=time.monotonic()
            with self.assertRaisesRegex(TimeoutError,'send deadline'):
                guard.bounded_send(process,{'id':1,'method':'blocked','params':{'large':'x'*(2*1024*1024)}},.3)
            self.assertLess(time.monotonic()-started,4)
            self.assertIsNotNone(process.poll())
        finally:
            guard.stop(process);process.stdin.close()

    def test_posix_zombie_owner_is_exited_even_before_reaping(self):
        record='123 (owner with spaces) Z '+' '.join(['0']*18)+' 12345 0'
        with patch.object(guard.os,'name','posix'),patch.object(guard,'Path') as path:
            path.return_value.read_text.return_value=record
            with self.assertRaises(ProcessLookupError):guard.process_token(123)

    @unittest.skipUnless(os.name=='nt','Windows exclusive file lock regression')
    def test_locked_owned_scratch_is_retained_then_recovered(self):
        name='run-'+'d'*32
        self.base.mkdir();folder=self.base/name;folder.mkdir()
        (folder/'owner.json').write_text(json.dumps({'schema':1,'run':name}))
        (self.base/(name+'.lock')).write_bytes(b'0')
        path=folder/'held';path.write_text('keep')
        # A file opened without delete-sharing cannot be removed on Windows.
        with path.open('rb'):
            self.assertEqual(guard.clean_stale(self.base),[])
            self.assertTrue(path.exists())
            self.assertTrue((folder/'owner.json').exists())
        self.assertEqual(guard.clean_stale(self.base),[name])

    def test_sequential_notification_flood_still_yields_idle(self):
        stream=io.StringIO((json.dumps({'method':'notification'})+'\n')*100000)
        with patch.object(guard.sys,'stdin',stream):
            lines=guard.idle_lines(stream,idle_seconds=.002)
            for count,line in enumerate(lines):
                if line is None:break
            else:self.fail('Continuous notifications defeated idle expiry')
        self.assertLess(count,100000)

    def test_async_protocol_output_keeps_original_stream_during_redirect(self):
        intended=io.StringIO();other=io.StringIO()
        with contextlib.redirect_stdout(intended):output=guard.MCPOutput()
        try:
            with contextlib.redirect_stdout(other):
                output.emit({'id':1,'result':'protocol'})
                self.assertTrue(output.drained.wait(timeout=2))
        finally:output.close()
        self.assertIn('protocol',intended.getvalue())
        self.assertEqual(other.getvalue(),'')

    def test_keepalive_requests_do_not_reset_sequential_idle_age(self):
        stream=io.StringIO((json.dumps({'id':1,'method':'ping'})+'\n'+json.dumps({'id':2,'method':'tools/list'})+'\n')*100000)
        with patch.object(guard.sys,'stdin',stream):
            for count,line in enumerate(guard.idle_lines(stream,idle_seconds=.002)):
                if line is None:break
            else:self.fail('Keepalive defeated idle expiry')
        self.assertLess(count,200000)

    def test_unanswered_reverse_request_has_a_deadline(self):
        pidfile=self.root/'reverse-pid'
        backend="import sys,json,os,pathlib,time\npathlib.Path("+repr(str(pidfile))+").write_text(str(os.getpid()))\nfor line in sys.stdin:\n m=json.loads(line)\n if m.get('method')=='initialize':\n  print(json.dumps({'id':m['id'],'result':{}}),flush=True)\n  print(json.dumps({'id':'unanswered','method':'roots/list'}),flush=True)\n"
        # Isolate reverse-call expiry from interpreter startup and idle eviction.
        process=self.launch_relay(backend,timeout=2,idle=5)
        inbox=queue.Queue()
        def read():
            for line in process.stdout:inbox.put(json.loads(line))
        reader=threading.Thread(target=read,daemon=True);reader.start()
        process.stdin.write(json.dumps({'id':1,'method':'initialize'})+'\n');process.stdin.flush()
        initialized=inbox.get(timeout=5)
        self.assertEqual(initialized['id'],1)
        self.assertIn('result',initialized)
        self.assertNotIn('error',initialized)
        reverse=inbox.get(timeout=5)
        self.assertEqual(reverse['id'],'unanswered')
        self.assertEqual(reverse['method'],'roots/list')
        self.wait_for(lambda:gone(int(pidfile.read_text())))
        process.stdin.write(json.dumps({'id':2,'method':'ping'})+'\n');process.stdin.flush()
        self.assertEqual(inbox.get(timeout=5),{'jsonrpc':'2.0','id':2,'result':{}})
        self.assertTrue(gone(int(pidfile.read_text())))

        process.stdin.close();process.wait(timeout=4)
        reader.join(timeout=1);self.assertFalse(reader.is_alive())

    def test_catalogue_pages_and_change_notification_preserve_tool_surface(self):
        backend='''import sys,json
mode='paged';reads=0
for line in sys.stdin:
 m=json.loads(line);method=m.get('method')
 if 'id' not in m:continue
 if method=='initialize':result={}
 elif method=='tools/list':
  reads+=1
  if mode=='paged':
   result={'tools':[{'name':'b' if m.get('params',{}).get('cursor') else 'a'}]}
   if not m.get('params',{}).get('cursor'):result['nextCursor']='last'
  else:result={'tools':[{'name':mode}], 'reads':reads}
 elif method=='tools/call':
  mode=m['params']['name'];result={}
  print(json.dumps({'method':'notifications/tools/list_changed'}),flush=True)
 else:result={}
 print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':result}),flush=True)
'''
        process=self.launch_relay(backend,timeout=2)
        serial=0
        def rpc(method,params={}):
            nonlocal serial
            serial+=1;process.stdin.write(json.dumps({'id':serial,'method':method,'params':params})+'\n');process.stdin.flush()
            while True:
                message=json.loads(process.stdout.readline())
                if message.get('id')==serial:return message['result']
        rpc('initialize')
        self.assertEqual(rpc('tools/list')['tools'][0]['name'],'a')
        self.assertEqual(rpc('tools/list',{'cursor':'last'})['tools'][0]['name'],'b')
        self.assertEqual(rpc('tools/list')['tools'][0]['name'],'a')
        rpc('tools/call',{'name':'full'})
        first=rpc('tools/list');self.assertEqual(first['tools'][0]['name'],'full')
        self.assertEqual(first,rpc('tools/list'))  # Cached, no extra backend call.
        rpc('tools/call',{'name':'changed'})
        self.assertEqual(rpc('tools/list')['tools'][0]['name'],'changed')
        process.stdin.close();process.wait(timeout=4)

    def test_change_before_list_response_cannot_repopulate_stale_cache(self):
        backend='''import sys,json
first=True
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m:continue
 result={}
 if m.get('method')=='tools/list':
  result={'tools':[{'name':'old' if first else 'new'}]}
  if first:print(json.dumps({'method':'notifications/tools/list_changed'}),flush=True);first=False
 print(json.dumps({'id':m['id'],'result':result}),flush=True)
'''
        # Keep this cache-revision test on one backend; idle eviction is tested separately.
        process=self.launch_relay(backend,timeout=2,idle=5)
        for id,expected in [(1,None),(2,'old'),(3,'new')]:
            process.stdin.write(json.dumps({'id':id,'method':'initialize' if id==1 else 'tools/list'})+'\n');process.stdin.flush()
            while True:
                message=json.loads(process.stdout.readline())
                if message.get('id')==id:break
            if expected:self.assertEqual(message['result']['tools'][0]['name'],expected)
        process.stdin.close();process.wait(timeout=4)

    def launch_relay(self, backend_text, timeout=.5, idle=.2):
        backend=self.root/'scenario.py';backend.write_text(backend_text)
        launcher=self.root/'scenario-relay.py'
        launcher.write_text("import sys\nsys.path.insert(0,sys.argv[1])\nfrom resource_guard import Relay\n"
            "Relay([sys.executable,sys.argv[2]],sys.argv[3],idle=float(sys.argv[5]),timeout=float(sys.argv[4])).serve()\n")
        error_log=self.root/'scenario-errors.log'
        with error_log.open('w') as log:
            process=subprocess.Popen([sys.executable,str(launcher),str(Path(guard.__file__).parent),str(backend),str(self.root),str(timeout),str(idle)],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.error_log=error_log
        def cleanup():
            guard.stop(process)
            process.stdin.close();process.stdout.close()
        self.addCleanup(cleanup)
        return process

    def test_replay_and_deferred_tool_share_client_deadline(self):
        counter=self.root/'initializations'
        backend='''import sys,json,time,os,pathlib
counter=pathlib.Path(COUNTER)
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m:continue
 if m.get('method')=='initialize':
  count=int(counter.read_text())+1 if counter.exists() else 1
  counter.write_text(str(count))
  if count>1:time.sleep(.9)
 else:time.sleep(.9)
 print(json.dumps({'id':m['id'],'result':{'pid':os.getpid()}}),flush=True)
'''.replace('COUNTER',repr(str(counter)))
        process=self.launch_relay(backend,timeout=1.4)
        inbox=queue.Queue()
        def read():
            for line in process.stdout:inbox.put(json.loads(line))
        threading.Thread(target=read,daemon=True).start()
        def send(message):process.stdin.write(json.dumps(message)+'\n');process.stdin.flush()
        send({'id':1,'method':'initialize'})
        first=inbox.get(timeout=4)['result']['pid']
        self.wait_for(lambda:gone(first))
        started=time.monotonic()
        send({'id':2,'method':'tools/call','params':{'name':'slow'}})
        response=inbox.get(timeout=4)
        self.assertEqual(response['id'],2)
        self.assertIn('total deadline',response['error']['message'])
        self.assertLess(time.monotonic()-started,1.8)
        send({'id':3,'method':'ping'})
        self.assertEqual(inbox.get(timeout=2)['result'],{})

    def test_cancelled_managed_run_reaps_only_its_owned_tree(self):
        cancelled=threading.Event()
        pidfile=self.root/'cancelled-pid'
        peer=guard.ManagedProcess([sys.executable,'-c','import time;time.sleep(60)'],
            transient=self.base,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL)
        self.addCleanup(lambda:guard.stop(peer))
        def cancel():
            while not pidfile.exists():time.sleep(.01)
            cancelled.set()
        threading.Thread(target=cancel,daemon=True).start()
        started=time.monotonic()
        with self.assertRaises(guard.CancelledError):
            guard.run([sys.executable,'-c',"import os,pathlib,time;pathlib.Path("+repr(str(pidfile))+").write_text(str(os.getpid()));time.sleep(60)"],
                transient=self.base,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                timeout=30,cancelled=cancelled)
        self.assertLess(time.monotonic()-started,3)
        self.wait_for(lambda:gone(int(pidfile.read_text())))
        self.assertIsNone(peer.poll())

    def test_relay_nonreader_and_queue_overload_reset_instead_of_hanging(self):
        pidfile=self.root/'scenario-pid'
        backend="import os,pathlib,time\npathlib.Path("+repr(str(pidfile))+").write_text(str(os.getpid()))\ntime.sleep(60)\n"
        for overload in [False,True]:
            pidfile.unlink(missing_ok=True)
            process=self.launch_relay(backend,timeout=1)
            inbox=queue.Queue()
            def read(stream):
                for line in stream:inbox.put(json.loads(line))
            threading.Thread(target=read,args=(process.stdout,),daemon=True).start()
            process.stdin.write(json.dumps({'id':1,'method':'blocked','params':{'large':'x'*(2*1024*1024)}})+'\n');process.stdin.flush()
            self.wait_for(pidfile.exists)
            if overload:
                for id in range(2,75):process.stdin.write(json.dumps({'id':id,'method':'blocked'})+'\n')
                process.stdin.flush()
            try:result=inbox.get(timeout=5)
            except queue.Empty:self.fail('Relay state '+str(process.poll())+': '+process.error_log.read_text())
            self.assertIn('error',result)
            self.assertIn('queue limit' if overload else 'deadline',result['error']['message'])
            process.stdin.close();process.wait(timeout=4)
            self.assertEqual(process.returncode,0)
            self.wait_for(lambda:gone(int(pidfile.read_text())))

    def test_relay_stalled_output_and_client_eof_reap_backend(self):
        pidfile=self.root/'output-pid'
        backend="import sys,json,os,pathlib,time\npathlib.Path("+repr(str(pidfile))+").write_text(str(os.getpid()))\nfor line in sys.stdin:\n m=json.loads(line);print(json.dumps({'id':m['id'],'result':{'large':'x'*(2*1024*1024)}}),flush=True)\n time.sleep(60)\n"
        process=self.launch_relay(backend,timeout=.5)
        process.stdin.write(json.dumps({'id':1,'method':'large'})+'\n');process.stdin.flush()
        self.wait_for(pidfile.exists)
        time.sleep(.1)
        process.stdin.close()  # Deliberately keep stdout open and do not drain it.
        process.wait(timeout=4)
        self.assertIn(process.returncode,[0,124])
        self.wait_for(lambda:gone(int(pidfile.read_text())))

    def test_relay_idle_replays_handshake_and_preserves_reverse_cancel_notifications(self):
        backend=self.root/'backend.py'
        backend.write_text('''import sys,json,os,time,threading
initialized=False
def emit(m): print(json.dumps(m),flush=True)
for line in sys.stdin:
 m=json.loads(line); method=m.get('method')
 if method=='initialize':
  initialized=True; emit({'id':m['id'],'result':{'pid':os.getpid()}})
  def noise():
   while True:
    time.sleep(.05);emit({'method':'notice','params':{'noise':True}})
  threading.Thread(target=noise,daemon=True).start()
 elif method=='query':
  emit({'method':'notice','params':{'preserved':True}})
  emit({'id':m['id'],'result':{'pid':os.getpid(),'initialized':initialized}})
 elif method=='long':
  emit({'method':'notice','params':{'running':True}})
  def reply(id):
   time.sleep(.7);emit({'id':id,'result':{'completed':True}})
  threading.Thread(target=reply,args=(m['id'],)).start()
 elif method=='reverse': emit({'id':'server-call','method':'roots/list'})
 elif 'result' in m: emit({'id':9,'result':m['result']})
 elif method=='notifications/cancelled': emit({'id':10,'result':{'cancelled':True}})
''')
        launcher=self.root/'relay.py'
        launcher.write_text("import sys\nsys.path.insert(0,sys.argv[1])\nfrom resource_guard import Relay\n"
            "Relay([sys.executable,sys.argv[2]],sys.argv[3],idle=.25,timeout=2).serve()\n")
        process=subprocess.Popen([sys.executable,str(launcher),str(Path(guard.__file__).parent),str(backend),str(self.root)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda: guard.stop(process) if process.poll() is None else None)
        inbox=queue.Queue()
        def read():
            for line in process.stdout:inbox.put(json.loads(line))
        threading.Thread(target=read,daemon=True).start()
        def send(message):process.stdin.write(json.dumps(message)+'\n');process.stdin.flush()
        def response(id):
            deadline=time.monotonic()+4
            while True:
                message=inbox.get(timeout=max(.01,deadline-time.monotonic()))
                if message.get('id')==id:return message
        send({'id':1,'method':'initialize','params':{'capabilities':{'roots':{}}}})
        first=response(1)['result']['pid']
        send({'id':2,'method':'query'});self.assertTrue(response(2)['result']['initialized'])
        self.wait_for(lambda: gone(first))
        send({'id':3,'method':'query'});second=response(3)['result']
        self.assertNotEqual(first,second['pid']);self.assertTrue(second['initialized'])
        send({'id':4,'method':'long'})
        while not inbox.get(timeout=2).get('params',{}).get('running'):pass
        time.sleep(.35);self.assertFalse(gone(second['pid']))
        send({'method':'notifications/cancelled','params':{'requestId':4}})
        self.assertTrue(response(10)['result']['cancelled'])
        self.assertTrue(response(4)['result']['completed'])
        send({'id':9,'method':'reverse'});self.assertEqual(response('server-call')['method'],'roots/list')
        send({'id':'server-call','result':{'roots':['preserved']}})
        self.assertEqual(response(9)['result']['roots'],['preserved'])
        process.stdin.close();process.wait(timeout=4)
        self.assertEqual(process.returncode,0,process.stderr.read())
        process.stdout.close();process.stderr.close()


if __name__ == '__main__':
    unittest.main()

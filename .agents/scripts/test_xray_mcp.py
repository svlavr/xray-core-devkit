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
from types import SimpleNamespace
from unittest.mock import patch

import xray_mcp as gateway

import resource_guard as guard
from test_resource_guard import gone


class GatewayTests(unittest.TestCase):
    def test_gopls_catalogue_preserves_only_executable_backend_tools(self):
        response = {'result': {'tools': [{'name': 'go_workspace'}]}}
        with patch.object(gateway, 'args', SimpleNamespace(backend='gopls'), create=True):
            result = gateway.decorate(response, 'tools/list')
        self.assertEqual([tool['name'] for tool in result['result']['tools']], ['go_workspace'])
        self.assertTrue(result['result']['tools'][0]['annotations']['readOnlyHint'])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def launch(self,mode='normal',budget=45,delay=0,queue_budget=60,retire=15,prep_delay=.4,prep_budget=900):
        cli=self.root/'gitnexus/node_modules/gitnexus/dist/cli/index.js'
        cli.parent.mkdir(parents=True)
        cli.write_text('''import sys,json,time,os
for line in sys.stdin:
 m=json.loads(line);method=m.get('method')
 with open(__CALLS__,'a') as calls: calls.write(json.dumps(m)+'\\n')
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
'''.replace('DELAY',repr(delay)).replace('__CALLS__',repr(str(self.root/'backend-calls'))))
        adapter=self.root/'.agents/scripts/go_mcp.py';adapter.parent.mkdir(parents=True)
        adapter.write_text("import os,time,pathlib;pathlib.Path("+repr(str(self.root/'adapter-pid'))+").write_text(str(os.getpid()));time.sleep(60)")
        launcher=self.root/'launcher.py'
        launcher.write_text('''import sys,os,time,pathlib,json,subprocess
sys.path.insert(0,SCRIPTS)
import xray_mcp as gateway
from resource_guard import check_cancelled,run
root=pathlib.Path(__ROOT__)
gateway.ROOT=root;gateway.TOOLS=root;gateway.node_executable=lambda:sys.executable
gateway.cache_root=lambda:root/'cache'
gateway.STARTUP_SECONDS=BUDGET
gateway.REQUEST_SECONDS=__QUEUE_TIMEOUT__
gateway.CANCEL_RETIRE_SECONDS=__RETIRE_TIMEOUT__
state={'repo':str(root),'head':'test-head','fingerprint':'test-fingerprint','coverage':'test','dirty':''}
identity={'schema':2,'analyzer':'test','export':'test'}
manifest={**state,'identity':identity,'registry_home':str(root/'registry'),'index':str(root/'index')}
def source(deadline=None,**kwargs):
 time.sleep(SOURCE_DELAY)
 gateway.remaining(deadline,'test source validation')
 return state
calls=0
def status(deadline=None,cancelled=None):
 global calls
 calls+=1;check_cancelled(cancelled)
 if (root/'source-changed').exists():state['fingerprint']='changed-source'
 if MODE=='inventory' and calls>1:raise RuntimeError('inventory must not validate source')
 if MODE=='unresponsive' and calls>1:
  (root/'validation-started').write_text('started')
  time.sleep(60)
 if MODE=='bad_status' and calls==2:raise ValueError('bad manifest')
 if MODE=='refresh' and calls>1:return {'status':'MISSING','source':state,'identity':identity}
 if MODE in ('cold','switched','inventory') and not (root/'graph-ready').exists():return {'status':'MISSING','source':state,'identity':identity}
 return {'status':'CURRENT','source':state,'identity':identity,'manifest':manifest}
def refresh(deadline=None,cancelled=None,**kwargs):
 (root/'refresh-started').write_text('started')
 if MODE in ('cold','switched'):
  kwargs['progress']({'phase':'analyzer','preparation_id':'shared-owner'})
  script="import os,pathlib,time;pathlib.Path("+repr(str(root/'analyzer-pid'))+").write_text(str(os.getpid()));print('analyzing',flush=True);time.sleep(__PREP_DELAY__)"
  with (root/'analyze.log').open('w') as log:run([sys.executable,'-c',script],stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=gateway.remaining(deadline,'fake analyzer'),cancelled=cancelled)
  (root/'graph-ready').write_text('ready')
  if MODE=='switched':gateway.preparation.value['preparation_id']='replacement-owner'
  return status(deadline,cancelled)
 cancelled.wait(60);check_cancelled(cancelled)
 raise RuntimeError('cancel was not delivered')
gateway.source_state=source;gateway.graph_status=status;gateway.refresh_graph=refresh
gateway.main(['gopls' if MODE=='gopls' else 'gitnexus','--graph-prepare-seconds','__PREP_LIMIT__'])
'''.replace('SCRIPTS',repr(str(Path(guard.__file__).parent)))
            .replace('__ROOT__',repr(str(self.root)))
            .replace('BUDGET',repr(budget)).replace('SOURCE_DELAY',repr(delay))
            .replace('__QUEUE_TIMEOUT__',repr(queue_budget)).replace('__RETIRE_TIMEOUT__',repr(retire))
            .replace('__PREP_DELAY__',str(prep_delay)).replace('__PREP_LIMIT__',str(prep_budget))
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

    def call(self, id, name, arguments=None, timeout=4):
        self.send({'id':id,'method':'tools/call','params':{'name':name,'arguments':arguments or {}}})
        return self.response(id,timeout)

    def test_inventory_is_cheap_without_source_validation_or_preparation(self):
        self.launch(mode='inventory');self.initialize()
        self.assertIn('result',self.call(2,'list_repos'))
        self.assertFalse((self.root/'refresh-started').exists())
        self.send({'id':3,'method':'tools/list'})
        names={tool['name'] for tool in self.response(3)['result']['tools']}
        self.assertTrue({'graph_prepare','graph_status','graph_wait','graph_cancel'}.issubset(names))

    def test_cold_ticket_wait_delivers_original_query_and_reuses_backend(self):
        self.launch(mode='cold',prep_delay=.5);self.initialize()
        original={'search_query':'exact original Dispatch','limit':3}
        pending=self.call(2,'query',original)['result']['structuredContent']
        self.assertEqual(pending['status'],'PREPARING')
        self.assertEqual(pending['original_call'],{'name':'query','arguments':original})
        waiting=self.call(3,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':0})['result']['structuredContent']
        self.assertEqual(waiting['status'],'PREPARING')
        result=self.call(4,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':2})
        self.assertEqual(result['id'],4)
        self.assertEqual(result['result']['content'][0]['text'],'answer')
        self.assertIn('xray_provenance',result['result']['content'][-1]['text'])
        calls=[json.loads(line) for line in (self.root/'backend-calls').read_text().splitlines()]
        executed=[call for call in calls if call.get('method')=='tools/call']
        self.assertEqual([call['params'] for call in executed],[{'name':'query','arguments':original}])
        repeated=self.call(5,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':0})
        self.assertEqual(repeated['result']['content'][:-1],result['result']['content'])
        self.assertTrue(json.loads(repeated['result']['content'][-1]['text'])['xray_ticket']['historical'])
        warm=self.call(6,'query',original)
        self.assertEqual(warm['result']['pid'],result['result']['pid'])

    def test_wait_cancellation_does_not_cancel_owned_preparation(self):
        self.launch(mode='cold',prep_delay=1);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        self.send({'id':3,'method':'tools/call','params':{'name':'graph_wait','arguments':{'ticket':pending['ticket'],'timeout_seconds':30}}})
        time.sleep(.1)
        self.send({'method':'notifications/cancelled','params':{'requestId':3}})
        self.assertEqual(self.response(3)['error']['code'],-32800)
        self.assertIn('result',self.call(4,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':2}))
        self.assertTrue((self.root/'graph-ready').exists())

    def test_ticket_rejects_source_change_before_original_query(self):
        self.launch(mode='cold',prep_delay=.3);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        (self.root/'source-changed').touch()
        answer=self.call(3,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':2})
        self.assertEqual(answer['result']['structuredContent']['status'],'FAILED')
        self.assertIn('Source/analyzer changed',answer['result']['structuredContent']['error'])

    def test_wait_rejects_replaced_operation_even_for_identical_source(self):
        self.launch(mode='switched',prep_delay=.3);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        answer=self.call(3,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':2})
        self.assertEqual(answer['result']['structuredContent']['status'],'STALE')
        self.assertIn('Preparation changed while waiting',answer['result']['structuredContent']['error'])
        calls=[json.loads(line) for line in (self.root/'backend-calls').read_text().splitlines()]
        self.assertFalse(any(call.get('method')=='tools/call' for call in calls))

    def test_preparation_timeout_reaps_owned_analyzer_and_latches_failure(self):
        self.launch(mode='cold',prep_delay=60,prep_budget=1);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        answer=self.call(3,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':3})['result']['structuredContent']
        self.assertIn(answer['status'],('FAILED','CANCELLED'))
        pid=int((self.root/'analyzer-pid').read_text())
        self.assertTrue(gone(pid))
        self.assertFalse((self.root/'graph-ready').exists())

    @unittest.skipUnless(os.environ.get('XRAY_LONG_GRAPH_TEST')=='1','explicit >240s process lifetime control')
    def test_preparation_survives_client_limit_as_real_owned_subprocess(self):
        self.launch(mode='cold',prep_delay=242,prep_budget=300);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        deadline=time.monotonic()+250
        counter=3
        while time.monotonic()<deadline:
            answer=self.call(counter,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':20},timeout=24)
            counter+=1
            if 'structuredContent' not in answer.get('result',{}):
                self.assertGreater(time.monotonic()-(deadline-250),240)
                self.assertIn('xray_provenance',answer['result']['content'][-1]['text'])
                break
            self.assertEqual(answer['result']['structuredContent']['status'],'PREPARING')
        else:self.fail('Long owned preparation did not deliver original query')

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
        preparing=self.response(2)['result']['structuredContent']
        deadline=time.monotonic()+4
        while not (self.root/'refresh-started').exists():
            if time.monotonic()>deadline:self.fail('Fake refresh did not start')
            time.sleep(.01)
        self.send({'id':4,'method':'tools/call','params':{'name':'graph_cancel','arguments':{'preparation_id':preparing['preparation_id']}}})
        self.assertIn(self.response(4)['result']['structuredContent']['status'],('PREPARING','CANCELLED'))
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


    def test_terminal_tickets_free_capacity_and_cached_results_survive_new_preparation(self):
        self.launch(mode='cold',prep_delay=60,prep_budget=1);self.initialize()
        pending=[]
        for number in range(32):
            pending.append(self.call(10+number,'query')['result']['structuredContent'])
        first=self.call(50,'graph_wait',{'ticket':pending[0]['ticket'],'timeout_seconds':3})
        self.assertIn(first['result']['structuredContent']['status'],('FAILED','CANCELLED'))
        for number,item in enumerate(pending[1:]):
            terminal=self.call(60+number,'graph_wait',{'ticket':item['ticket'],'timeout_seconds':0})
            self.assertIn(terminal['result']['structuredContent']['status'],('FAILED','CANCELLED'))
        self.call(100,'graph_prepare',{'force':True,'timeout_seconds':1})
        admitted=self.call(101,'query')['result']['structuredContent']
        self.assertEqual(admitted['status'],'PREPARING')
        old=self.call(102,'graph_wait',{'ticket':pending[-1]['ticket'],'timeout_seconds':0})
        self.assertIn(old['result']['structuredContent']['status'],('FAILED','CANCELLED'))
        self.assertTrue(json.loads(old['result']['content'][-1]['text'])['xray_ticket']['historical'])

    def test_completed_ticket_retrieval_survives_later_preparation(self):
        self.launch(mode='cold',prep_delay=.2);self.initialize()
        pending=self.call(2,'query')['result']['structuredContent']
        first=self.call(3,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':2})
        self.call(4,'graph_prepare',{'force':True})
        cached=self.call(5,'graph_wait',{'ticket':pending['ticket'],'timeout_seconds':0})
        self.assertEqual(cached['result']['content'][:-1],first['result']['content'])
        calls=[json.loads(line) for line in (self.root/'backend-calls').read_text().splitlines()]
        self.assertEqual(sum(call.get('method')=='tools/call' for call in calls),1)

    def test_old_watchdog_cannot_cancel_a_replacement_preparation(self):
        prep=gateway.GraphPreparation()
        current={'status':'MISSING','source':{'fingerprint':'same-source'},'identity':{'analyzer':'test'}}
        first_done=threading.Event();second_done=threading.Event();inside=threading.Event();release=threading.Event()
        class PausedEvent(threading.Event):
            def is_set(self):
                inside.set();release.wait(3)
                return super().is_set()
        calls=[]
        def refresh(**kwargs):
            gate=first_done if not calls else second_done
            calls.append(1);gate.wait(3)
            return {**current,'status':'CURRENT'}
        with patch.object(gateway,'refresh_graph',side_effect=refresh):
            prep.start(current);old=PausedEvent();prep.cancelled=old;prep.deadline=0
            watcher=threading.Thread(target=prep.watchdog);watcher.start()
            self.assertTrue(inside.wait(2))
            first_done.set();prep.thread.join(2)
            admitted=threading.Event()
            replacement=threading.Thread(target=lambda:(prep.start(current,force=True),admitted.set()))
            replacement.start()
            self.assertFalse(admitted.wait(.05))
            release.set();watcher.join(2);replacement.join(2)
            self.assertTrue(admitted.is_set())
            self.assertTrue(old.is_set())
            self.assertFalse(prep.cancelled.is_set())
            second_done.set();prep.thread.join(2)

if __name__=='__main__':unittest.main()

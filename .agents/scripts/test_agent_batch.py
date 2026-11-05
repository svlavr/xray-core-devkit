"""Evidence fidelity and native replay checks for parallel advisory dispatch."""
import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import agent_batch as batch


def packet():
    return {'batch_id':'test-parallel','sources':{'current':{'paths':['owner.go']}},
        'jobs':[{'key':k,'kind':'review','title':k,'body':'Read the supplied owner.','inputs':['current']} for k in ('one','two','three')]}


class FakeNative:
    def __init__(self):self.items={};self.calls=[];self.fail=None
    def scoped(self,store_ref):return self
    def show(self,id):return copy.deepcopy(self.items.get(id))
    def run(self,args,body=None):
        self.calls.append(args)
        if args[:2]==['bd','create']:
            id=args[args.index('--id')+1]
            if id in self.items:raise AssertionError('Duplicate create')
            self.items[id]={'id':id,'title':args[2],'description':body.decode(),
                'metadata':json.loads(args[args.index('--metadata')+1]),'status':'open'}
            mode='create'
        else:
            mode='sling';id=args[2]
            self.items[id]['metadata']['gc.routed_to']=args[1]
        if self.fail==mode:
            self.fail=None
            raise subprocess.TimeoutExpired(args,60)
        return b'{}'


class BatchTests(unittest.TestCase):
    def state(self):
        p=packet();return {'batch_id':p['batch_id'],'jobs':batch.planned_jobs(p,{'linux':'/snapshot','source_head':'a'*40})}

    def test_bounds_and_host_paths_fail_before_dispatch(self):
        p=packet();self.assertEqual(batch.check_packet(p),'test-parallel')
        p['jobs']=p['jobs'][:1]
        with self.assertRaises(ValueError):batch.check_packet(p)
        p=packet();p['jobs'][0]['body']='Read /mnt/e/AI/code'
        with self.assertRaises(ValueError):batch.check_packet(p)
        for path in ('../outside','/absolute','folder/../outside','.git/config','.codex/config.toml','.codex/CONFIG.TOML','.LOCAL/workspace/context.json','a\\b'):
            with self.assertRaises(ValueError):batch.relative(path)

    def test_dirty_worktree_bytes_and_corrupt_copy(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(batch.workspace,'git',return_value='a'*40):
            root=Path(tmp);(root/'owner.go').write_bytes(b'current dirty content\r\n')
            head,files,manifest=batch.capture(packet(),root)
            self.assertEqual(files['current/owner.go'],b'current dirty content\r\n')
            dest=root/'snapshot';(dest/'current').mkdir(parents=True)
            (dest/'current/owner.go').write_bytes(files['current/owner.go'])
            batch.verify_copy(dest,manifest)
            (dest/'current/owner.go').write_bytes(b'corrupt')
            with self.assertRaises(RuntimeError):batch.verify_copy(dest,manifest)

    def test_source_change_during_capture_is_rejected(self):
        with patch.object(batch.workspace,'git',return_value='a'*40),patch.object(batch,'read_worktree',side_effect=[b'first',b'changed']):
            with self.assertRaisesRegex(RuntimeError,'changed'):batch.capture(packet())

    def test_aliases_and_links_rejected(self):
        p=packet();p['sources']['current']['paths']=['owner.go','OWNER.go']
        with self.assertRaises(ValueError):batch.check_packet(p)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'real').write_text('x')
            import os
            os.link(root/'real',root/'owner.go')
            with self.assertRaisesRegex(ValueError,'Hard-linked'):batch.read_worktree(root,'owner.go')

    def test_job_only_receives_its_selected_source_directories(self):
        p=packet();p['sources']['other']={'paths':['other.go']};p['jobs'][1]['inputs']=['other']
        jobs=batch.planned_jobs(p,{'linux':'/snapshot','source_head':'a'*40})
        self.assertIn('Your source directories: /snapshot/current',jobs[0]['body'])
        self.assertNotIn('/snapshot/other',jobs[0]['body'])
        self.assertIn('Your source directories: /snapshot/other',jobs[1]['body'])

    def test_all_native_jobs_created_then_routed_without_wait(self):
        state=self.state();native=FakeNative();batch.enqueue(state,native,lambda:None)
        self.assertEqual([c[:2] for c in native.calls[:3]],[['bd','create']]*3)
        self.assertEqual([c[0] for c in native.calls[3:]],['sling']*3)
        self.assertTrue(all(j['phase']=='routed' for j in state['jobs']))
        batch.enqueue(state,native,lambda:None)
        self.assertEqual(len(native.calls),9)
        self.assertTrue(all('--nudge' in c for c in native.calls[6:]))

    def test_unknown_create_and_sling_resume_same_ids_without_duplication(self):
        for mode in ('create','sling'):
            state=self.state();native=FakeNative();native.fail=mode
            with self.assertRaises((RuntimeError,subprocess.TimeoutExpired)):batch.enqueue(state,native,lambda:None)
            batch.enqueue(state,native,lambda:None)
            self.assertEqual(len(native.items),3)
            self.assertEqual(len([c for c in native.calls if c[:2]==['bd','create']]),3)
            self.assertEqual(len(native.calls),6 if mode=='create' else 9)

    def test_conflicting_content_or_route_is_not_reassigned(self):
        state=self.state();native=FakeNative();batch.enqueue(state,native,lambda:None)
        item=native.items[state['jobs'][0]['id']]
        item['metadata']['gc.routed_to']='other-pool'
        with self.assertRaises(RuntimeError):batch.enqueue(state,native,lambda:None)
        self.assertEqual(len(native.calls),6)

    def test_replay_cannot_switch_native_namespace(self):
        data={'distribution':'Xray-Workers','user':'owner','city':'/city-one'}
        state={'namespace':batch.namespace(data)}
        batch.check_namespace(state,data)
        with self.assertRaises(RuntimeError):batch.check_namespace(state,{**data,'city':'/city-two'})

    def test_closed_jobs_are_not_reopened_and_content_conflicts_block(self):
        state=self.state();native=FakeNative();batch.enqueue(state,native,lambda:None)
        for item in native.items.values():item['status']='closed'
        batch.enqueue(state,native,lambda:None)
        self.assertEqual(len(native.calls),6)
        native.items[state['jobs'][0]['id']]['description']='different input'
        with self.assertRaises(RuntimeError):batch.enqueue(state,native,lambda:None)
        self.assertEqual(len(native.calls),6)

    def test_unverified_claim_is_not_reassigned_or_nudged(self):
        state=self.state();native=FakeNative();batch.enqueue(state,native,lambda:None)
        first=state['jobs'][0]['id'];native.items[first]['assignee']='other-session'
        native.items[first]['status']='in_progress'
        with self.assertRaises(RuntimeError):batch.enqueue(state,native,lambda:None)
        self.assertFalse(any(c[0]=='sling' and c[2]==first for c in native.calls[6:]))

    def test_closed_same_pool_session_cannot_prove_live_claim(self):
        state=self.state();native=FakeNative();batch.enqueue(state,native,lambda:None)
        first=state['jobs'][0]['id'];native.items[first]['assignee']='closed-session'
        native.items[first]['status']='in_progress'
        native.items['closed-session']={'id':'closed-session','issue_type':'session','status':'closed',
            'metadata':{'template':'mu-reviewer','state':'closed'}}
        with self.assertRaises(RuntimeError):batch.enqueue(state,native,lambda:None)
        self.assertNotEqual(state['jobs'][0]['phase'],'claimed')
        self.assertFalse(any(c[0]=='sling' and c[2]==first for c in native.calls[6:]))


    def test_implementation_ids_and_all_task_operations_use_rig_while_session_owner_uses_city(self):
        p=packet();p['jobs']=p['jobs'][:1];p['jobs'][0]['kind']='implement'
        state={'batch_id':p['batch_id'],'jobs':batch.planned_jobs(p,{'linux':'/snapshot','source_head':'a'*40})}
        job=state['jobs'][0];self.assertTrue(job['id'].startswith('mux-b-'))
        self.assertEqual(job['store_ref'],'rig:mu-core')
        self.assertEqual(job['metadata']['mu.store_ref'],'rig:mu-core')
        databases={'city':{},'rig:mu-core':{}};calls=[]
        def execute(args,input=None,**kwargs):
            calls.append(args)
            if args[0]=='bd':
                store='rig:mu-core' if args[1:3]==['--rig','mu-core'] else 'city'
                operation=args[3:] if store=='rig:mu-core' else args[1:]
                if operation[0]=='show':
                    item=databases[store].get(operation[1])
                    return subprocess.CompletedProcess(args,0 if item else 1,
                        json.dumps([item]).encode() if item else b'',b'' if item else b'not found')
                self.assertEqual(operation[0],'create')
                identity=operation[operation.index('--id')+1]
                self.assertTrue(identity.startswith('mux-b-'));self.assertNotIn(identity,databases[store])
                databases[store][identity]={'id':identity,'title':operation[1],'description':input.decode(),
                    'metadata':json.loads(operation[operation.index('--metadata')+1]),'status':'open'}
            else:
                self.assertEqual(args[:2],['sling','mu-core/codex'])
                databases['rig:mu-core'][args[2]]['metadata']['gc.routed_to']=args[1]
            return subprocess.CompletedProcess(args,0,b'{}',b'')
        native=batch.Native({},lambda data,args:args)
        with patch.object(batch.subprocess,'run',side_effect=execute):
            batch.enqueue(state,native,lambda:None)
            batch.enqueue(state,native,lambda:None)
            owner='mc-wisp-owner';databases['rig:mu-core'][job['id']]['assignee']=owner
            databases['city'][owner]={'id':owner,'issue_type':'session','status':'open',
                'metadata':{'template':'mu-core/codex','state':'active'}}
            batch.enqueue(state,native,lambda:None)
        task_ops=[args for args in calls if args[0]=='bd' and job['id'] in args]
        self.assertTrue(task_ops);self.assertTrue(all(args[1:3]==['--rig','mu-core'] for args in task_ops))
        self.assertEqual(len([args for args in task_ops if 'create' in args]),1)
        self.assertIn(['bd','show',owner,'--json'],calls)
        self.assertEqual(job['phase'],'claimed')


    def test_old_cross_store_implementation_receipt_refuses_before_any_native_mutation(self):
        p=packet();p['jobs']=p['jobs'][:1];p['jobs'][0]['kind']='implement'
        state={'batch_id':p['batch_id'],'jobs':batch.planned_jobs(p,{'linux':'/snapshot','source_head':'a'*40})}
        state['jobs'][0].pop('store_ref');native=FakeNative()
        with self.assertRaisesRegex(RuntimeError,'store differs from target rig'):batch.enqueue(state,native,lambda:None)
        self.assertFalse(native.calls)


    def test_mutable_roots_are_prepared_by_selected_linux_user_before_freezing(self):
        data={'distribution':'fixture-distro','user':'fixture-user'}
        with patch.object(batch.subprocess,'run') as invoke:
            batch.prepare_run_roots(data,'/owned/runs/unique',['one','two'])
        args=invoke.call_args.args[0]
        self.assertEqual(args[:8],['wsl.exe','-d','fixture-distro','-u','fixture-user','--exec','python3','-c'])
        self.assertEqual(args[-3:],['/owned/runs/unique','one','two'])
        # Execute the exact creation/write probe on owned local fixture paths;
        # actual WSL UID ownership remains an integration check.
        with tempfile.TemporaryDirectory() as folder:
            runtime=Path(folder)/'runs'
            subprocess.run([sys.executable,'-c',args[8],str(runtime),'one','two'],check=True,capture_output=True)
            self.assertTrue((runtime/'one/transient').is_dir())
            self.assertTrue((runtime/'two/transient').is_dir())


    def test_launch_binding_is_native_metadata_before_admission_and_cannot_change(self):
        state=self.state();native=FakeNative()
        for job in state['jobs']:
            job['metadata'].update({'mu.role':'mu_security_reviewer','mu.launch_path':'/frozen/'+job['key'],
                'mu.launch_sha256':'c'*64,'mu.profile_sha256':'d'*64})
        batch.enqueue(state,native,lambda:None)
        for call in native.calls[:3]:
            meta=json.loads(call[call.index('--metadata')+1])
            self.assertEqual(meta['mu.role'],'mu_security_reviewer')
            self.assertEqual(meta['mu.launch_sha256'],'c'*64)
        native.items[state['jobs'][0]['id']]['metadata']['mu.launch_sha256']='different'
        with self.assertRaisesRegex(RuntimeError,'metadata differs'):batch.enqueue(state,native,lambda:None)
        self.assertEqual(len(native.calls),6)


    def test_implementation_is_not_rewritten_as_read_only_advice(self):
        p=packet();p['jobs']=p['jobs'][:1];p['jobs'][0]['kind']='implement'
        job=batch.planned_jobs(p,{'linux':'/snapshot','source_head':'a'*40})[0]
        self.assertIn('Honor only the dispatched write set',job['body'])
        self.assertNotIn('No source edits, Git writes',job['body'])



    def test_implementation_freezes_maintained_catalog_while_advisory_stays_selected(self):
        task={'kind':'implement','role':'mu_investigator'}
        _,files=batch.tooling_inputs(task)
        skills={Path(name).parent.name for name in files if name.endswith('/SKILL.md')}
        self.assertEqual(skills,batch.workspace.MANAGED_SKILLS)
        self.assertEqual(len(skills),18)
        self.assertLess(len(files),512)
        self.assertLess(sum(map(len,files.values())),64*1024*1024)
        _,selected=batch.tooling_inputs({**task,'kind':'review','skills':['xray-code-analysis']})
        self.assertEqual([name for name in selected if name.endswith('/SKILL.md')],['.agents/skills/xray-code-analysis/SKILL.md'])

    def test_neutral_snapshot_constructs_hooks_without_reading_mutable_city_file(self):
        from runtime_hooks import reviewed_document
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);real_path=Path
            data={'city':'/srv/city','distribution':'fixture','user':'owner'}
            p=packet()
            with patch.object(batch,'capture',return_value=('a'*40,{},{})), \
                 patch.object(batch,'Path',side_effect=lambda value:base if value=='//wsl.localhost' else real_path(value)), \
                 patch.object(batch,'prepare_run_roots'),patch.object(batch,'freeze_launches',return_value=({},{})) as freeze, \
                 patch.object(batch,'read_worktree',side_effect=AssertionError('Mutable GC city hooks became snapshot authority')), \
                 patch.object(batch.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                result=batch.snapshot(data,p)
            self.assertEqual(result['source_head'],'a'*40)
            self.assertEqual(json.loads(freeze.call_args.kwargs['native_hooks']),reviewed_document(data['city']))
            self.assertEqual(freeze.call_args.kwargs['city'],data['city'])

    def test_retained_batch_uses_exact_saved_assignment_before_current_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);state_dir=root/'state';state_dir.mkdir();remote=root/'remote'
            frozen=remote/'fixture/saved';frozen.mkdir(parents=True)
            helper=frozen/'role_bootstrap.py';helper.write_bytes(b'old immutable helper')
            manifest={'role_bootstrap.py':{'sha256':batch.digest(helper.read_bytes())}}
            (frozen/'manifest.json').write_bytes(batch.encoded(manifest))
            p=packet();p['jobs'][0].update(previous_model='gpt-6-luna',blocker='unresolved_technical',model='formerly-ignored')
            file=root/'packet.json';file.write_text(json.dumps(p));data={'distribution':'fixture','user':'owner','city':'/city'}
            old={'key':'one','id':'mc-retained','route':{'model':'gpt-6.1-sol','effort':'high','target':'mu-reviewer'},'phase':'routed'}
            state={'batch_id':p['batch_id'],'namespace':batch.namespace(data),'packet_hash':batch.digest(batch.encoded(p)),
                'evidence':{'linux':'/saved','source_head':'a'*40,'files':manifest,'manifest_sha256':batch.digest((frozen/'manifest.json').read_bytes())},'jobs':[old]}
            record=state_dir/(p['batch_id']+'.json');record.write_text(json.dumps(state))
            real_path=Path
            with patch.object(batch,'STATE',state_dir),patch.object(batch.workspace,'repository_guard'), \
                 patch.object(batch,'Path',side_effect=lambda value:remote if value=='//wsl.localhost' else real_path(value)), \
                 patch.object(batch,'select_route',side_effect=AssertionError('Retained packet was re-admitted')), \
                 patch.object(batch,'snapshot',side_effect=AssertionError('Retained helper was rewritten')), \
                 patch.object(batch,'Native'),patch.object(batch,'enqueue') as enqueue:
                result=batch.run_batch(data,file,lambda *args:[])
                self.assertEqual(result['jobs'][0]['id'],'mc-retained')
                self.assertEqual(enqueue.call_args.args[0]['jobs'],[old])
                state['packet_hash']='different';record.write_text(json.dumps(state))
                with self.assertRaisesRegex(ValueError,'different packet'):batch.run_batch(data,file,lambda *args:[])
            self.assertEqual(helper.read_bytes(),b'old immutable helper')

if __name__=='__main__':unittest.main()

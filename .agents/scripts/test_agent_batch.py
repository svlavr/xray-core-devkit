"""Evidence fidelity and native replay checks for parallel advisory dispatch."""
import copy
import json
from pathlib import Path
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


if __name__=='__main__':unittest.main()

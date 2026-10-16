"""Cost routing must never turn missing evidence into an Astra worker fan-out."""
import unittest
from model_router import select_route,validate_models


class ModelRoutingTests(unittest.TestCase):
    def test_bounded_lookup_uses_luna_high(self):
        r=select_route({'kind':'explore','bounded':True})
        self.assertEqual((r['model'],r['effort']),('gpt-6-luna','high'))

    def test_cross_owner_analysis_and_implementation_use_sol_61(self):
        for task in [{'kind':'explore','bounded':True,'cross_owner':True},{'kind':'implement'},{'kind':'review'}]:
            self.assertEqual(select_route(task)['model'],'gpt-6.1-sol')

    def test_unresolved_luna_escalates_to_sol(self):
        r=select_route({'kind':'explore','bounded':True,'previous_model':'gpt-6-luna','blocker':'unresolved_technical'})
        self.assertEqual(r['model'],'gpt-6.1-sol')

    def test_astra_requires_sol_evidence_and_named_question(self):
        with self.assertRaises(ValueError):select_route({'kind':'deep'})
        with self.assertRaises(ValueError):select_route({'kind':'deep','previous_model':'gpt-6.1-sol',
            'discriminator':'already resolved question','evidence':['receipt']})
        r=select_route({'kind':'review','previous_model':'gpt-6.1-sol','blocker':'unresolved_technical',
                        'discriminator':'one unresolved lock ordering','evidence':['source/test receipt']})
        self.assertEqual((r['target'],r['max_active']),('mu-deep',1))

    def test_missing_input_does_not_escalate(self):
        r=select_route({'kind':'deep','blocker':'missing_input','previous_model':'gpt-6.1-sol'})
        self.assertEqual(r['action'],'NEEDS_CONTEXT')

    def test_unchanged_astra_problem_is_not_repeated(self):
        r=select_route({'kind':'deep','previous_model':'gpt-6-astra','blocker':'unresolved_technical'})
        self.assertEqual(r['action'],'NEEDS_CONTEXT')

    def test_global_astra_default_is_rejected(self):
        cfg={'workspace':{'provider':'codex'},'providers':{'codex':{'option_defaults':{'model':'gpt-6-astra','effort':'high'}}},'agent':[{'name':'codex'}]}
        with self.assertRaisesRegex(RuntimeError,'Worker default'):validate_models(cfg)
        cfg['providers']['codex']['option_defaults']['model']='gpt-6.1-sol'
        cfg['agent']=[{'name':'mu-deep','max_active_sessions':2,'option_defaults':{'model':'gpt-6-astra'}}]
        with self.assertRaises(RuntimeError):validate_models(cfg)
        cfg['agent'][0]['max_active_sessions']=1
        self.assertTrue(validate_models(cfg))

    def test_duplicate_deep_pool_and_unbounded_worker_capacity_are_rejected(self):
        cfg={'workspace':{'provider':'codex'},'providers':{'codex':{'option_defaults':{'model':'gpt-6.1-sol','effort':'high'}}},
             'agent':[{'name':'mu-deep','max_active_sessions':1,'option_defaults':{'model':'gpt-6-astra'}}]*2}
        with self.assertRaisesRegex(RuntimeError,'Only one'):validate_models(cfg)
        for limit in (0,24,True,'23'):
            cfg['agent']=[{'name':'codex','max_active_sessions':limit}]
            with self.assertRaisesRegex(RuntimeError,'capacity'):validate_models(cfg)


if __name__=='__main__':unittest.main()

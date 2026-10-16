"""Reject a shared context policy after incompatible model-catalog drift."""
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from context_policy import settings
import context_policy


class ContextPolicyTests(unittest.TestCase):
    def test_eighty_percent_of_effective_window_and_catalog_guard(self):
        catalog={'models':[{'slug':n,'context_window':272000,'max_context_window':872000,
            'effective_context_window_percent':95} for n in ('gpt-6-astra','gpt-6.1-sol','gpt-6-luna')]}
        self.assertEqual(settings(catalog)['model_auto_compact_token_limit'],662720)
        catalog['models'][-1]['max_context_window']=272000
        with self.assertRaisesRegex(RuntimeError,'gpt-6-luna'):settings(catalog)

    def test_absent_or_malformed_catalog_is_not_claimed_compatible(self):
        with self.assertRaisesRegex(RuntimeError, 'capability catalog'):
            settings({})
        with self.assertRaisesRegex(RuntimeError, 'gpt-6-astra'):
            settings({'models': []})

    def test_invalid_context_percentages_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'context.json'
            source = json.loads(context_policy.POLICY.read_text(encoding='utf-8'))
            source['effective_percent'] = 101
            path.write_text(json.dumps(source), encoding='utf-8')
            with patch.object(context_policy, 'POLICY', path):
                with self.assertRaisesRegex(RuntimeError, 'Invalid context policy'):
                    settings()


if __name__=='__main__':unittest.main()

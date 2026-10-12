import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((BASE / 'scientific_library' / 'knowledge_base.json').read_text(encoding='utf-8'))

    def test_catalog_has_unique_ids_and_required_fields(self):
        entries = self.catalog['entries']
        self.assertGreaterEqual(len(entries), 150)
        self.assertEqual(len({e['id'] for e in entries}), len(entries))
        required = {'id','title','domain','kind','formula_or_rule','meaning','applicability_conditions','limitations','executable','validation_status'}
        for entry in entries:
            self.assertTrue(required.issubset(entry.keys()), entry.get('id'))

    def test_foundational_domains_are_present(self):
        domains = ' '.join(e['domain'] for e in self.catalog['entries']).casefold()
        for term in ('mathematics','physics','chemistry','biology','medicine','environment','statistics','computer_science','neuroscience','engineering','materials_science','cosmetics','astronomy','earth_science'):
            self.assertIn(term, domains)

    def test_unimplemented_knowledge_is_not_claimed_executable(self):
        for entry in self.catalog['entries']:
            if entry['validation_status'] == 'not_individually_verified_in_software':
                self.assertFalse(entry['executable'], entry['id'])


    def test_entries_have_clear_nonexecution_status(self):
        for entry in self.catalog['entries']:
            if not entry.get('executable', False):
                self.assertIn('not_individually_verified', entry.get('validation_status', ''))

    def test_domain_distribution_is_nontrivial(self):
        domains = {e['domain'] for e in self.catalog['entries']}
        self.assertGreaterEqual(len(domains), 12)

if __name__ == '__main__':
    unittest.main()

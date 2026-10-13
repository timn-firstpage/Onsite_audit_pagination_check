"""Integration tests catch wrong checklist branches, false passes and lost URL semantics."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ENGINE = Path(__file__).resolve().parents[1] / 'scripts' / 'audit.py'


class AuditTests(unittest.TestCase):
    def setUp(self):
        test_root = ENGINE.parents[1] / 'runs' / 'tests'
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.pcols = ['Address', 'rel="next" 1', 'rel="prev" 1', 'Canonical Link Element 1', 'Canonical Link Element 2']
        self.icols = ['Address', 'Status Code', 'Redirect URI', 'Canonical Link Element 1', 'Canonical Link Element 2', 'Indexability', 'Indexability Status']
        self.p = [['https://example.com/products', '/products?page=2', '', '/products', ''],
                  ['https://example.com/products?page=2', '', '/products', '/products?page=2', '']]
        self.i = [['https://example.com/products', '200', '', '/products', '', 'Indexable', ''],
                  ['https://example.com/products?page=2', '200', '', '/products?page=2', '', 'Indexable', ''],
                  ['https://example.com/other', '200', '', '/other', '', 'Indexable', '']]
        self.pairs = []

    def write(self, name, cols, rows):
        path = self.base / name
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f); w.writerow(cols); w.writerows(rows)
        return path

    def run_audit(self, options=None, expect_code=0):
        self.assertTrue(ENGINE.exists(), 'Missing CSV-to-findings automation engine')
        self.write('pagination_all.csv', self.pcols, self.p)
        self.write('internal_all.csv', self.icols, self.i)
        self.write('near_duplicate_pairs.csv', ['Address', 'Near Duplicate Address', 'Similarity'], self.pairs)
        config = {'site': {'name': '=Example', 'start_url': 'https://example.com/'},
                  'source': {'export_directory': '.'},
                  'checks': {'pagination': True, 'live_checks': False},
                  'output': {'audit_date': '2026-10-12', 'language': 'zh'},
                  'budget': {'max_mcp_calls': 10}, 'pagination': options or {}}
        path = self.base / 'config.json'; path.write_text(json.dumps(config), encoding='utf-8')
        proc = subprocess.run([sys.executable, str(ENGINE), '--config', str(path), '--run-dir', str(self.base / 'run')], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(proc.returncode, expect_code, proc.stderr)
        if expect_code: return proc
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), config, 'Input global config was mutated')
        output = self.base / 'run' / 'pagination'
        return json.loads((output / 'findings.json').read_text(encoding='utf-8'))

    def check(self, result, id):
        return next(c for c in result['checks'] if c['id'] == id)

    def test_clean_crawl_and_manual_14_1(self):
        result = self.run_audit()
        self.assertEqual([c['result'] for c in result['checks']], ['Human check', '√', '√', '√', '√', '√'])
        self.assertEqual(self.check(result, '14.1')['issues'], [])

    def test_relative_tracking_canonical_and_page_one_are_allowed(self):
        self.p += [['https://example.com/products?page=2&utm_source=email', '', '/products', '/products?page=2', ''],
                   ['https://example.com/products?page=1', '/products?page=2', '', '/products', '']]
        result = self.run_audit()
        self.assertEqual(self.check(result, '14.2')['result'], '√')
        self.assertEqual(self.check(result, '14.6')['result'], '√')

    def test_wrong_missing_conflicting_canonicals_are_all_failures(self):
        self.p[1][3] = '/products'
        self.p += [['https://example.com/blog?page=2', '', '/blog', '', ''],
                   ['https://example.com/news?page=2', '', '/news', '/news?page=2', '/news']]
        result = self.run_audit()
        for id in ['14.2', '14.6']:
            self.assertEqual(self.check(result, id)['result'], 'X')
            self.assertEqual(len(self.check(result, id)['issues']), 3)

    def test_both_annotations_empty_is_x_not_na(self):
        self.p[1][2] = ''
        result = self.run_audit()
        self.assertEqual(self.check(result, '14.3')['result'], 'X')
        self.assertEqual(self.check(result, '14.3')['issues'][0]['address'], 'https://example.com/products?page=2')

    def test_page_one_exact_parameter_preserves_filter_and_matches_root(self):
        self.i += [['https://example.com/products?category=shoes', '200', '', '?category=shoes', '', 'Indexable', ''],
                   ['https://example.com/products?page=1&category=shoes', '200', '', '?category=shoes&page=1', '', 'Indexable', ''],
                   ['https://example.com/products?page=10', '200', '', '', '', 'Indexable', '']]
        result = self.run_audit()
        check = self.check(result, '14.4')
        self.assertEqual(check['result'], 'X')
        self.assertEqual(len(check['issues']), 1)
        self.assertEqual(check['issues'][0]['target'], 'https://example.com/products?category=shoes')

    def test_page_one_permanent_redirect_and_absent_root_do_not_fail(self):
        self.i += [['https://example.com/products?page=1', '301', '/products', '', '', 'Non-Indexable', 'Redirected'],
                   ['https://example.com/missing?page=1', '200', '', '', '', 'Indexable', '']]
        self.assertEqual(self.check(self.run_audit(), '14.4')['result'], '√')

    def test_page_one_missing_canonical_is_x(self):
        self.i += [['https://example.com/products?page=1', '200', '', '', '', 'Indexable', '']]
        self.assertEqual(self.check(self.run_audit(), '14.4')['result'], 'X')

    def test_native_pair_rule_deduplicates_reverse_pair_and_keeps_self_canonical(self):
        self.pairs = [['https://example.com/products?page=2', 'https://example.com/other', '95'],
                      ['https://example.com/other', 'https://example.com/products?page=2', '95']]
        result = self.run_audit()
        check = self.check(result, '14.5')
        self.assertEqual(check['result'], 'X')
        self.assertEqual(len(check['issues']), 1)
        self.assertEqual(check['issues'][0]['address'], 'https://example.com/products?page=2')
        self.assertIn('https://example.com/other', check['issues'][0]['issue'])

    def test_nonindexable_canonicalised_and_unrelated_pairs_are_excluded(self):
        self.i[2][5:] = ['Non-Indexable', 'Canonicalised']
        self.i += [['https://example.com/unrelated', '200', '', '/unrelated', '', 'Indexable', '']]
        self.pairs = [['https://example.com/products?page=2', 'https://example.com/other', '99'],
                      ['https://example.com/other', 'https://example.com/unrelated', '99']]
        self.assertEqual(self.check(self.run_audit(), '14.5')['result'], '√')

    def test_empty_exports_do_not_trigger_scope_human_checks(self):
        self.p = []; self.i = []
        result = self.run_audit()
        self.assertEqual(self.check(result, '14.2')['result'], '√')
        self.assertEqual(self.check(result, '14.4')['result'], '√')
        self.assertEqual(self.check(result, '14.5')['result'], '√')
        self.assertEqual(self.check(result, '14.3')['result'], 'X')

    def test_missing_required_field_is_error_not_canonical_failure(self):
        self.pcols = self.pcols[:3]
        self.p = [r[:3] for r in self.p]
        result = self.run_audit()
        self.assertEqual(self.check(result, '14.2')['result'], 'Human check')
        self.assertEqual(self.check(result, '14.6')['result'], 'Human check')

    def test_disabled_module_writes_nothing(self):
        self.assertTrue(ENGINE.exists(), 'Missing CSV-to-findings automation engine')
        path = self.base / 'disabled.json'; path.write_text('{"checks":{"pagination":false}}', encoding='utf-8')
        proc = subprocess.run([sys.executable, str(ENGINE), '--config', str(path), '--run-dir', str(self.base / 'run')], capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse((self.base / 'run').exists())

    def test_malformed_absolute_canonical_does_not_resolve_to_self(self):
        self.p[1][3] = 'https://'
        result = self.run_audit()
        self.assertEqual(self.check(result, '14.2')['result'], 'X')
        self.assertEqual(self.check(result, '14.6')['result'], 'X')

    def test_unclosed_csv_quote_is_read_error_not_clean_result(self):
        (self.base / 'broken.csv').write_text('Address,Canonical Link Element 1,rel next,rel prev,Extra\nhttps://example.com/products?page=2,/products?page=2,/products,,"unterminated', encoding='utf-8')
        result = self.run_audit({'exports': {'pagination': 'broken.csv'}})
        self.assertEqual(self.check(result, '14.2')['result'], 'Human check')
        self.assertEqual(self.check(result, '14.3')['result'], 'Human check')


if __name__ == '__main__': unittest.main()

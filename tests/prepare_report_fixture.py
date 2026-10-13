"""Create clearly synthetic raw exports and exercise the CLI for visual QA."""
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'runs' / 'synthetic-report-qa'
base.mkdir(parents=True, exist_ok=True)

def export(name, fields, rows):
    with (base / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(fields); writer.writerows(rows)

export('pagination_all.csv', ['Address', 'rel="next" 1', 'rel="prev" 1', 'Canonical Link Element 1'], [
    ['https://example.com/products', '/products?page=2', '', '/products'],
    ['https://example.com/products?page=2', '', '/products', '/products'],
    ['https://example.com/news?page=2', '', '', ''],
])
export('internal_all.csv', ['Address', 'Status Code', 'Redirect URI', 'Canonical Link Element 1', 'Indexability', 'Indexability Status'], [
    ['https://example.com/products', '200', '', '/products', 'Indexable', ''],
    ['https://example.com/products?page=2', '200', '', '/products', 'Indexable', ''],
    ['https://example.com/products?page=1', '200', '', '?page=1', 'Indexable', ''],
    ['https://example.com/news?page=2', '200', '', '', 'Indexable', ''],
    ['https://example.com/other', '200', '', '/other', 'Indexable', ''],
])
export('near_duplicate_pairs.csv', ['Address', 'Near Duplicate Address', 'Similarity'], [
    ['https://example.com/news?page=2', 'https://example.com/other', '96']
])
config = {'site': {'name': 'Synthetic QA', 'start_url': 'https://example.com/'},
          'source': {'export_directory': '.'}, 'checks': {'pagination': True, 'live_checks': False},
          'output': {'audit_date': '2026-10-12', 'language': 'zh', 'archive_raw': True}}
path = base / 'config.json'; path.write_text(json.dumps(config), encoding='utf-8')
subprocess.run([sys.executable, str(ROOT/'scripts'/'audit.py'), '--config', str(path), '--run-dir', str(base / 'audit')], check=True)

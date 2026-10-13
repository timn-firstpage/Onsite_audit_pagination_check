"""Deterministic owner-selected pagination rules. Reads CSV only; never crawls."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import unicodedata
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

ITEMS = [
    'Are there on-page links to page 2 and onward? (can be hidden with CSS for users if ajax is being used)',
    'Is the client having both a “View All” page and paginated pages without a correct rel=canonical?',
    'Are rel=”prev” and rel=”next” link attributes being used, so that Google knows to consolidate the ranking signals?',
    'Does the client have a page=1 in addition to the root page? (This is wrong if no canonical)',
    'Caused Duplication? (Even if your H1 etc are the same, the actual page content differs, it’s not duplication)',
    'On paginated content, does the canonical tag always refer to the page itself?',
]
FILES = {
    'pagination': ['pagination_all.csv', 'pagination.csv'],
    'first_page': ['pagination_first_page.csv', 'first_page.csv'],
    'paginated_2_plus': ['pagination_paginated_2_plus_pages.csv', 'paginated_2_plus_pages.csv'],
    'internal': ['internal_all.csv'],
    'near_duplicate_pairs': ['near_duplicate_pairs.csv', 'content_near_duplicate_pairs.csv'],
}


def header(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKC', value).lower())


def text(value):
    value = str(value or '').strip()
    return '' if value.lower() in {'null', 'none', 'nan'} else value


def field(row, *names):
    for name in names:
        if header(name) in row:
            return text(row[header(name)])
    return ''


def has(row, *names):
    return any(header(name) in row for name in names)


def key(url):
    p = urlsplit(text(url))
    if p.scheme.lower() not in {'http', 'https'} or not p.hostname:
        raise ValueError(f'Invalid HTTP URL: {url}')
    # Compare query order, retaining all parameter values; never collapse path slashes.
    port = p.port
    authority = p.netloc.lower()
    if (p.scheme.lower(), port) in {('https', 443), ('http', 80)}:
        authority = authority.rsplit(':', 1)[0]
    return urlunsplit((p.scheme.lower(), authority, p.path or '/', urlencode(sorted(parse_qsl(p.query, keep_blank_values=True))), p.fragment))


def page_one_root(url):
    p = urlsplit(url)
    params = parse_qsl(p.query, keep_blank_values=True)
    if not any(k == 'page' and v == '1' for k, v in params):
        return None
    remaining = [(k, v) for k, v in params if not (k == 'page' and v == '1')]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(remaining), p.fragment))


def preferred(url, tracking):
    p = urlsplit(url)
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
              if not k.lower().startswith('utm_') and k.lower() not in tracking
              and not (k == 'page' and v == '1')]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(params), p.fragment))


def canonical_columns(columns):
    return [c for c in columns if re.fullmatch(r'(canonicallinkelement|httpcanonical|canonicalurl|canonical)\d*', c)]


def relation_columns(columns, relation):
    return [c for c in columns if re.fullmatch(rf'(http)?rel{relation}\d*', c)]


def canonical_problem(row, expected):
    address = field(row, 'Address')
    cols = canonical_columns(row)
    if not cols:
        raise ValueError('Missing canonical column (empty canonical values are different from absent columns).')
    values = [text(row[c]) for c in cols if text(row[c])]
    if not values:
        return 'Missing canonical', values
    try:
        for value in values:
            declared = urlsplit(value)
            if re.search(r'\s', value) or (declared.scheme and
                    (declared.scheme.lower() not in {'http', 'https'} or not declared.hostname)):
                return 'Invalid canonical URL', values
            if value.startswith('//') and not declared.hostname:
                return 'Invalid canonical URL', values
        resolved = {key(urljoin(address, c)) for c in values}
    except ValueError:
        return 'Invalid canonical URL', values
    if len(resolved) > 1:
        return 'Conflicting canonical declarations', values
    if resolved != {key(expected)}:
        return f'Canonical should point to {expected}', values
    return None, values


def read_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, strict=True)
        if not reader.fieldnames:
            raise ValueError('CSV has no header.')
        cols = [header(c) for c in reader.fieldnames]
        if len(set(cols)) != len(cols):
            raise ValueError('CSV has ambiguous duplicate column names.')
        rows = []
        for number, raw in enumerate(reader, 2):
            if None in raw:
                raise ValueError(f'CSV row {number} has extra fields.')
            if any(v is None for v in raw.values()):
                raise ValueError(f'CSV row {number} is truncated.')
            row = {header(k): text(v) for k, v in raw.items()}
            if any(row.values()):
                rows.append(row)
    return cols, rows


def issue(address, reason, instruction, target='', **extra):
    return {'address': address, 'issue': reason, 'instruction': instruction, 'target': target, **extra}


def translated(language, zh, en):
    return zh if language.lower().startswith('zh') else en


def evaluate(config, tables, errors):
    lang = config.get('output', {}).get('language', 'zh')
    tr = lambda zh, en: translated(lang, zh, en)
    site_url = config['site']['start_url']
    tracking = {str(k).lower() for k in config.get('pagination', {}).get('tracking_parameters', ['gclid', 'fbclid', 'msclkid'])}
    checks = []

    def add(n, issues, problems, finding, instruction=None, evidence=None):
        result = 'X' if issues else ('Human check' if problems else '√')
        if issues:
            finding = tr(f'发现 {len(issues)} 条问题。', f'Found {len(issues)} issues.') + ' ' + finding
        if problems:
            finding += ' ' + tr('读取／字段错误：', 'Read/field error: ') + '; '.join(sorted(set(problems)))
        action = instruction or (tr('请修正明细中的问题。', 'Correct the listed issues.') if issues else
                                 tr('请补充或修正对应 SF export。', 'Supply or correct the affected SF export.') if problems else
                                 tr('无需处理。', 'No action needed.'))
        checks.append({'id': f'14.{n}', 'item_name': ITEMS[n - 1], 'result': result,
                       'finding': finding, 'instruction': action, 'evidence': evidence or [],
                       'evidence_state': 'partial' if problems else 'available', 'issues': issues})

    checks.append({'id': '14.1', 'item_name': ITEMS[0], 'result': 'Human check',
                   'finding': tr('按约定跳过自动检查，默认人工核验。', 'Automatic checking skipped by agreement; manual review required.'),
                   'instruction': tr('请检查实际下一页链接；最后一页无需 next，AJAX 页面需检查可抓取的分页链接。',
                                     'Check actual onward anchor links, including AJAX pagination; the final page needs no next link.'),
                   'evidence': [], 'evidence_state': 'not_applicable', 'issues': []})

    pages = tables.get('pagination', ([], []))[1]
    internal = tables.get('internal', ([], []))[1]
    indexed = {}
    internal_errors = list(errors.get('internal', []))
    for row in internal:
        address = field(row, 'Address')
        try:
            urlkey = key(address)
            if urlkey in indexed and indexed[urlkey] != row:
                raise ValueError(f'Conflicting Internal rows for {address}')
            indexed[urlkey] = row
        except ValueError as exc:
            internal_errors.append(str(exc))

    canon_issues = []; canon_errors = list(errors.get('pagination', []))
    canonical_cols = canonical_columns(tables.get('pagination', ([], []))[0])
    if 'pagination' in tables and not canonical_cols:
        canon_errors.append('Pagination: missing canonical column')
    seen = set()
    for row in pages:
        address = field(row, 'Address')
        try:
            sig = (key(address), tuple(text(row[c]) for c in canonical_columns(row)))
            if sig in seen: continue
            seen.add(sig)
            expected = preferred(address, tracking)
            reason, values = canonical_problem(row, expected)
            if reason:
                canon_issues.append(issue(address, reason + '; canonical=' + (' | '.join(values) or '(empty)'),
                                          tr(f'请将 canonical 指向 {expected}，并移除冲突声明。', f'Set the canonical to {expected} and remove conflicting declarations.'),
                                          expected, canonical=values))
        except ValueError as exc:
            canon_errors.append(f'{address}: {exc}')
    canon_finding = tr('按提供的分页记录检查 canonical；View All 不参与判断。',
                      'Canonical check uses the supplied pagination records; View All is excluded.')
    add(2, canon_issues.copy(), canon_errors, canon_finding, evidence=['pagination'])

    annotation_issues = []; annotation_errors = list(errors.get('pagination', []))
    cols = tables.get('pagination', ([], []))[0]
    nextcols = relation_columns(cols, 'next'); prevcols = relation_columns(cols, 'prev')
    if 'pagination' in tables and (not nextcols or not prevcols):
        annotation_errors.append('Pagination: missing rel=next or rel=prev column')
    else:
        for row in pages:
            if not any(text(row.get(c, '')) for c in nextcols + prevcols):
                annotation_issues.append(issue(field(row, 'Address'), 'rel=next and rel=prev are both empty.',
                                              tr('如需满足本项标记检查，请为该页添加正确的 prev 或 next 关系。', 'Add the correct prev or next relation to satisfy this markup-presence check.')))
        if 'pagination' in tables and not pages and not annotation_errors:
            annotation_issues.append(issue(site_url, 'No prev/next annotations found in the supplied pagination result.',
                                          tr('请确认网站是否采用 prev／next 标记。', 'Confirm whether the site uses prev/next annotations.')))
    add(3, annotation_issues, annotation_errors,
        tr('任一 prev／next 有值即通过；这是标记存在检查，Google 已不再用它归并排名信号。',
           'Either prev or next suffices. This checks markup presence; Google no longer uses it to consolidate ranking signals.'),
        evidence=['pagination'])

    alias_issues = []; alias_errors = list(internal_errors); aliases = 0; root_absent = 0
    for row in internal:
        address = field(row, 'Address')
        root = page_one_root(address)
        if root is None: continue
        aliases += 1
        try:
            if key(root) not in indexed:
                root_absent += 1; continue
            if not has(row, 'Status Code'):
                raise ValueError('Missing Status Code column')
            status = field(row, 'Status Code')
            if status in {'301', '308'}:
                dest = field(row, 'Redirect URI', 'Redirect URL')
                if not has(row, 'Redirect URI', 'Redirect URL'):
                    raise ValueError('Missing Redirect URI column')
                chain_seen = {key(address)}
                while dest:
                    resolved = urljoin(address, dest)
                    if key(resolved) == key(root): break
                    if key(resolved) in chain_seen: break
                    chain_seen.add(key(resolved))
                    middle = indexed.get(key(resolved))
                    if not middle or field(middle, 'Status Code') not in {'301', '308'}: break
                    address_for_join = field(middle, 'Address')
                    dest = urljoin(address_for_join, field(middle, 'Redirect URI', 'Redirect URL')) if field(middle, 'Redirect URI', 'Redirect URL') else ''
                if not dest or key(urljoin(address, dest)) != key(root):
                    alias_issues.append(issue(address, f'page=1 does not permanently redirect to root {root}; redirect={dest or "(empty)"}',
                                              tr(f'请将该版本永久跳转到 {root}。', f'Permanently redirect this version to {root}.'), root))
            elif status == '200':
                reason, values = canonical_problem(row, root)
                if reason:
                    alias_issues.append(issue(address, f'{reason}; root={root}; canonical=' + (' | '.join(values) or '(empty)'),
                                              tr(f'请将 page=1 的 canonical 指向 {root}。', f'Point the page=1 canonical to {root}.'), root, canonical=values))
            elif status not in {'404', '410'}:
                alias_errors.append(f'{address}: status {status or "(empty)"}; consolidation not verified')
        except ValueError as exc:
            alias_errors.append(f'{address}: {exc}')
    add(4, alias_issues, alias_errors,
        tr(f'检查 {aliases} 条 page=1；其中 {root_absent} 条 root 未出现在提供的数据中，不触发问题。',
           f'Checked {aliases} page=1 records; {root_absent} roots absent from supplied data do not trigger an issue.'),
        evidence=['internal'])

    pair_issues = []; pair_errors = list(errors.get('near_duplicate_pairs', [])) + internal_errors + list(errors.get('pagination', []))
    pair_cols, pairs = tables.get('near_duplicate_pairs', ([], []))
    source_names = ('Address', 'Source', 'URL')
    target_names = ('Near Duplicate Address', 'Near Duplicate URL', 'Duplicate Address', 'Duplicate URL', 'Destination', 'Matched URL')
    if 'near_duplicate_pairs' in tables and (not has(dict.fromkeys(pair_cols), *source_names) or not has(dict.fromkeys(pair_cols), *target_names)):
        pair_errors.append('Near Duplicates requires source and matched URL columns, not only a similarity count.')
    pagination_keys = set()
    for row in pages:
        try: pagination_keys.add(key(field(row, 'Address')))
        except ValueError: pass
    pair_seen = set()
    for pair in pairs:
        a = field(pair, *source_names); b = field(pair, *target_names)
        try:
            ka, kb = key(a), key(b)
            if ka not in pagination_keys and kb not in pagination_keys: continue
            signature = tuple(sorted((ka, kb)))
            if ka == kb or signature in pair_seen: continue
            pair_seen.add(signature)
            # SF duplicate rows need Indexability for BOTH endpoints, usually joined from Internal All.
            endpoints = []
            for endpoint in (ka, kb):
                r = indexed.get(endpoint)
                if not r or not has(r, 'Indexability') or not field(r, 'Indexability'):
                    raise ValueError(f'No Indexability record for {endpoint}')
                if not has(r, 'Indexability Status', 'Canonicalised', 'Canonicalized'):
                    raise ValueError(f'No canonicalised-state field for {endpoint}')
                status = field(r, 'Indexability Status').lower()
                explicit = field(r, 'Canonicalised', 'Canonicalized')
                endpoints.append(field(r, 'Indexability').lower() == 'indexable'
                                 and not explicit and 'canonicalis' not in status and 'canonicaliz' not in status)
            if all(endpoints):
                if ka not in pagination_keys: a, b = b, a
                similarity = field(pair, 'Similarity', 'Similarity Match', 'Closest Similarity Match')
                pair_issues.append(issue(a, f'SF near-duplicate pair: {b}; both Indexable, no Canonicalised status' + (f'; similarity={similarity}' if similarity else ''),
                                         tr('请核对该配对的主要内容；若内容等价，请归并到正确版本。', 'Review the main content of this pair and consolidate equivalent versions where appropriate.'), b,
                                         rule='sf_near_duplicate_pair_screen', similarity=similarity))
        except ValueError as exc:
            pair_errors.append(str(exc))
    add(5, pair_issues, pair_errors,
        tr('按 SF Near Duplicates 配对规则筛查；不因相同 H1／Title 单独判重复，也不声称已验证正文完全相同。',
           'Screened SF Near Duplicate pairs; matching H1/title alone is not duplication, and identical main content is not asserted.'),
        evidence=['pagination', 'internal', 'near_duplicate_pairs'])
    add(6, canon_issues.copy(), canon_errors,
        tr('复用 14.2 的首选分页 URL 判断；page=1 可归并 root，追踪参数可归并同一分页。',
           'Reuses 14.2 preferred-pagination decisions; page=1 may consolidate to root and tracking variants to the same page.'),
        evidence=['pagination'])
    return checks


def load_tables(config, base, export_dir):
    mapping = config.get('pagination', {}).get('exports', {})
    if not isinstance(mapping, dict): raise ValueError('pagination.exports must be an object')
    metadata = {}; tables = {}; errors = {}

    def load(role):
        explicit = mapping.get(role)
        if explicit:
            path = Path(explicit); path = path if path.is_absolute() else base / path
        else:
            candidates = [export_dir / name for name in FILES[role] if (export_dir / name).is_file()]
            if len(candidates) > 1:
                errors[role] = [f'{role}: ambiguous export files; set pagination.exports.{role}']; return
            if not candidates:
                errors[role] = [f'{role}: export not supplied']; return
            path = candidates[0]
        try:
            cols, rows = read_csv(path)
            if role != 'near_duplicate_pairs' and 'address' not in cols:
                raise ValueError('Missing Address column')
            tables[role] = (cols, rows)
            metadata[role] = {'path': str(path.resolve()), 'rows': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        except (OSError, ValueError, UnicodeError, csv.Error) as exc:
            errors[role] = [f'{role}: {exc}']

    if mapping.get('first_page') or mapping.get('paginated_2_plus') or (not mapping.get('pagination') and not any((export_dir / n).is_file() for n in FILES['pagination']) and any((export_dir / n).is_file() for n in FILES['first_page'] + FILES['paginated_2_plus'])):
        load('first_page'); load('paginated_2_plus')
        columns = sorted(set(tables.get('first_page', ([], []))[0]) | set(tables.get('paginated_2_plus', ([], []))[0]))
        # Missing fields must not disappear when two differently shaped exports are joined.
        if 'first_page' in tables and 'paginated_2_plus' in tables and set(tables['first_page'][0]) != set(tables['paginated_2_plus'][0]):
            errors['pagination'] = ['First Page and Paginated 2+ export headers differ; export the same columns.']
        errors['pagination'] = errors.get('pagination', []) + errors.get('first_page', []) + errors.get('paginated_2_plus', [])
        if tables.get('first_page') or tables.get('paginated_2_plus'):
            tables['pagination'] = (columns, tables.get('first_page', ([], []))[1] + tables.get('paginated_2_plus', ([], []))[1])
    else:
        load('pagination')
    load('internal'); load('near_duplicate_pairs')
    return tables, errors, metadata


def safe_csv(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def write_csv(path, columns, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(columns)
        writer.writerows([[safe_csv(v) for v in row] for row in rows])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--exports-dir', type=Path)
    parser.add_argument('--run-dir', type=Path, help='Shared run directory; writes only its pagination/ child.')
    parser.add_argument('--site-url'); parser.add_argument('--site-name'); parser.add_argument('--date')
    args = parser.parse_args(argv)
    base = args.config.resolve().parent if args.config else Path.cwd()
    config = json.loads(args.config.read_text(encoding='utf-8-sig')) if args.config else {}
    if not isinstance(config, dict): raise ValueError('Config must be an object')
    if config.get('checks', {}).get('pagination', True) is False:
        print('Pagination disabled; no files written.'); return 0
    site = config.setdefault('site', {})
    if args.site_url: site['start_url'] = args.site_url
    if args.site_name: site['name'] = args.site_name
    if not site.get('start_url') or not site.get('name'):
        raise ValueError('Supply site.start_url and site.name (or --site-url / --site-name).')
    key(site['start_url'])
    source = config.get('source', {})
    exp = args.exports_dir or Path(source.get('export_directory') or '.')
    export_dir = exp if exp.is_absolute() else base / exp
    output = config.get('output', {})
    date = args.date or output.get('audit_date')
    if not date:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        zone = output.get('timezone') or 'Asia/Hong_Kong'
        try: tz = ZoneInfo(zone)
        except ZoneInfoNotFoundError:
            if zone != 'Asia/Hong_Kong': raise ValueError(f'Timezone data unavailable: {zone}; supply output.audit_date')
            tz = timezone(timedelta(hours=8))
        date = datetime.now(tz).date().isoformat()
    datetime.strptime(date, '%Y-%m-%d')
    run = args.run_dir
    if run is None:
        root = Path(output.get('run_root') or 'runs')
        root = root if root.is_absolute() else base / root
        run = root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    elif not run.is_absolute(): run = base / run
    dest = run / 'pagination'
    if dest.exists(): raise ValueError(f'Output already exists; use a new run directory: {dest}')
    tables, errors, metadata = load_tables(config, base, export_dir)
    checks = evaluate(config, tables, errors)
    dest.mkdir(parents=True)
    for role, entry in metadata.items():
        if output.get('archive_raw', True):
            raw = dest / 'raw'; raw.mkdir(exist_ok=True)
            target = raw / (role + '.csv'); shutil.copyfile(entry['path'], target)
            entry['archive'] = str(target.relative_to(dest))
    findings = {'site_name': site['name'], 'site_url': site['start_url'], 'audit_date': date,
                'language': output.get('language', 'zh'), 'checks': checks}
    # Replace symbolic export roles with actual evidence references.
    for check in checks:
        refs = []
        for role in check['evidence']:
            roles = ['first_page', 'paginated_2_plus'] if role == 'pagination' and 'pagination' not in metadata else [role]
            refs += [metadata[r].get('archive', metadata[r]['path']) for r in roles if r in metadata]
        check['evidence'] = list(dict.fromkeys(refs))
    manifest = {'module': 'pagination', 'scope_policy': 'supplied SF records are the agreed complete audit scope',
                'config_path': str(args.config.resolve()) if args.config else None,
                'source': source, 'crawl_timestamp': source.get('crawl_timestamp'), 'exports': metadata, 'errors': errors,
                'calls_made': {'mcp': 0, 'live': 0, 'paid': 0}, 'pagination_rows': len(tables.get('pagination', ([], []))[1])}
    (dest / 'findings.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding='utf-8')
    (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(dest / 'Checklist.csv', ['Item No.', 'Item Name', 'Check Result', 'Findings', 'Instruction'],
              [[c['id'], c['item_name'], c['result'], c['finding'], c['instruction']] for c in checks])
    details = {}
    for check in checks:
        for item in check['issues']:
            sig = (item['address'], item['issue'], item['instruction'])
            details.setdefault(sig, []).append(check['id'])
    write_csv(dest / 'issues.csv', ['Address', 'Issue', 'Instruction'],
              [[a, '/'.join(ids) + ': ' + reason, action] for (a, reason, action), ids in details.items()])
    print(str(dest / 'findings.json'))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Pagination audit error: {exc}', file=sys.stderr)
        raise SystemExit(2)

import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import fs from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const source = new URL('../scripts/build_report.mjs', import.meta.url);

function fixture() {
  return {site_name: '=Example', audit_date: '2026-10-12', checks: Array.from({length: 6}, (_, i) => ({
    id: `14.${i + 1}`, item_name: 'Check', result: i === 0 ? 'Human check' : '√',
    finding: 'Finding', instruction: 'Action', issues: []
  }))};
}

test('clean audit produces only Checklist with all six IDs', async () => {
  assert.ok(existsSync(source), 'Missing report builder');
  const {reportRows} = await import(source);
  const rows = reportRows(fixture());
  assert.deepEqual(Object.keys(rows), ['Checklist']);
  assert.deepEqual(rows.Checklist.slice(1).map(row => row[0]), ['14.1','14.2','14.3','14.4','14.5','14.6']);
});

test('shared canonical defect appears once with both item IDs', async () => {
  assert.ok(existsSync(source), 'Missing report builder');
  const {reportRows} = await import(source);
  const f = fixture();
  const issue = {address: 'https://example.com/?page=2', issue: 'Missing canonical', instruction: '=literal text'};
  for (const i of [1, 5]) {f.checks[i].result = 'X'; f.checks[i].issues = [issue];}
  const rows = reportRows(f);
  assert.equal(rows['14. Pagination'].length, 2);
  assert.equal(rows['14. Pagination'][1][1], '14.2/14.6: Missing canonical');
  assert.equal(rows['14. Pagination'][1][2], "'=literal text");
});

test('invalid X without issues and missing checklist row are rejected', async () => {
  assert.ok(existsSync(source), 'Missing report builder');
  const {reportRows} = await import(source);
  const f = fixture(); f.checks[1].result = 'X';
  assert.throws(() => reportRows(f), /issue/i);
  f.checks.pop();
  assert.throws(() => reportRows(f), /six|6/i);
});

test('preview rendering cannot turn a verified report into CLI failure', {skip: !process.env.AUDIT_NODE_MODULES}, async () => {
  const root = fileURLToPath(new URL('../runs/report-cli-tests/', import.meta.url));
  await fs.mkdir(root, {recursive:true});
  const dir = await fs.mkdtemp(path.join(root, 'qa-'));
  const f = fixture(); f.site_name = 'Report CLI QA';
  await fs.writeFile(path.join(dir,'findings.json'), JSON.stringify(f));
  const result = spawnSync(process.execPath, [fileURLToPath(source),'--input',path.join(dir,'findings.json'),'--node-modules',process.env.AUDIT_NODE_MODULES,'--preview'], {encoding:'utf8',timeout:60000,windowsHide:true});
  assert.equal(result.status,0,result.stderr);
  assert.ok(existsSync(path.join(dir,'Report CLI QA_onsite_pagination_audit_2026-10-12.xlsx')));
  const preview = JSON.parse(await fs.readFile(path.join(dir,'preview-status.json'),'utf8'));
  assert.ok(['rendered','rendered_with_exit_error','unavailable'].includes(preview.state));
  assert.equal(JSON.parse(await fs.readFile(path.join(dir,'report-verification.json'),'utf8')).checklistRows,6);
});

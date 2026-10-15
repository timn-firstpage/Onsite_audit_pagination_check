import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const literal = value => /^[\s]*[=+@-]/.test(String(value)) ? "'" + String(value) : String(value);

export function reportFilename(siteName, auditDate) {
  const cleanName = String(siteName || 'Site').replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').replace(/[. ]+$/g, '').slice(0, 100) || 'Site';
  if (!/^\d{4}-\d{2}-\d{2}$/.test(auditDate)) throw new Error('Invalid audit date.');
  return `14.1-14.6_${cleanName}_onsite_pagination_audit_${auditDate}.xlsx`;
}

export function reportRows(findings) {
  if (!Array.isArray(findings.checks) || findings.checks.length !== 6) throw new Error('Exactly six checklist rows required.');
  const rows = {Checklist: [['Item No.', 'Item Name', 'Check Result', 'Findings', 'Instruction']]};
  const details = new Map();
  for (let i = 0; i < 6; i++) {
    const c = findings.checks[i];
    if (c.id !== `14.${i + 1}`) throw new Error('Checklist IDs must be 14.1–14.6 in order.');
    if (!['√', 'X', 'Human check', 'N/A'].includes(c.result)) throw new Error('Invalid result.');
    if (i === 0 && c.result !== 'Human check') throw new Error('14.1 must remain Human check.');
    if (i === 2 && c.result === 'N/A') throw new Error('14.3 must not use N/A.');
    for (const field of ['item_name','finding','instruction']) {
      if (typeof c[field] !== 'string' || !c[field].trim()) throw new Error(`Missing ${field}.`);
    }
    if (!Array.isArray(c.issues) || (c.result === 'X' ? !c.issues.length : c.issues.length)) throw new Error('X requires issues; other statuses have none.');
    rows.Checklist.push([c.id, c.item_name, c.result, c.finding, c.instruction].map(literal));
    for (const issue of c.issues) {
      for (const field of ['address','issue','instruction']) {
        if (typeof issue[field] !== 'string' || !issue[field].trim()) throw new Error(`Missing issue ${field}.`);
      }
      const key = JSON.stringify([issue.address, issue.issue, issue.instruction]);
      if (!details.has(key)) details.set(key, {issue, ids: []});
      details.get(key).ids.push(c.id);
    }
  }
  if (details.size) rows['14. Pagination'] = [['Address','Issue','Instruction'], ...Array.from(details.values(), ({issue, ids}) =>
    [issue.address, `${ids.join('/')}: ${issue.issue}`, issue.instruction].map(literal))];
  return rows;
}

async function artifactLibrary(modules) {
  if (modules) {
    const require = createRequire(path.join(path.resolve(modules), '..', 'pagination-loader.cjs'));
    return import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
  }
  return import('@oai/artifact-tool');
}

async function renderOnly(input, outputDir, modules, includeIssues) {
  const {SpreadsheetFile, FileBlob} = await artifactLibrary(modules);
  const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(input));
  for (const [sheetName, name] of [['Checklist','checklist-preview.png'], ...(includeIssues ? [['14. Pagination','pagination-issues-preview.png']] : [])]) {
    const png = await wb.render({sheetName, autoCrop:'all', scale:1, format:'png'});
    await fs.writeFile(path.join(outputDir, name), new Uint8Array(await png.arrayBuffer()));
  }
}

export async function buildReport(findings, outputDir, modules, preview = false) {
  const rows = reportRows(findings);
  const {Workbook, SpreadsheetFile, FileBlob} = await artifactLibrary(modules);
  const wb = Workbook.create();
  for (const [name, data] of Object.entries(rows)) {
    const sheet = wb.worksheets.add(name);
    const end = name === 'Checklist' ? 'E' : 'C';
    sheet.showGridLines = false;
    const area = sheet.getRange(`A1:${end}${data.length}`);
    area.values = data;
    area.format.font = {name: 'Arial', size: 11};
    area.format.wrapText = true;
    area.format.verticalAlignment = 'top';
    const head = sheet.getRange(`A1:${end}1`);
    head.format.fill = '#203B53';
    head.format.font = {name: 'Arial', size: 11, color: '#FFFFFF', bold: true};
    head.format.horizontalAlignment = 'center';
    head.format.rowHeightPx = 30;
    const widths = name === 'Checklist' ? [85, 360, 115, 430, 430] : [370, 610, 430];
    widths.forEach((width, i) => sheet.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}${data.length}`).format.columnWidthPx = width);
    for (let r = 1; r < data.length; r++) {
      const lines = Math.max(...data[r].map((cell, i) => String(cell).split('\n').reduce((n, line) => n + Math.max(1, Math.ceil(Array.from(line).reduce((n,c) => n + (c.charCodeAt(0)>255?2:1),0) / (widths[i]/7))), 0)));
      sheet.getRange(`A${r+1}:${end}${r+1}`).format.rowHeightPx = Math.max(60, lines * 17 + 16);
      if (r % 2 === 0) sheet.getRange(`A${r+1}:${end}${r+1}`).format.fill = '#F2F5F8';
    }
    sheet.freezePanes.freezeRows(1);
    if (name === 'Checklist') {
      const statuses = sheet.getRange('C2:C7');
      statuses.format.horizontalAlignment = 'center';
      for (const [status, fill, color] of [['X','#FDE8E7','#A12A22'], ['Human check','#FFF0CE','#815500']]) {
        statuses.conditionalFormats.add('containsText', {text: status, format: {fill, font: {bold: true, color}}});
      }
    }
  }
  const reportName = reportFilename(findings.site_name, findings.audit_date);
  await fs.mkdir(outputDir, {recursive: true});
  const filename = path.join(outputDir, reportName);
  try {await fs.access(filename); throw new Error(`Refusing to overwrite ${filename}`);} catch (error) {if (error.code !== 'ENOENT') throw error;}
  wb.recalculate();
  const file = await SpreadsheetFile.exportXlsx(wb);
  await file.save(filename);
  const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(filename));
  const summary = await reopened.inspect({kind:'sheet', include:'id,name', maxChars:3000});
  const verification = {filename, sheets: Object.keys(rows), checklistRows:6, issueRows:rows['14. Pagination']?.length - 1 || 0, sheetInspection:summary.ndjson ?? summary};
  for (const [name, data] of Object.entries(rows)) {
    const sheet = reopened.worksheets.getItem(name);
    const end = name === 'Checklist' ? 'E' : 'C';
    const readback = sheet.getRange(`A1:${end}${data.length}`).values;
    if (readback.length !== data.length) throw new Error(`Row count mismatch: ${name}`);
    for (let r = 0; r < data.length; r++) for (let c = 0; c < data[r].length; c++) {
      // Excel's leading quote may be consumed as a text marker on import.
      const expected = String(data[r][c]); const actual = String(readback[r][c] ?? '');
      if (actual !== expected && !(expected.startsWith("'") && actual === expected.slice(1))) throw new Error(`Readback mismatch: ${name} row ${r+1}`);
    }
    if (sheet.getRange(`A1:${end}${data.length}`).formulas.some(row => row.some(Boolean))) throw new Error('Unexpected formula in report.');
  }
  await fs.writeFile(path.join(outputDir, 'report-verification.json'), JSON.stringify(verification,null,2));
  if (preview) {
    // Isolate the optional native renderer. On Windows its shutdown can crash
    // AFTER PNGs are saved; this must not kill verified workbook generation.
    const renderArgs = [fileURLToPath(import.meta.url), '--render-only', '--input', filename, '--output-dir', outputDir];
    if (modules) renderArgs.push('--node-modules', modules);
    const includeIssues = rows['14. Pagination'] && rows['14. Pagination'].length <= 31;
    if (includeIssues) renderArgs.push('--issues-preview');
    const child = spawnSync(process.execPath, renderArgs, {encoding:'utf8',timeout:60000,windowsHide:true,maxBuffer:1024*1024});
    const names = ['checklist-preview.png', ...(includeIssues ? ['pagination-issues-preview.png'] : [])];
    const images = [];
    for (const name of names) {
      try {
        const bytes = await fs.readFile(path.join(outputDir, name));
        if (bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) images.push(name);
      } catch {}
    }
    const state = images.length !== names.length ? 'unavailable' : child.status === 0 ? 'rendered' : 'rendered_with_exit_error';
    await fs.writeFile(path.join(outputDir,'preview-status.json'), JSON.stringify({state, images, rendererExitCode:child.status, signal:child.signal, error:child.error?.message, stderr:(child.stderr||'').slice(-2000)},null,2));
    if (state !== 'rendered') console.warn(`Optional preview renderer: ${state}; verified workbook preserved. See preview-status.json.`);
  }
  return filename;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const args = process.argv.slice(2);
  const value = flag => args[args.indexOf(flag)+1];
  try {
    if (!args.includes('--input')) throw new Error('Usage: node build_report.mjs --input findings.json [--output-dir dir] [--node-modules bundled-path] [--preview]');
    const input = path.resolve(value('--input'));
    const outputDir = args.includes('--output-dir') ? path.resolve(value('--output-dir')) : path.dirname(input);
    const modules = args.includes('--node-modules') ? value('--node-modules') : undefined;
    if (args.includes('--render-only')) {
      await renderOnly(input, outputDir, modules, args.includes('--issues-preview'));
      console.log('Preview images written.');
    } else {
      const findings = JSON.parse(await fs.readFile(input, 'utf8'));
      console.log(await buildReport(findings, outputDir, modules, args.includes('--preview')));
    }
    process.exitCode = 0;
  } catch (error) {console.error(`Pagination report error: ${error.message}`); process.exitCode = 2;}
}

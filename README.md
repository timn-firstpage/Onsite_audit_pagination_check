# Onsite Pagination Audit

Reusable Codex skill for the owner's six Pagination checks, integrated with the shared onsite config and sf-shared-config saved-crawl workflow. 14.1 defaults to Human check; View All is skipped; supplied SF records are the scoring scope. No automatic crawl or website changes.

## Use

Install the runtime folder as `onsite-audit-pagination` in the user's skills directory. Invoke `$onsite-audit-pagination` with site/company, the existing global config and SF evidence. No additional Begin/Review intake or workbook template is needed. Source acquisition remains agent-owned; Python reads CSV exports only.

Required exports and actual header aliases: [exports](references/exports.md). Scoring: [rules](references/audit-rules.md). Shared configuration: [integration](references/shared-config.md). Workbook: [output](references/output-contract.md).

```text
python scripts/audit.py --config <config.json> --run-dir <shared-run>
node scripts/build_report.mjs --input <shared-run>/pagination/findings.json --node-modules <discovered-bundled-node_modules> --preview
```

Python requires 3.10+ and only its standard library. The XLSX builder uses the available spreadsheet skill's bundled Node and @oai/artifact-tool; discover these via load_workspace_dependencies. Run that skill's artifact-operation marker before creating a workbook. Nothing auto-installs dependencies. `output.language` supports zh and en; date uses the configured timezone or explicit date.

Runtime output: `<shared-run>/pagination/` with findings.json, manifest.json, raw exports when enabled, CSV intermediates, workbook and verification/preview. An existing module output is never overwritten. No supplied real site audit is implied by synthetic tests.

## Tests and packaging

```text
python -m unittest discover -s tests -v
node --test tests/report.test.mjs
python scripts/package_skill.py --output dist/onsite-audit-pagination.zip
```

The zip contains one `onsite-audit-pagination/` directory with skill instructions, config, references and runtime scripts. Excludes .git, local data, tests, dependencies and plans. Do not modify other onsite skills or automatically merge master-workbook history.

Set AUDIT_NODE_MODULES to the discovered bundled node_modules path to include the report CLI integration test; otherwise that dependency-specific test is skipped. Optional preview rendering is isolated in a child process. preview-status.json records image availability and any native-renderer exit error without discarding a verified workbook.

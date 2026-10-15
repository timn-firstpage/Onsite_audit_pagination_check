# Workbook and findings

Filename: `14.1-14.6_{site_name}_onsite_pagination_audit_{YYYY-MM-DD}.xlsx`. Prefix the covered checklist range; sanitize invalid filename characters; preserve prior files.

Always `Checklist`: **Item No. | Item Name | Check Result | Findings | Instruction**, six rows 14.1–14.6. Keep original item labels. No Coverage column. Findings are observations; Instruction is the next action, short and concrete. Use output.language (zh default). No-action passes use 无需处理。 / No action needed.

Create **14. Pagination** only when any result is X: **Address | Issue | Instruction**. Every X has issue records; other decisions do not. Prefix issues with relevant item IDs. Identical 14.2/14.6 defects are one detail row tagged 14.2/14.6. Copy actual source and counterpart/target URLs; do not create an issue row for skipped 14.1 or technical Human checks.

`findings.json` has site_name, site_url, audit_date, language, checks. Each check has id, item_name, result, finding, instruction, evidence_state, evidence and issues. Every issue has address, issue, instruction, target, with optional canonical values/similarity/rule. This schema is suitable for coordinator imports; manifest stores source/hash/count/date and partial-crawl provenance. Supplied scope is scoring scope; no claim of Google indexing or identical near-duplicate main content.

`scripts/audit.py` also writes Checklist.csv and issues.csv as intermediates. Always retain findings/manifest on a workbook error. The builder `scripts/build_report.mjs` validates all IDs/statuses and issue inclusion, writes literal strings, refuses overwrite, imports the saved XLSX and verifies cell values plus absence of formulas. Report-verification.json records verification. --preview renders Checklist; inspect it and representative issue rows for clipping. Use the spreadsheet skill's artifact-operation marker immediately before authoring, and discovered bundled dependencies via --node-modules. Do not install libraries into the bundled runtime.

Sheet formatting: readable widths, wrapped descriptions/URLs, header freeze, restrained X/Human check highlights. No screenshots column, cover tab, extra report sheets or prior-review D/E columns. Large complete issue lists remain in the workbook; renderer previews are not a replacement for full records.

Preview rendering runs in a separate process so a native renderer shutdown failure cannot terminate verified workbook creation. preview-status.json records renderer exit status and PNG availability; do not present a renderer failure as a workbook scoring error. Inspect available images; if absent use a supported workbook viewer or disclose unverified visual layout. The main builder still rejects export/readback failures.

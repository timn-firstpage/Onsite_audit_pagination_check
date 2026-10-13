---
name: onsite-audit-pagination
description: Use when checking onsite Pagination items 14.1–14.6 from an existing Screaming Frog session, saved crawl or CSV exports, especially alongside the shared onsite configuration and other audit workflows.
---

# Onsite Pagination Audit

Produce `{site name}_onsite_pagination_audit_{YYYY-MM-DD}.xlsx` using the owner's six agreed checks. Read [audit rules](references/audit-rules.md) and [exports](references/exports.md). **14.1 stays Human check. View All is skipped. Provided SF rows define the complete scope for scoring**; do not add site-wide completeness gates or browser/crawl requirements to these decisions. Only actual read/schema/tool errors need error-driven Human check.

## Shared evidence

Reuse the current global config, source and run; [config.template.json](config.template.json) is only a standalone fallback. Read [shared integration](references/shared-config.md) for saved-crawl Open, source precedence, cache and cumulative budgets. `checks.pagination=false` disables this flow. Do not reset sibling config, reload SF profiles, invent MCP operations or start a crawl. New preparation belongs to `sf-shared-config`; it owns user-run Start and handover.

Get site/name and matching exports from the selected session or saved crawl. Retain explicit paths and provenance, including crawl date. Complete native files and header-only empty reports are usable; missing files and missing columns are errors, not empty results. Export full pair URLs for Near Duplicates, not just similarity counts. Python consumes files only and needs no third-party library.

## Run

1. Resolve export roles using [CSV contract](references/exports.md). The pagination scope is First Page ∪ Paginated 2+ Pages; the equivalent Pagination:All file is also accepted. Internal:All supplies page=1/root matching and both duplicate endpoints' indexability state. No All Outlinks or anchor filter is needed because 14.1 is skipped.
2. Run `python scripts/audit.py --config <resolved-config.json> --run-dir <shared-run>`. Optional CLI overrides are `--exports-dir`, `--site-url`, `--site-name`, `--date`; relative paths resolve against the config directory. Output is isolated under `<shared-run>/pagination/`, refuses overwrite and includes findings/manifest, archived exports and CSV intermediates.
3. Read findings. 14.2 and 14.6 reuse preferred-URL canonical decisions; retain both checklist rows. 14.3 checks whether **either** next or prev has a value, with no N/A. 14.4 handles exact page=1 and root consolidation. 14.5 flags the owner's native SF near-duplicate pairs when both are Indexable and neither is canonicalised; it is a screening rule, not proof of identical main content. A nonempty self-canonical does not disqualify a pair.
4. Use the available Spreadsheets skill and its artifact-operation marker before authoring. Discover Node and `@oai/artifact-tool` through `load_workspace_dependencies`; never install packages into its runtime. Run `node scripts/build_report.mjs --input <findings.json> --node-modules <bundled-node_modules> --preview`. This renders and verifies the saved workbook. Use [output contract](references/output-contract.md), inspect the Checklist preview and issue layout, then deliver the workbook. Preserve findings if rendering/export fails.

Only X creates `14. Pagination`; duplicates shared by 14.2/14.6 appear once with both IDs. Findings state the observation; Instruction states the action. Keep six original item names and short configured-language findings. No Coverage column or historical D/E merge. A coordinator can consume findings separately without modifying sibling reports.

This invocation includes no live site repair, automatic crawling, scheduling, messaging, publishing or automatic dependency installation. Package/install mechanics and runnable commands are in [README](README.md).

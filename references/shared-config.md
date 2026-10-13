# Shared onsite integration

Consume the existing resolved global config without modifying it: site/source/mcp/budget/cache/output follow the HTTPS/robots/sitemap/hreflang/content conventions. This module adds only checks.pagination and pagination.exports/tracking_parameters. Ignore sibling check keys and preserve usage.json and sf-handover.json. Config.template.json is a fallback, not a profile or mandatory new intake.

Explicit current-session/saved-crawl evidence wins over stale configuration. Match site/crawl identity before using exports. A supplied partial crawl still defines the agreed scoring scope; record its scope/date in manifest, not a completeness-based Human check.

Use installed `sf-shared-config` ([repository](https://github.com/timn-firstpage/On-_site_SF_shared_config)) and its references/saved-crawl-entry.md for `.seospider`/`.dbseospider`. .seospiderconfig is configuration, not saved evidence. Discover actual SF tools and supported filters, preserve active/unsaved sessions, reuse cache or open the saved crawl once. Never deserialize arbitrary binaries. One SF instance must be operated serially across flows.

No reader/import failure: request File → Open of the saved crawl plus only the required exports once. Do not switch to Configuration → Load + Start or independent crawling. source.allow_new_crawl=false still allows saved-crawl reads/exports. Missing evidence requiring permitted new preparation belongs to sf-shared-config: it controls profile staging/loading, site/sitemap confirmation, user manual Start and saved-file handover. This module never starts/restarts a crawl or copies a separate SF profile.

checks.live_checks=false forbids new website/browser reads, not parsing files or supported MCP export transport. Even when true, this module's supplied-data rules need no new site requests. Source/MCP/export retrieval uses the coordinator's cumulative budget/cache and verified tool schemas; do not reset budgets per export/check. scripts/audit.py performs zero MCP/live/paid calls and never changes shared usage counters.

Paths resolve against the supplied config directory (CWD without config). Runtime and file access belong to the executing host; do not hardcode this owner's runtime, fixed MCP port or Downloads location. Default report date uses output.timezone, normally Asia/Hong_Kong; explicit output.audit_date/--date wins.

--run-dir is the shared run directory; write only its pagination/ child, refusing an existing child to preserve prior reports. With no run directory, create a unique run beneath output.run_root. Archive actual complete exports, hashes, source metadata and errors in pagination/manifest.json. Do not add a Coverage column or merge unrelated master-sheet history automatically. Coordinator integration consumes findings.json and issue records, then owns an explicitly requested master-workbook merge.

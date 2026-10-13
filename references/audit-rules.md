# Owner's six rules

Score exactly 14.1–14.6. √ = no failure under the supplied-data rule; X = a matching failure; Human check = explicitly skipped 14.1 or actual read/field/tool error. No extra completeness or coverage gates. Empty usable exports are valid; inaccessible files are not empty. Known failures take precedence over errors and retain the error disclosure. Findings are observations; Instruction is a short next action.

## 14.1 On-page onward links

Always Human check. Do not inspect All Outlinks, click AJAX, infer the last page or apply the earlier anchor/subset algorithm. Finding: “按约定跳过自动检查，默认人工核验。” Instruction: inspect actual onward anchors, hidden links if present, AJAX discovery and terminal-page exception. No issue rows.

## 14.2 Correct pagination canonical; skip View All

Scope = First Page ∪ Paginated 2+ Pages (or equivalent supplied Pagination:All). Do not screen for View All controls or treat coexistence as a defect. Preserve original item label but explain the active canonical test in Findings.

Each page expects its own preferred URL. Resolve relative canonicals. Drop only tracking parameters (`utm_*`, gclid, fbclid, msclkid by default; additional exact names configurable). Preserve filters, sort, locale and pagination. Query ordering is immaterial; path case/trailing slashes and www variants are not silently merged. page=1 may canonicalize to the same root with the page=1 parameter removed.

Missing canonical VALUE, invalid URL, conflicting HTML/HTTP targets or a target pointing to root/page 1/another numbered page/unrelated content instead of the expected URL => X. A missing canonical COLUMN is a technical input error => Human check. Equal resolved HTML/HTTP declarations are consistent, not conflicting. No live target fetches are required by this supplied-result rule.

Copy source Address, canonical value(s), expected URL and reason. Any X => whole check X; no issues in usable supplied rows (including zero rows) => √.

## 14.3 prev / next presence

Correct field name is rel, not ref. For each supplied pagination row: either rel=next OR rel=prev nonempty => pass. Both empty => X for that Address. Never require both tags; first and last pages can have one. The markup need not include anchors for this presence-only check. Accept the native numbered and smart-quoted header variants; distinguish empty cells from missing required columns.

No N/A: readable empty pagination results => X, “no annotations found in supplied pagination result,” using the site URL as the report reference. No SF read/schema errors => ordinary scoring; actual errors => Human check unless known X. Retain the user's markup checklist, but explicitly state Google no longer uses these tags to consolidate ranking signals. Do not claim absence harms Google rankings.

## 14.4 page=1 plus root

Read Internal:All and build an Address lookup. Parse query parameters, exact case-sensitive page=1 only (not page=10, arbitrary p=1 or page=01). Remove only page=1; preserve other parameters. Root absent from supplied records => no issue under owner's rule; do not open the website to find it.

Both present: page=1 permanently redirects (301/308, including a recorded all-permanent chain) to root => √. 200 alias with a single consistent canonical target to root => √. Missing/self/other/conflicting canonical => X. Permanent redirect to another destination or loop => X. 404/410 alias is not a served duplicate and does not fail. Other responses such as temporary redirect/failed response require Human check for consolidation, rather than pretending they fit a tested branch. No independent content-equivalence gate is imposed.

Copy page=1 source, derived root and canonical/redirect reason. No page=1 or no matching root is √ with actual counts stated.

## 14.5 Caused duplication — native pair screen

Use SF Content:Near Duplicates with actual Address/matched Address pairs. Similarity score or No. Near Duplicates alone cannot identify a pair. At least one endpoint must be in this audit's pagination set; ignore unrelated pairs. Join BOTH endpoints to Internal:All for Indexability and canonicalised-state fields. Deduplicate reversed pairs and self-pairs.

If both endpoints are Indexable and neither has Canonicalised/Canonicalized status (or a nonempty explicit Canonicalised field), flag X and copy both URLs. Otherwise do not flag the pair. **Canonicalised is a state, not Canonical Link Element**: both URLs may have nonempty self-canonicals and still match this rule. H1/title equality alone never flags this item.

This is the owner's automation heuristic. Report “SF near-duplicate pair; both Indexable; no canonicalised state,” not “verified identical main content” or “Google duplicate-content penalty.” Do not add manual main-content confirmation as a gate to X; recommend content review as the issue's action. Missing endpoint/state columns or pair export parse failure are technical errors, not invented clean results. A readable zero-row pair report yields √.

## 14.6 Self/preferred pagination canonical

Reuse exactly 14.2's canonical evaluation to prevent contradictory scoring. Include the separate original checklist item. Tracking aliases may point to the clean SAME numbered page; page=1 may point to root. Wrong/missing/conflicting canonicals => X. Shared defects appear once on the issue sheet, tagged 14.2/14.6.

## Standards context

Owner-selected scoring takes precedence over generic recommendations. Sources explain mechanics, not extra gates:

- [SF Pagination and Content fields](https://www.screamingfrog.co.uk/seo-spider/user-guide/tabs/): prev/next-based discovery, canonical data, minhash near duplicates and content-area dependence.
- [Google pagination](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading): separate preferred URLs and obsolete prev/next ranking consolidation.

Checked 2026-10-12. The local pair heuristic is not a Google rule.

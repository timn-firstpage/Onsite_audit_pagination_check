# SF exports and column mapping

Obtain exports from the same selected SF session/crawl. Preserve native columns, complete files and crawl provenance. Use UTF-8 CSV with optional BOM, comma separator and header first. Header-only is a valid zero-match result; zero-byte is a read error. Smart quotes, punctuation and numbered headings are normalized by the script. A blank cell is different from a missing field.

| Role | SF source | Fields |
|---|---|---|
| pagination | Pagination:All, equivalent to First Page ∪ Paginated 2+ Pages | Address; rel=next; rel=prev; Canonical Link Element 1/2…; HTTP Canonical 1/2… when present |
| first_page + paginated_2_plus | Alternative two native Pagination filters | Same columns as pagination; export both with matching headers |
| internal | Internal:All | Address; Status Code; Redirect URI; Canonical Link Element(s); Indexability; Indexability Status |
| near_duplicate_pairs | Content:Near Duplicates plus Duplicate Details/pair export | Address; Near Duplicate Address or matched URL; optional similarity |

Default filenames: `pagination_all.csv` (or `pagination.csv`), `internal_all.csv`, `near_duplicate_pairs.csv` (or `content_near_duplicate_pairs.csv`). Alternative scope files: `pagination_first_page.csv`, `pagination_paginated_2_plus_pages.csv` (short forms first_page.csv / paginated_2_plus_pages.csv accepted). Do not put multiple old/new versions in the same directory; ambiguity needs an explicit mapping.

Use `pagination.exports` for actual filenames:

```json
{
  "pagination": {
    "exports": {
      "pagination": "exports/pagination_all.csv",
      "internal": "exports/internal_all.csv",
      "near_duplicate_pairs": "exports/near_duplicate_pairs.csv"
    }
  }
}
```

Explicit mapped paths resolve against the configuration directory, not export_directory. Default filenames resolve inside source.export_directory. CLI --exports-dir overrides that default directory. Explicit role paths win. For the two-filter route map first_page and paginated_2_plus instead of pagination; supplying either selects that route and both are needed. Do not supply both routes.

Pair source column aliases: Address / Source / URL. Pair target aliases: Near Duplicate Address / Near Duplicate URL / Duplicate Address / Duplicate URL / Destination / Matched URL. The normal Content:Near Duplicates overview may only contain counts or highest similarity; it is insufficient if it omits the matched URL. Discover supported Duplicate Details exports in the actual SF version. If needed create the two-URL CSV from the complete native pair evidence, retaining the original export beside it and its transformation in the manifest. Do not invent pairs from equal H1 or rounded similarity.

Internal:All joins state to both endpoints. Canonicalised state is read from Indexability Status, or explicit Canonicalised/Canonicalized fields if supplied. Do not rename Canonical Link Element as Canonicalised. Include endpoint records even when an endpoint is not itself a pagination URL.

No anchor/outlinks, View All, browser observations, sitemap or robots exports are required for the agreed automatic checks. Obtain only missing data and reuse exports across audit workflows.

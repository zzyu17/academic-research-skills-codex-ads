# ADS API Verification Protocol

**Status**: ADS edition
**Used by**: `bibliography_agent`, `source_verification_agent`, `integrity_verification_agent`
**API base**: `https://api.adsabs.harvard.edu/v1/search/query`
**Rate limit**: 5000 req/day (with API token)
**Auth env var**: `ADS_API_TOKEN` (required — ADS does not support anonymous access)

---

## Purpose

Adds ADS as a fifth bibliographic-index lookup alongside Semantic Scholar, OpenAlex, Crossref, and arXiv. ADS (SAO/NASA Astrophysics Data System) is the primary bibliographic index for astronomy and astrophysics and the authoritative source for ADS bibcodes.

Mirrors the structure of `arxiv_api_protocol.md` and `crossref_api_protocol.md`.

## Response format

The ADS query API returns **JSON**. A match yields a `{"response": {"docs": [...]}}` envelope; a miss yields `{"response": {"docs": []}}` (not a 404). Per-document fields the client reads:

- `title` — (list of strings, joined by space)
- `bibcode` — ADS canonical bibcode (e.g., `2024ApJ...967..123C`)
- `year` — publication year (int or string)
- `doi` — DOI if available
- `pub` — publication name
- `author` — author list

## Query Patterns

### Pattern 1: Bibcode Lookup with Title Cross-Check (primary when a bibcode is available)

```
GET /search/query?q=bibcode:"{bibcode}"&fl=title,bibcode,author,year,doi,pub&rows=5
```

**Matching rule (mirrors the arXiv ID_MISMATCH pattern):** Bibcode lookup hits are gated by a 0.70 title cross-check (same SequenceMatcher threshold as the sibling clients). If the resolved entry's title is below threshold → BIBCODE_MISMATCH, return None, fall through to title search. An empty docs array (non-existent bibcode) is a miss → None.

### Pattern 2: Title Search (fallback on bibcode-miss / BIBCODE_MISMATCH)

```
GET /search/query?q=title:"{title}"&fl=title,bibcode,author,year,doi,pub&rows=5
```

**Matching rule:** similarity >= 0.70. When multiple candidates pass, prefer the matching-year tiebreaker via a +0.05 score bonus.

## Verification outcome derivation

The production verification gate writes ADS into `citation_verification_summary[].resolver_outcomes.ads`. It reports `matched` when bibcode lookup or its title fallback matches, and `unmatched` when both miss.

A citation with **no bibcode** is `skipped`, not `unmatched`. ADS applicability is bibcode-gated so a title-only miss for a non-astronomy work cannot become fabrication evidence.

## Degradation handling

| Condition | Action |
|---|---|
| Docs array empty | Treat as miss — caller falls through to title search / reports unmatched. NOT a degradation. |
| HTTP 401 (invalid token) | Raise `AdsUnavailable` immediately. |
| HTTP 429 (rate limit) | Back off 2 seconds, retry up to 3 times. After exhaustion, raise `AdsUnavailable`. |
| HTTP 5xx | Raise `AdsUnavailable` immediately (no retry). |
| Network timeout (30s default) / URLError | Raise `AdsUnavailable`. |
| Malformed JSON body | Raise `AdsUnavailable`. |
| `ADS_API_TOKEN` not set | Raise `AdsUnavailable` immediately on first call. |
| `AdsUnavailable` raised | Record ADS as `unreachable`; other indexes proceed independently. |

## ADS-specific notes

- **The verification outcome is bibcode-gated.** A citation with no bibcode records ADS as `skipped`. Astronomy workflows may still use title search for discovery outside the existence gate.
- **Auth is mandatory.** Unlike S2 (optional key) or arXiv (anonymous), ADS requires `ADS_API_TOKEN` for all API access. Get one free at https://ui.adsabs.harvard.edu/user/settings/token.
- **JSON, not XML.** Mirrors OpenAlex/Crossref/S2 clients structurally; the only divergence from the arXiv client.

## Client implementation

See `scripts/ads_client.py`. Class `AdsClient` exposes `bibcode_lookup(bibcode, expected_title)` and `title_search(title, year=None)`. Both return `dict | None`. Both raise `AdsUnavailable` on degradation per the table above.

## Cross-references

- Mirror template: `deep-research/references/arxiv_api_protocol.md`
- Sibling protocols: `deep-research/references/semantic_scholar_api_protocol.md`, `deep-research/references/openalex_api_protocol.md`, `deep-research/references/crossref_api_protocol.md`

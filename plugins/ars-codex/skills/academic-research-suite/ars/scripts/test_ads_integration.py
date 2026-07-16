#!/usr/bin/env python3
"""Integration tests for ADS API client against the real ADS API.

Requires ADS_API_TOKEN env var. All tests are skipped if the token is not set.
Uses known real papers (Planck 2018, Gaia EDR3) as ground-truth fixtures.

These tests are optional and make live requests only when ADS_API_TOKEN is set.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from unittest import mock

from ads_client import AdsClient, AdsUnavailable  # noqa: E402

# ---------------------------------------------------------------------------
# Ground-truth fixtures (verified against real ADS API 2026-06-16)
# ---------------------------------------------------------------------------
PLANCK_BIBCODE = "2020A&A...641A...6P"
PLANCK_TITLE = "Planck 2018 results. VI. Cosmological parameters"
PLANCK_YEAR = 2020

GAIA_BIBCODE = "2021A&A...649A...5F"
GAIA_TITLE = "Gaia Early Data Release 3. Catalogue validation"
GAIA_YEAR = 2021

# ---------------------------------------------------------------------------
# Skip decorator
# ---------------------------------------------------------------------------
_ads_token = os.environ.get("ADS_API_TOKEN", "")
requires_token = unittest.skipIf(
    not _ads_token,
    "ADS_API_TOKEN not set — skipping real-API integration test",
)


class RealBibcodeLookupTest(unittest.TestCase):
    """Real ADS API bibcode_lookup tests."""

    @requires_token
    def test_bibcode_hit_with_correct_title(self):
        """Known bibcode + correct title -> returns entry with matching fields."""
        client = AdsClient()
        result = client.bibcode_lookup(PLANCK_BIBCODE, PLANCK_TITLE)
        self.assertIsNotNone(result, "Planck bibcode should resolve with correct title")
        self.assertEqual(result["bibcode"], PLANCK_BIBCODE)
        self.assertEqual(result["year"], PLANCK_YEAR)
        self.assertIn("Planck", result["title"])

    @requires_token
    def test_bibcode_mismatch_wrong_title(self):
        """Known bibcode + completely unrelated title -> BIBCODE_MISMATCH -> None."""
        client = AdsClient()
        result = client.bibcode_lookup(
            PLANCK_BIBCODE, "Completely Unrelated Paper About Galaxy Morphology"
        )
        self.assertIsNone(result, "BIBCODE_MISMATCH should return None")

    @requires_token
    def test_nonexistent_bibcode_returns_none(self):
        """Fake bibcode -> empty docs -> None."""
        client = AdsClient()
        result = client.bibcode_lookup("9999ZZZZ...999Z", "Anything")
        self.assertIsNone(result, "Fake bibcode should return None")


class RealTitleSearchTest(unittest.TestCase):
    """Real ADS API title_search tests."""

    @requires_token
    def test_title_search_match(self):
        """Known paper title -> returns entry with bibcode."""
        client = AdsClient()
        result = client.title_search(PLANCK_TITLE)
        self.assertIsNotNone(result, "Planck title should resolve in ADS")
        self.assertEqual(result["bibcode"], PLANCK_BIBCODE)
        self.assertEqual(result["year"], PLANCK_YEAR)

    @requires_token
    def test_title_search_with_year_param(self):
        """Title search with year parameter returns paper with matching year."""
        client = AdsClient()
        result = client.title_search(PLANCK_TITLE, year=PLANCK_YEAR)
        self.assertIsNotNone(result)
        self.assertEqual(result["year"], PLANCK_YEAR,
                         f"Year should be {PLANCK_YEAR} when year param is set")

    @requires_token
    def test_title_search_no_match(self):
        """Gibberish title -> None."""
        client = AdsClient()
        result = client.title_search(
            "XyzzyFlibbertigibbetNonExistentPaperTitle42"
        )
        self.assertIsNone(result, "Gibberish title should return None")


class RealVerificationGateTest(unittest.TestCase):
    """Test the production verification gate with a real AdsClient."""

    def _clients(self, ads):
        def default():
            client = mock.MagicMock()
            client.doi_lookup_with_title_check.return_value = None
            client.title_search.return_value = None
            client.arxiv_id_lookup.return_value = None
            client.lookup.return_value = {"matched": False}
            return client
        return {
            "crossref": default(),
            "openalex": default(),
            "semantic_scholar": default(),
            "arxiv": default(),
            "ads": ads,
        }

    @requires_token
    def test_verification_gate_with_real_ads_hit(self):
        from verification_gate import verify_citation  # noqa: E402

        entry = {
            "citation_key": "planck2020",
            "title": PLANCK_TITLE,
            "bibcode": PLANCK_BIBCODE,
            "obtained_via": "zotero-bbt-export",
            "year": PLANCK_YEAR,
        }
        result = verify_citation(
            entry, self._clients(AdsClient()), ref_slug="planck-2020"
        )
        self.assertEqual(result["resolver_outcomes"]["ads"]["status"], "matched")

    @requires_token
    def test_verification_gate_with_ads_no_match(self):
        from verification_gate import verify_citation  # noqa: E402

        entry = {
            "citation_key": "fake2025",
            "title": "XyzzyFlibbertigibbetNonExistentPaperTitle42",
            "bibcode": "9999ZZZZ...999Z",
            "obtained_via": "folder-scan",
            "year": 2025,
        }
        result = verify_citation(
            entry, self._clients(AdsClient()), ref_slug="fake-2025"
        )
        self.assertEqual(result["resolver_outcomes"]["ads"]["status"], "unmatched")

    @requires_token
    def test_verification_gate_without_bibcode_skips_ads(self):
        from verification_gate import verify_citation  # noqa: E402

        entry = {
            "citation_key": "planck2020",
            "title": PLANCK_TITLE,
            "obtained_via": "zotero-bbt-export",
            "year": PLANCK_YEAR,
        }
        result = verify_citation(
            entry, self._clients(AdsClient()), ref_slug="planck-2020"
        )
        self.assertEqual(result["resolver_outcomes"]["ads"]["status"], "skipped")


class RealAdsDegradationTest(unittest.TestCase):
    """Test degradation behavior with real API conditions."""

    def test_missing_token_raises_ads_unavailable(self):
        """Without ADS_API_TOKEN, AdsClient raises AdsUnavailable on first call."""
        with mock.patch.dict("os.environ", {}, clear=True):
            client = AdsClient()
            with self.assertRaises(AdsUnavailable):
                client.bibcode_lookup(PLANCK_BIBCODE, PLANCK_TITLE)


if __name__ == "__main__":
    unittest.main()

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

from venturelab import rank_opportunities


def evidence(kind="demand"):
    return {"url": "https://example.org/source", "published_on": "2025-01-02", "finding": "Observed evidence", "kind": kind}


def opportunity(identifier="a", kinds=("demand", "engineering"), scores=None):
    return {
        "id": identifier,
        "title": "Test venture",
        "buyer": "Small businesses",
        "problem": "Manual workflow",
        "evidence": [evidence(kind) for kind in kinds],
        "scores": scores or {"pain": 5, "demand": 4, "payment_likelihood": 3, "feasibility": 2, "differentiation": 1, "distribution": 0},
    }


class OpportunityRankingTests(unittest.TestCase):
    def test_good_ranking_and_preserves_original_record(self):
        low = opportunity("z", scores={key: 1 for key in ("pain", "demand", "payment_likelihood", "feasibility", "differentiation", "distribution")})
        high = opportunity("a")
        result = rank_opportunities({"opportunities": [low, high]})
        self.assertEqual([item["id"] for item in result], ["a", "z"])
        self.assertTrue(result[0]["eligible"])
        self.assertEqual(result[0]["score"], 61)
        self.assertEqual({k: result[0][k] for k in high}, high)
        self.assertEqual(result[0]["reasons"], [])

    def test_weights_calculate_exactly(self):
        scores = {"pain": 5, "demand": 4, "payment_likelihood": 3, "feasibility": 2, "differentiation": 1, "distribution": 0}
        self.assertEqual(rank_opportunities({"opportunities": [opportunity(scores=scores)]})[0]["score"], 61)
        self.assertEqual(rank_opportunities({"opportunities": [opportunity(scores={k: 5 for k in scores})]})[0]["score"], 100)

    def test_invalid_schema(self):
        for data in (None, {}, {"opportunities": []}, {"opportunities": "bad"}, {"opportunities": [None]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                rank_opportunities(data)
        record = opportunity()
        for field in ("id", "title", "buyer", "problem"):
            bad = copy.deepcopy(record)
            bad[field] = " "
            with self.subTest(field=field), self.assertRaises(ValueError):
                rank_opportunities({"opportunities": [bad]})

    def test_boolean_score_rejected(self):
        record = opportunity()
        record["scores"]["pain"] = True
        with self.assertRaises(ValueError):
            rank_opportunities({"opportunities": [record]})

    def test_malformed_dates_and_urls(self):
        for key, value in (("published_on", "2025-02-30"), ("published_on", "2025-1-02"), ("url", "http://example.org/a"), ("url", "https:///missing-host")):
            record = opportunity()
            record["evidence"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                rank_opportunities({"opportunities": [record]})

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            rank_opportunities({"opportunities": [opportunity("same"), opportunity("same")]})

    def test_missing_evidence_gate_and_reason(self):
        missing_demand = opportunity("a", kinds=("engineering",))
        missing_engineering = opportunity("b", kinds=("demand",))
        result = rank_opportunities({"opportunities": [missing_demand, opportunity("c"), missing_engineering]})
        self.assertEqual([item["id"] for item in result], ["c", "a", "b"])
        self.assertFalse(result[1]["eligible"])
        self.assertEqual(result[1]["reasons"], ["Missing required demand evidence"])

    def test_deterministic_ties(self):
        records = [opportunity("z"), opportunity("a"), opportunity("m")]
        results = rank_opportunities({"opportunities": records})
        self.assertEqual([r["id"] for r in results], ["a", "m", "z"])
        self.assertEqual([r["id"] for r in rank_opportunities({"opportunities": list(reversed(records))})], ["a", "m", "z"])

    def test_cli_success_and_clean_error(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with tempfile.TemporaryDirectory() as directory:
            manifest = os.path.join(directory, "input.json")
            with open(manifest, "w", encoding="utf-8") as output:
                json.dump({"opportunities": [opportunity()]}, output)
            ok = subprocess.run([sys.executable, "-m", "venturelab", "rank", manifest], cwd=root, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0)
            self.assertEqual(json.loads(ok.stdout)[0]["score"], 61)
            bad = subprocess.run([sys.executable, "-m", "venturelab", "rank", os.path.join(directory, "absent.json")], cwd=root, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertTrue(bad.stderr.startswith("error:"))


if __name__ == "__main__":
    unittest.main()

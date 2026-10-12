import unittest
from dataset_analysis import analyze_csv

class DatasetAnalysisTests(unittest.TestCase):
    def test_numeric_summary_and_correlation(self):
        out = analyze_csv("time,value,group\n1,2,A\n2,4,A\n3,6,B\n4,8,B\n")
        self.assertEqual(out["row_count"], 4)
        self.assertEqual(out["column_count"], 3)
        value = next(c for c in out["columns"] if c["name"] == "value")
        self.assertAlmostEqual(value["statistics"]["mean"], 5)
        corr = next(c for c in out["correlations"] if c["column_a"] == "time" and c["column_b"] == "value")
        self.assertAlmostEqual(corr["pearson_r"], 1)
    def test_missing_and_duplicates(self):
        out = analyze_csv("x,y\n1,2\n1,2\n3,NA\n")
        self.assertEqual(out["duplicate_rows"], 1)
        y = next(c for c in out["columns"] if c["name"] == "y")
        self.assertEqual(y["missing"], 1)
    def test_bad_width_rejected(self):
        with self.assertRaises(ValueError):
            analyze_csv("a,b\n1,2\n3")
    def test_duplicate_headers_rejected(self):
        with self.assertRaises(ValueError):
            analyze_csv("x,x\n1,2\n")
    def test_empty_data_rejected(self):
        with self.assertRaises(ValueError):
            analyze_csv("a,b\n")
    def test_nonfinite_numbers_are_not_numeric(self):
        out = analyze_csv("x\n1\ninf\n3\n")
        self.assertEqual(out["columns"][0]["inferred_type"], "categorical/text")
    def test_invalid_preview_limit_rejected(self):
        with self.assertRaises(ValueError):
            analyze_csv("x\n1\n", preview_rows=0)

if __name__ == "__main__":
    unittest.main()

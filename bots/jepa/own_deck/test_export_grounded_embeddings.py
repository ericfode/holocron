import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_grounded_embeddings as E


class SavedVectorExportTests(unittest.TestCase):
    def test_normalization_preserves_raw_and_zero_status(self):
        vectors = np.ones((12, 16), np.float32)
        vectors[0] = 0
        original = vectors.copy()
        norms, units = E.normalized_vectors(vectors)
        np.testing.assert_array_equal(vectors, original)
        self.assertEqual(norms[0], 0)
        self.assertFalse(units[0].any())
        np.testing.assert_allclose(np.linalg.norm(units[1:], axis=1), 1)
        with self.assertRaises(ValueError):
            E.normalized_vectors(np.full((12, 16), np.nan, np.float32))

    def test_atomic_json_and_schema_have_explicit_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            E.write(path, {"old": 1})
            E.write(path, {"new": 2})
            self.assertEqual(json.loads(path.read_text()), {"new": 2})
            self.assertFalse(path.with_suffix(".json.tmp").exists())
        spec = E.schema()
        self.assertFalse(spec["properties"]["semantic_validated"]["const"])
        self.assertEqual(spec["properties"]["rows"]["minItems"], 12)


if __name__ == "__main__":
    unittest.main()

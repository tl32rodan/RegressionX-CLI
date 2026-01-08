import unittest
import tempfile
import shutil
import os
from pathlib import Path

# We will implement this module next
try:
    from regressionx.comparator import compare_directories
except ImportError:
    compare_directories = None

class TestComparator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        self.dir_a = self.root / "base"
        self.dir_b = self.root / "cand"
        self.dir_a.mkdir()
        self.dir_b.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, parent: Path, name: str, content: str):
        p = parent / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')

    def test_identical_directories(self):
        # Arrange
        self.create_file(self.dir_a, "f1.txt", "content")
        self.create_file(self.dir_b, "f1.txt", "content")
        self.create_file(self.dir_a, "sub/f2.txt", "sub")
        self.create_file(self.dir_b, "sub/f2.txt", "sub")

        if compare_directories is None:
            self.fail("Implementation Missing")

        # Act
        result = compare_directories(self.dir_a, self.dir_b)

        # Assert
        self.assertTrue(result.match)
        self.assertEqual(len(result.diffs), 0)

    def test_content_mismatch(self):
        # Arrange
        self.create_file(self.dir_a, "f1.txt", "content A")
        self.create_file(self.dir_b, "f1.txt", "content B")

        if compare_directories is None:
            self.fail("Implementation Missing")

        # Act
        result = compare_directories(self.dir_a, self.dir_b)

        # Assert
        self.assertFalse(result.match)
        self.assertIn("Content mismatch: f1.txt", result.diffs)
        
    def test_unexpected_file_in_candidate(self):
        # Arrange
        self.create_file(self.dir_a, "f1.txt", "content")
        self.create_file(self.dir_b, "f1.txt", "content")
        self.create_file(self.dir_b, "extra.txt", "extra")

        if compare_directories is None:
            self.fail("Implementation Missing")

        # Act
        result = compare_directories(self.dir_a, self.dir_b)

        # Assert
        self.assertFalse(result.match)
        self.assertIn("Only in candidate: extra.txt", result.errors)
        
    def test_missing_file_in_candidate(self):
        # Arrange
        self.create_file(self.dir_a, "missing.txt", "content")

        if compare_directories is None:
            self.fail("Implementation Missing")

        # Act
        result = compare_directories(self.dir_a, self.dir_b)

        # Assert
        self.assertFalse(result.match)
        self.assertIn("Only in baseline: missing.txt", result.errors)

if __name__ == "__main__":
    unittest.main()

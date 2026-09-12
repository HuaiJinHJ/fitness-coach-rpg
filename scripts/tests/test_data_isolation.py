import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts._common import resolve_user_data


class DataIsolationTests(unittest.TestCase):
    def test_default_is_repository_user_data(self):
        root = Path("C:/repo")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_user_data(root), root / "user-data")

    def test_environment_override_uses_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"FITNESS_COACH_DATA_DIR": temp_dir}):
                self.assertEqual(
                    resolve_user_data(Path("C:/repo")),
                    Path(temp_dir).resolve(),
                )


if __name__ == "__main__":
    unittest.main()

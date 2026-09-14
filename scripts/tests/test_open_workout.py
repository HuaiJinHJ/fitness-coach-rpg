import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "open_workout.py"


def load_module():
    spec = importlib.util.spec_from_file_location("open_workout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenWorkoutTests(unittest.TestCase):
    def test_build_workout_url_contains_session_query(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "index.html"
            index.write_text("<html></html>", encoding="utf-8")
            url = module.build_workout_url(index, "session-123")
        self.assertTrue(url.startswith("file:"))
        self.assertIn("session=session-123", url)

    def test_main_uses_default_browser_only_after_validation(self):
        module = load_module()
        with mock.patch.object(module, "validate_active_workout", return_value="session-123"), \
             mock.patch.object(module.webbrowser, "open", return_value=True) as browser:
            result = module.main()
        self.assertEqual(result, 0)
        browser.assert_called_once()
        self.assertEqual(browser.call_args.kwargs["new"], 2)

    def test_main_does_not_open_browser_when_validation_fails(self):
        module = load_module()
        with mock.patch.object(module, "validate_active_workout", side_effect=ValueError("bad workout")), \
             mock.patch.object(module.webbrowser, "open") as browser:
            result = module.main()
        self.assertEqual(result, 1)
        browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()

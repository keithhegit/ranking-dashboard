import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sensor_tower_focus_fast as wrapper


class TooltipReaderPatchTest(unittest.TestCase):
    def test_reader_script_recovers_current_sensor_tower_tooltip_markup(self):
        self.assertTrue(
            hasattr(wrapper, "build_tooltip_reader_script"),
            "wrapper should expose the patched tooltip reader script",
        )

        script = wrapper.build_tooltip_reader_script()

        self.assertIn("TooltipChartValues-module__tooltipCardContent", script)
        self.assertIn("hasTooltipText", script)
        self.assertIn("!visible && !hasTooltipText", script)

    def test_patch_replaces_engine_tooltip_reader(self):
        self.assertTrue(
            hasattr(wrapper, "patch_tooltip_reader"),
            "wrapper should patch the compiled engine tooltip reader",
        )

        class Module:
            pass

        class Page:
            def evaluate(self, script):
                self.script = script
                return [{"selector": "div[class*='Tooltip']", "text": "Wednesday, Jun 10, 2026\n#378"}]

        module = Module()
        wrapper.patch_tooltip_reader(module)
        page = Page()

        result = module.read_tooltip_candidates(page)

        self.assertEqual(result[0]["text"], "Wednesday, Jun 10, 2026\n#378")
        self.assertIn("TooltipChartValues-module__tooltipCardContent", page.script)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

from modules import hud


class HudLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video_driver_patch = patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"})
        cls.video_driver_patch.start()
        hud.initialize_pygame()

    @classmethod
    def tearDownClass(cls):
        hud.cleanup()
        cls.video_driver_patch.stop()

    def test_settings_dialog_hides_overlapping_memory_panel(self):
        original_state = (
            hud.settings_panel_open,
            hud.task_panel_x,
            hud.task_panel_target_x,
        )
        hud.settings_panel_open = True
        hud.task_panel_x = hud.WINDOW_WIDTH
        hud.task_panel_target_x = hud.WINDOW_WIDTH
        titles = []

        try:
            with patch(
                "modules.hud.draw_glass_panel",
                side_effect=lambda surface, x, y, width, height, title="": titles.append(title),
            ):
                hud.render_frame(0.0)
        finally:
            (
                hud.settings_panel_open,
                hud.task_panel_x,
                hud.task_panel_target_x,
            ) = original_state

        self.assertIn("Identity Settings", titles)
        self.assertNotIn("Memory Commands", titles)


if __name__ == "__main__":
    unittest.main()

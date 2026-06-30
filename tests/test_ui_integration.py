"""pygame 화면 컨트롤러와 데이터 저장 계층의 연결을 검사한다."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from dashboard import App
from data_manager import DataManager


class DashboardIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.manager = DataManager(Path(self.temp.name))
        self.app = App(data_manager=self.manager, dev_mode=True)

    def tearDown(self) -> None:
        pygame.quit()
        self.temp.cleanup()

    def test_full_day_two_flow(self) -> None:
        session = self.app.start_session("주혁테스트")
        self.assertEqual(self.app.state["session_id"], session["session_id"])

        self.app.run_task(1)
        self.assertEqual(self.app.current_screen.name, "interim_result")
        self.app.run_task(2)
        self.assertEqual(self.app.current_screen.name, "interim_result")

        report = self.app.finish_current_session()
        self.assertEqual(self.app.current_screen.name, "final_result")
        self.assertEqual(report["participant_id"], "주혁테스트")
        self.assertEqual(report["rank"], 1)
        self.assertEqual(len(self.app.get_top_rankings()), 1)

    def test_duplicate_id_is_rejected(self) -> None:
        self.app.start_session("brain01")
        with self.assertRaises(ValueError):
            self.app.start_session("brain01")


if __name__ == "__main__":
    unittest.main()

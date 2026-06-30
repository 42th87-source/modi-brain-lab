"""MODI 입출력 계층과 TASK 3·4 채점 호환성을 검사한다."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from modi_io import MockModiIO, RealModiIO
from scoring import score_task3, score_task4


class FakeButton:
    pressed = False
    clicked = False


class FakeDial:
    degree = 55


class FakeGyro:
    pitch = 10
    roll = -12
    yaw = 3
    angular_vel_x = 1
    angular_vel_y = 2
    angular_vel_z = 3


class FakeLed:
    rgb = (0, 0, 0)


class FakeSpeaker:
    tune = (0, 0)
    volume = 0

    def turn_off(self):
        self.volume = 0


class FakeBundle:
    buttons = [FakeButton()]
    dials = [FakeDial()]
    gyros = [FakeGyro()]
    leds = [FakeLed()]
    speakers = [FakeSpeaker()]


class ModiIOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_mock_button_uses_space(self) -> None:
        io = MockModiIO()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        self.assertTrue(io.poll_button([event]))

    def test_real_wrapper_maps_module_properties(self) -> None:
        io = RealModiIO(FakeBundle())
        self.assertEqual(io.get_dial_value(), 55)
        self.assertEqual(io.get_gyro().roll, -12)
        io.set_led(100, 20, 5)
        self.assertEqual(io.led.rgb, (100, 20, 5))
        io.play_tone(440, 60)
        self.assertEqual(io.speaker.tune, (440, 60))


class NewTaskScoringTests(unittest.TestCase):
    def test_task3_trials_produce_attention_score(self) -> None:
        trials = [
            {"stimulus_condition": "congruent", "hit": True, "reaction_time_ms": 300},
            {"stimulus_condition": "visual_only", "hit": True, "reaction_time_ms": 350},
            {"stimulus_condition": "audio_only", "false_alarm": False, "correct_rejection": True},
            {"stimulus_condition": "none", "false_alarm": False, "correct_rejection": True},
        ]
        result = score_task3({"task_id": "task3", "trials": trials})
        self.assertEqual(result["metrics"]["balanced_accuracy"], 100)
        self.assertGreater(result["score"], 80)

    def test_task4_trials_produce_coordination_score(self) -> None:
        trials = [
            *({"phase": "cursor_baseline", "inside_target": True} for _ in range(10)),
            *({"phase": "dual_task", "inside_target": True} for _ in range(8)),
            *({"phase": "dual_task", "inside_target": False} for _ in range(2)),
            *(
                {
                    "phase": "rhythm_baseline",
                    "beat_error_ms": 60,
                    "missed_beat": False,
                    "extra_press": False,
                }
                for _ in range(4)
            ),
            *(
                {
                    "phase": "dual_task",
                    "beat_error_ms": 100,
                    "missed_beat": False,
                    "extra_press": False,
                }
                for _ in range(4)
            ),
        ]
        result = score_task4({"task_id": "task4", "trials": trials})
        self.assertEqual(result["metrics"]["dual_cursor_hold_rate"], 80)
        self.assertIsNotNone(result["score"])


if __name__ == "__main__":
    unittest.main()

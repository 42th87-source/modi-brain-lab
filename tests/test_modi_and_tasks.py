"""MODI 입출력 계층과 TASK 3·4 채점 호환성을 검사한다."""

import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from modi_io import MockModiIO, RealModiIO
from scoring import score_task3, score_task4
from tasks.task2_memory import color_from_dial, generate_sequence
from tasks.task4_coordination import target_position
from tasks.task1_reaction import angle_displacement, angular_speed


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


class FakeImu:
    angle_x = -21
    angle_y = 14
    angle_z = 5
    angular_vel_x = 4
    angular_vel_y = 5
    angular_vel_z = 6


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


class FakePlusBundle(FakeBundle):
    imus = [FakeImu()]
    gyros = []


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

    def test_modi_plus_imu_property_names_are_supported(self) -> None:
        io = RealModiIO(FakePlusBundle())
        gyro = io.get_gyro()
        self.assertEqual(gyro.roll, -21)
        self.assertEqual(gyro.pitch, 14)

    def test_legacy_reset_prompt_is_skipped_without_deleting_code(self) -> None:
        import builtins

        original_input = builtins.input
        with RealModiIO._skip_legacy_reset_prompt():
            self.assertEqual(builtins.input("reset?"), "n")
        self.assertIs(builtins.input, original_input)


class NewTaskScoringTests(unittest.TestCase):
    def test_task1_gyro_helpers_measure_speed_and_displacement(self) -> None:
        neutral = type("State", (), {"pitch": 2.0, "roll": -3.0})()
        state = type(
            "State",
            (),
            {
                "pitch": 12.0,
                "roll": 37.0,
                "angular_velocity_x": 30.0,
                "angular_velocity_y": 40.0,
                "angular_velocity_z": 0.0,
            },
        )()
        self.assertEqual(angle_displacement(state, neutral), 40.0)
        self.assertEqual(angular_speed(state), 50.0)

    def test_task2_dial_ranges_select_colors(self) -> None:
        self.assertEqual(color_from_dial(0), "red")
        self.assertEqual(color_from_dial(30), "green")
        self.assertEqual(color_from_dial(60), "blue")
        self.assertEqual(color_from_dial(90), "yellow")

    def test_task2_sequence_avoids_three_repeated_colors(self) -> None:
        sequence = generate_sequence(random.Random(7), 40)
        triples = zip(sequence, sequence[1:], sequence[2:])
        self.assertFalse(any(first == second == third for first, second, third in triples))

    def test_task4_target_moves_on_fixed_schedule(self) -> None:
        positions = [target_position(second, 960, 640) for second in (0, 1.0, 2.5, 4.0, 7.0, 10.0)]
        self.assertGreaterEqual(len(set(positions[:-1])), 5)
        self.assertEqual(positions[0], positions[-1])

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

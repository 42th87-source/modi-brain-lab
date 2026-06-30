"""데이터 저장, 점수 계산과 순위 기능의 통합 테스트다."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from data_manager import DataManager
from scoring import calculate_total_score, score_task1, score_task2


class ScoringTests(unittest.TestCase):
    def test_task1_uses_valid_trial_medians(self) -> None:
        result = score_task1(
            {
                "task_id": "task1",
                "trials": [
                    {"input_condition": "button", "reaction_time_ms": 300, "valid": True},
                    {"input_condition": "button", "reaction_time_ms": 320, "valid": True},
                    {"input_condition": "button", "reaction_time_ms": 900, "valid": False},
                    {"input_condition": "gyro", "reaction_time_ms": 360, "valid": True},
                    {"input_condition": "gyro", "reaction_time_ms": 380, "valid": True},
                ],
            }
        )
        self.assertEqual(result["metrics"]["button_median_ms"], 310)
        self.assertEqual(result["metrics"]["gyro_median_ms"], 370)
        self.assertEqual(result["metrics"]["input_mode_difference_ms"], 60)
        self.assertIsNotNone(result["score"])

    def test_task2_scores_both_conditions(self) -> None:
        trials = [
            {
                "sensory_condition": "visual",
                "sequence_length": 3,
                "position_correct_count": 3,
                "exact_sequence_correct": True,
            },
            {
                "sensory_condition": "audiovisual",
                "sequence_length": 3,
                "position_correct_count": 2,
                "exact_sequence_correct": False,
            },
        ]
        result = score_task2({"task_id": "task2", "trials": trials})
        self.assertEqual(result["metrics"]["visual_accuracy"], 100)
        self.assertAlmostEqual(result["metrics"]["audiovisual_accuracy"], 66.67, places=2)
        self.assertIsNotNone(result["score"])

    def test_total_score_averages_completed_tasks(self) -> None:
        self.assertEqual(calculate_total_score({"task1": 80, "task2": 70}), 75.0)


class DataManagerTests(unittest.TestCase):
    def test_session_save_report_and_leaderboard(self) -> None:
        with TemporaryDirectory() as directory:
            manager = DataManager(Path(directory))
            first = manager.create_participant_session("참가자01")
            manager.save_task_result(
                first["session_id"],
                {
                    "task_id": "task1",
                    "metrics": {"button_median_ms": 300, "gyro_median_ms": 350},
                    "trials": [],
                },
            )
            manager.save_task_result(
                first["session_id"],
                {
                    "task_id": "task2",
                    "metrics": {
                        "visual_accuracy": 80,
                        "audiovisual_accuracy": 90,
                        "visual_memory_span": 4,
                        "audiovisual_memory_span": 5,
                    },
                    "trials": [],
                },
            )
            report = manager.complete_session(first["session_id"])
            self.assertEqual(report["participant_id"], "참가자01")
            self.assertEqual(report["rank"], 1)
            self.assertEqual(report["participant_count"], 1)
            self.assertFalse(manager.is_participant_id_available("참가자01"))
            self.assertEqual(manager.get_leaderboard()[0]["participant_id"], "참가자01")
            analysis = manager.get_group_analysis()
            self.assertEqual(analysis["participant_count"], 1)
            self.assertIn("sensory_integration_effect", analysis["effects"])

    def test_invalid_ids_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            manager = DataManager(Path(directory))
            with self.assertRaises(ValueError):
                manager.create_participant_session("a!")


if __name__ == "__main__":
    unittest.main()

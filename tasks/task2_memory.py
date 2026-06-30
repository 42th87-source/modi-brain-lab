"""TASK 2: memory span and sensory integration.

This module is intentionally self-contained so it can be reviewed as a single
feature file. It runs a pygame prototype with keyboard fallback controls and
returns the shared task result shape:

{
    "task_id": "task2",
    "score": float | None,
    "metrics": {...},
    "trials": [...]
}
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Any

import pygame


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60

COLOR_BACKGROUND = (18, 22, 31)
COLOR_PANEL = (34, 41, 55)
COLOR_TEXT = (238, 242, 247)
COLOR_MUTED = (156, 163, 175)
COLOR_READY = (59, 130, 246)
COLOR_SUCCESS = (16, 185, 129)

TRIALS = [
    ("visual", 3),
    ("audiovisual", 3),
    ("audiovisual", 4),
    ("visual", 4),
    ("audiovisual", 5),
    ("visual", 5),
    ("visual", 6),
    ("audiovisual", 6),
]
PRACTICE_TRIAL = ("visual", 2)
STIMULUS_MS = 600
BLANK_MS = 300

COLORS = {
    "red": {
        "label": "빨강",
        "rgb": (239, 68, 68),
        "frequency": 262,
        "key": "1",
    },
    "green": {
        "label": "초록",
        "rgb": (34, 197, 94),
        "frequency": 330,
        "key": "2",
    },
    "blue": {
        "label": "파랑",
        "rgb": (59, 130, 246),
        "frequency": 392,
        "key": "3",
    },
    "yellow": {
        "label": "노랑",
        "rgb": (250, 204, 21),
        "frequency": 523,
        "key": "4",
    },
}
COLOR_ORDER = ["red", "green", "blue", "yellow"]


@dataclass
class TrialResult:
    """Raw result for one TASK 2 trial."""

    trial_index: int
    sensory_condition: str
    sequence_length: int
    target_sequence: list[str]
    response_sequence: list[str]
    position_correct_count: int
    exact_sequence_correct: bool
    response_start_time: float | None
    response_complete_time: float | None
    total_response_time_ms: float | None
    random_seed: int
    practice: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "sensory_condition": self.sensory_condition,
            "sequence_length": self.sequence_length,
            "target_sequence": self.target_sequence,
            "response_sequence": self.response_sequence,
            "position_correct_count": self.position_correct_count,
            "exact_sequence_correct": self.exact_sequence_correct,
            "response_start_time": _round_time(self.response_start_time),
            "response_complete_time": _round_time(self.response_complete_time),
            "total_response_time_ms": _round_ms(self.total_response_time_ms),
            "random_seed": self.random_seed,
            "practice": self.practice,
        }


class TonePlayer:
    """Generate simple sine tones for the audiovisual condition."""

    def __init__(self) -> None:
        self.enabled = False
        self.sample_rate = 44100
        self.cache: dict[int, pygame.mixer.Sound] = {}

        try:
            pygame.mixer.pre_init(self.sample_rate, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, frequency: int, duration_ms: int) -> None:
        if not self.enabled:
            return
        sound = self.cache.get(frequency)
        if sound is None:
            sound = self._make_sound(frequency, duration_ms)
            self.cache[frequency] = sound
        sound.play()

    def _make_sound(self, frequency: int, duration_ms: int) -> pygame.mixer.Sound:
        sample_count = int(self.sample_rate * duration_ms / 1000)
        amplitude = 9000
        samples = array.array("h")
        for index in range(sample_count):
            angle = 2 * math.pi * frequency * index / self.sample_rate
            samples.append(int(amplitude * math.sin(angle)))
        return pygame.mixer.Sound(buffer=samples.tobytes())


class Task2MemoryApp:
    """Pygame prototype for TASK 2.

    Keyboard fallback:
    - 1: red, 2: green, 3: blue, 4: yellow
    - left/right: move selection
    - space/enter: confirm selected color
    """

    def __init__(self, participant_id: str) -> None:
        pygame.init()
        pygame.display.set_caption("MODI Brain Lab - TASK 2")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("malgungothic", 52)
        self.font_medium = pygame.font.SysFont("malgungothic", 32)
        self.font_small = pygame.font.SysFont("malgungothic", 22)
        self.participant_id = participant_id
        self.random_seed = seed_from_participant(participant_id)
        self.random = random.Random(self.random_seed)
        self.tone_player = TonePlayer()

    def run(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        self._show_intro()

        practice_condition, practice_length = PRACTICE_TRIAL
        practice_sequence = self._generate_sequence(practice_length)
        practice_result = self._run_trial(
            trial_index=0,
            condition=practice_condition,
            sequence=practice_sequence,
            practice=True,
        )
        records.append(practice_result.to_dict())

        for trial_index, (condition, sequence_length) in enumerate(TRIALS, start=1):
            sequence = self._generate_sequence(sequence_length)
            result = self._run_trial(
                trial_index=trial_index,
                condition=condition,
                sequence=sequence,
                practice=False,
            )
            records.append(result.to_dict())

        result_payload = build_task2_result(records)
        self._show_summary(result_payload)
        pygame.quit()
        return result_payload

    def _run_trial(
        self,
        trial_index: int,
        condition: str,
        sequence: list[str],
        practice: bool,
    ) -> TrialResult:
        label = "연습" if practice else f"측정 {trial_index}/8"
        condition_label = "시각" if condition == "visual" else "시청각"
        self._draw_screen(
            title=f"{label} - {condition_label}",
            subtitle=f"{len(sequence)}개의 색상 순서를 기억하세요.",
            footer="스페이스바로 제시 시작",
            accent=COLOR_READY,
        )
        self._wait_for_key({pygame.K_SPACE})

        self._present_sequence(sequence, condition)
        response_start_time = time.perf_counter()
        response_sequence = self._collect_response(len(sequence))
        response_complete_time = time.perf_counter()
        total_response_time_ms = (response_complete_time - response_start_time) * 1000
        position_correct_count = sum(
            1 for target, response in zip(sequence, response_sequence) if target == response
        )
        exact_sequence_correct = sequence == response_sequence

        self._show_feedback(position_correct_count, len(sequence), exact_sequence_correct)

        return TrialResult(
            trial_index=trial_index,
            sensory_condition=condition,
            sequence_length=len(sequence),
            target_sequence=sequence,
            response_sequence=response_sequence,
            position_correct_count=position_correct_count,
            exact_sequence_correct=exact_sequence_correct,
            response_start_time=response_start_time,
            response_complete_time=response_complete_time,
            total_response_time_ms=total_response_time_ms,
            random_seed=self.random_seed,
            practice=practice,
        )

    def _generate_sequence(self, length: int) -> list[str]:
        sequence: list[str] = []
        while len(sequence) < length:
            color = self.random.choice(COLOR_ORDER)
            if len(sequence) >= 2 and sequence[-1] == sequence[-2] == color:
                continue
            sequence.append(color)
        return sequence

    def _present_sequence(self, sequence: list[str], condition: str) -> None:
        self._draw_screen(
            title="제시",
            subtitle="순서를 잘 기억하세요.",
            footer="",
            accent=COLOR_READY,
        )
        self._wait_ms(600)

        for index, color_name in enumerate(sequence, start=1):
            color_info = COLORS[color_name]
            if condition == "audiovisual":
                self.tone_player.play(color_info["frequency"], STIMULUS_MS)
            self._draw_color_stimulus(color_name, index, len(sequence), condition)
            self._wait_ms(STIMULUS_MS)
            self._draw_blank(index, len(sequence))
            self._wait_ms(BLANK_MS)

    def _collect_response(self, expected_length: int) -> list[str]:
        selected_index = 0
        response: list[str] = []

        while len(response) < expected_length:
            self._draw_response_screen(selected_index, response, expected_length)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        selected_index = (selected_index - 1) % len(COLOR_ORDER)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        selected_index = (selected_index + 1) % len(COLOR_ORDER)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        response.append(COLOR_ORDER[selected_index])
                    else:
                        keyed_color = self._color_from_number_key(event.key)
                        if keyed_color is not None:
                            selected_index = COLOR_ORDER.index(keyed_color)
                            response.append(keyed_color)
            self.clock.tick(FPS)

        return response

    def _color_from_number_key(self, key: int) -> str | None:
        mapping = {
            pygame.K_1: "red",
            pygame.K_2: "green",
            pygame.K_3: "blue",
            pygame.K_4: "yellow",
        }
        return mapping.get(key)

    def _show_intro(self) -> None:
        self._draw_screen(
            title="TASK 2",
            subtitle="기억력과 감각 통합",
            footer="스페이스바로 시작",
            accent=COLOR_READY,
        )
        self._wait_for_key({pygame.K_SPACE})

    def _show_feedback(self, correct_count: int, total_count: int, exact: bool) -> None:
        title = "정확합니다" if exact else f"{correct_count}/{total_count}개 일치"
        self._draw_screen(
            title=title,
            subtitle="다음 시행으로 넘어갑니다.",
            footer="",
            accent=COLOR_SUCCESS if exact else COLOR_READY,
        )
        self._wait_ms(900)

    def _show_summary(self, result: dict[str, Any]) -> None:
        metrics = result["metrics"]
        lines = [
            f"시각 조건 점수: {_format_value(metrics['visual_condition_score'])}",
            f"시청각 조건 점수: {_format_value(metrics['audiovisual_condition_score'])}",
            f"TASK 2 점수: {_format_value(result['score'])}",
            f"감각 통합 효과: {_format_value(metrics['sensory_integration_effect'])}",
        ]
        while True:
            self._fill()
            self._render_center("결과", self.font_large, COLOR_SUCCESS, 140)
            for offset, line in enumerate(lines):
                self._render_center(line, self.font_small, COLOR_TEXT, 245 + offset * 44)
            self._render_center("ESC로 종료", self.font_small, COLOR_MUTED, 540)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            self.clock.tick(FPS)

    def _draw_color_stimulus(
        self,
        color_name: str,
        index: int,
        total: int,
        condition: str,
    ) -> None:
        color_info = COLORS[color_name]
        self._fill()
        self._render_center(f"{index}/{total}", self.font_medium, COLOR_MUTED, 85)
        pygame.draw.circle(self.screen, color_info["rgb"], (SCREEN_WIDTH // 2, 285), 115)
        self._render_center(color_info["label"], self.font_large, COLOR_TEXT, 455)
        if condition == "audiovisual":
            self._render_center(
                f"{color_info['frequency']}Hz",
                self.font_small,
                COLOR_MUTED,
                510,
            )
        pygame.display.flip()

    def _draw_blank(self, index: int, total: int) -> None:
        self._fill()
        self._render_center(f"{index}/{total}", self.font_medium, COLOR_MUTED, 85)
        self._render_center("...", self.font_large, COLOR_MUTED, 300)
        pygame.display.flip()

    def _draw_response_screen(
        self,
        selected_index: int,
        response: list[str],
        expected_length: int,
    ) -> None:
        self._fill()
        self._render_center(
            f"입력 {len(response) + 1}/{expected_length}",
            self.font_medium,
            COLOR_TEXT,
            80,
        )
        self._render_center(
            "숫자 1~4 또는 방향키 + 스페이스바",
            self.font_small,
            COLOR_MUTED,
            125,
        )

        start_x = 190
        y = 230
        box_size = 125
        gap = 35
        for index, color_name in enumerate(COLOR_ORDER):
            color_info = COLORS[color_name]
            rect = pygame.Rect(start_x + index * (box_size + gap), y, box_size, box_size)
            border_color = COLOR_TEXT if index == selected_index else COLOR_PANEL
            pygame.draw.rect(self.screen, color_info["rgb"], rect, border_radius=8)
            pygame.draw.rect(self.screen, border_color, rect, width=4, border_radius=8)
            self._render_text(
                f"{color_info['key']}. {color_info['label']}",
                self.font_small,
                COLOR_TEXT,
                rect.centerx,
                y + box_size + 34,
            )

        entered = " ".join(COLORS[color]["label"] for color in response)
        self._render_center(f"입력됨: {entered}", self.font_small, COLOR_TEXT, 470)
        pygame.display.flip()

    def _draw_screen(self, title: str, subtitle: str, footer: str, accent) -> None:
        self._fill()
        pygame.draw.rect(
            self.screen,
            COLOR_PANEL,
            pygame.Rect(165, 120, 630, 350),
            border_radius=8,
        )
        pygame.draw.circle(self.screen, accent, (SCREEN_WIDTH // 2, 205), 46)
        self._render_center(title, self.font_large, COLOR_TEXT, 295)
        self._render_center(subtitle, self.font_small, COLOR_TEXT, 370)
        if footer:
            self._render_center(footer, self.font_small, COLOR_MUTED, 520)
        pygame.display.flip()

    def _fill(self) -> None:
        self.screen.fill(COLOR_BACKGROUND)

    def _render_center(self, text: str, font, color, y: int) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def _render_text(self, text: str, font, color, x: int, y: int) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(x, y))
        self.screen.blit(surface, rect)

    def _wait_for_key(self, keys: set[int]) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if event.key in keys:
                        return
            self.clock.tick(FPS)

    def _wait_ms(self, duration_ms: int) -> None:
        end_time = time.perf_counter() + duration_ms / 1000
        while time.perf_counter() < end_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
            self.clock.tick(FPS)


def build_task2_result(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the shared task result payload from raw trial rows."""

    metrics = calculate_task2_metrics(trials)
    return {
        "task_id": "task2",
        "score": metrics["task2_score"],
        "metrics": metrics,
        "trials": trials,
    }


def calculate_task2_metrics(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate TASK 2 scores from trial dictionaries."""

    visual = _summarize_condition(trials, "visual")
    audiovisual = _summarize_condition(trials, "audiovisual")

    task2_score = None
    if visual["condition_score"] is not None and audiovisual["condition_score"] is not None:
        task2_score = round((visual["condition_score"] + audiovisual["condition_score"]) / 2, 1)

    sensory_integration_effect = None
    if visual["position_accuracy"] is not None and audiovisual["position_accuracy"] is not None:
        sensory_integration_effect = round(
            audiovisual["position_accuracy"] - visual["position_accuracy"],
            1,
        )

    return {
        "visual_position_accuracy": visual["position_accuracy"],
        "visual_memory_span": visual["memory_span"],
        "visual_memory_span_score": visual["memory_span_score"],
        "visual_condition_score": visual["condition_score"],
        "audiovisual_position_accuracy": audiovisual["position_accuracy"],
        "audiovisual_memory_span": audiovisual["memory_span"],
        "audiovisual_memory_span_score": audiovisual["memory_span_score"],
        "audiovisual_condition_score": audiovisual["condition_score"],
        "sensory_integration_effect": sensory_integration_effect,
        "task2_score": task2_score,
    }


def run_task2(participant_id: str = "P001") -> dict[str, Any]:
    """Run TASK 2 and return the shared result dictionary."""

    return Task2MemoryApp(participant_id).run()


def seed_from_participant(participant_id: str) -> int:
    """Create a stable random seed from an anonymous participant ID."""

    digest = hashlib.sha256(participant_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _summarize_condition(trials: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    condition_trials = [
        trial
        for trial in trials
        if trial.get("sensory_condition") == condition and trial.get("practice") is False
    ]
    total_items = sum(int(trial.get("sequence_length", 0)) for trial in condition_trials)
    correct_items = sum(
        int(trial.get("position_correct_count", 0)) for trial in condition_trials
    )

    position_accuracy = None
    if total_items > 0:
        position_accuracy = round(correct_items / total_items * 100, 1)

    exact_lengths = [
        int(trial.get("sequence_length", 0))
        for trial in condition_trials
        if trial.get("exact_sequence_correct") is True
    ]
    memory_span = max(exact_lengths) if exact_lengths else 0
    memory_span_score = round(memory_span / 6 * 100, 1)

    condition_score = None
    if position_accuracy is not None:
        condition_score = round(position_accuracy * 0.7 + memory_span_score * 0.3, 1)

    return {
        "position_accuracy": position_accuracy,
        "memory_span": memory_span,
        "memory_span_score": memory_span_score,
        "condition_score": condition_score,
    }


def _round_time(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _round_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)


def _format_value(value: float | None) -> str:
    if value is None:
        return "-"
    return str(round(value, 1))


if __name__ == "__main__":
    participant = sys.argv[1] if len(sys.argv) > 1 else "P001"
    payload = run_task2(participant)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

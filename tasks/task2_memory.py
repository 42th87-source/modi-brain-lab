"""TASK 2: sequence memory and sensory integration."""

from __future__ import annotations

import array
import hashlib
import math
import random
import sys
import time
from dataclasses import dataclass

import pygame

from config import (
    COLOR_BACKGROUND,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_READY,
    COLOR_SUCCESS,
    COLOR_TEXT,
    FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TASK2_BLANK_MS,
    TASK2_COLOR_ORDER,
    TASK2_COLORS,
    TASK2_PRACTICE_TRIAL,
    TASK2_STIMULUS_MS,
    TASK2_TRIALS,
)
from data_manager import save_task2_trials
from scoring import summarize_task2


@dataclass
class Task2TrialResult:
    participant_id: str
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

    def as_row(self) -> dict:
        return {
            "participant_id": self.participant_id,
            "trial_index": self.trial_index,
            "sensory_condition": self.sensory_condition,
            "sequence_length": self.sequence_length,
            "target_sequence": " ".join(self.target_sequence),
            "response_sequence": " ".join(self.response_sequence),
            "position_correct_count": self.position_correct_count,
            "exact_sequence_correct": self.exact_sequence_correct,
            "response_start_time": _round_time(self.response_start_time),
            "response_complete_time": _round_time(self.response_complete_time),
            "total_response_time_ms": _round_ms(self.total_response_time_ms),
            "random_seed": self.random_seed,
            "practice": self.practice,
        }


class TonePlayer:
    """Small optional tone player for the audiovisual condition."""

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
    """Run TASK 2 with keyboard controls standing in for MODI dial/button."""

    def __init__(self, participant_id: str) -> None:
        pygame.init()
        pygame.display.set_caption("MODI Brain Lab - TASK 2")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("malgungothic", 52)
        self.font_medium = pygame.font.SysFont("malgungothic", 32)
        self.font_small = pygame.font.SysFont("malgungothic", 22)
        self.participant_id = participant_id
        self.random_seed = _seed_from_participant(participant_id)
        self.random = random.Random(self.random_seed)
        self.records: list[dict] = []
        self.tone_player = TonePlayer()

    def run(self) -> None:
        self._show_intro()

        practice_condition, practice_length = TASK2_PRACTICE_TRIAL
        practice_sequence = self._generate_sequence(practice_length)
        practice_result = self._run_trial(
            trial_index=0,
            condition=practice_condition,
            sequence=practice_sequence,
            practice=True,
        )
        self.records.append(practice_result.as_row())

        for trial_index, (condition, sequence_length) in enumerate(TASK2_TRIALS, start=1):
            sequence = self._generate_sequence(sequence_length)
            result = self._run_trial(
                trial_index=trial_index,
                condition=condition,
                sequence=sequence,
                practice=False,
            )
            self.records.append(result.as_row())

        output_path = save_task2_trials(self.participant_id, self.records)
        summary = summarize_task2(self.records)
        self._show_summary(summary, output_path)
        pygame.quit()

    def _run_trial(
        self,
        trial_index: int,
        condition: str,
        sequence: list[str],
        practice: bool,
    ) -> Task2TrialResult:
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

        return Task2TrialResult(
            participant_id=self.participant_id,
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
            color = self.random.choice(TASK2_COLOR_ORDER)
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
            color_info = TASK2_COLORS[color_name]
            if condition == "audiovisual":
                self.tone_player.play(color_info["frequency"], TASK2_STIMULUS_MS)
            self._draw_color_stimulus(color_name, index, len(sequence), condition)
            self._wait_ms(TASK2_STIMULUS_MS)
            self._draw_blank(index, len(sequence))
            self._wait_ms(TASK2_BLANK_MS)

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
                        selected_index = (selected_index - 1) % len(TASK2_COLOR_ORDER)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        selected_index = (selected_index + 1) % len(TASK2_COLOR_ORDER)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        response.append(TASK2_COLOR_ORDER[selected_index])
                    else:
                        keyed_color = self._color_from_number_key(event.key)
                        if keyed_color is not None:
                            selected_index = TASK2_COLOR_ORDER.index(keyed_color)
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
        self._wait_ms(1000)

    def _show_summary(self, summary: dict, output_path) -> None:
        visual = summary["visual"]
        audiovisual = summary["audiovisual"]
        lines = [
            f"시각 조건 점수: {_format_value(visual['condition_score'])}",
            f"시청각 조건 점수: {_format_value(audiovisual['condition_score'])}",
            f"TASK 2 점수: {_format_value(summary['task2_score'])}",
            f"감각 통합 효과: {_format_value(summary['sensory_integration_effect'])}",
            f"저장 위치: {output_path}",
        ]
        while True:
            self._fill()
            self._render_center("결과", self.font_large, COLOR_SUCCESS, 120)
            for offset, line in enumerate(lines):
                self._render_center(line, self.font_small, COLOR_TEXT, 215 + offset * 42)
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
        color_info = TASK2_COLORS[color_name]
        self._fill()
        self._render_center(f"{index}/{total}", self.font_medium, COLOR_MUTED, 85)
        pygame.draw.circle(self.screen, color_info["rgb"], (SCREEN_WIDTH // 2, 285), 115)
        self._render_center(color_info["label"], self.font_large, COLOR_TEXT, 455)
        if condition == "audiovisual":
            tone_text = f"{color_info['frequency']}Hz"
            self._render_center(tone_text, self.font_small, COLOR_MUTED, 510)
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
        for index, color_name in enumerate(TASK2_COLOR_ORDER):
            color_info = TASK2_COLORS[color_name]
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

        entered = " ".join(TASK2_COLORS[color]["label"] for color in response)
        self._render_center(f"입력됨: {entered}", self.font_small, COLOR_TEXT, 470)
        pygame.display.flip()

    def _draw_screen(self, title: str, subtitle: str, footer: str, accent) -> None:
        self._fill()
        pygame.draw.rect(self.screen, COLOR_PANEL, pygame.Rect(165, 120, 630, 350), border_radius=8)
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


def _seed_from_participant(participant_id: str) -> int:
    digest = hashlib.sha256(participant_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


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


def run_task2(participant_id: str) -> None:
    Task2MemoryApp(participant_id).run()


if __name__ == "__main__":
    participant = sys.argv[1] if len(sys.argv) > 1 else "P001"
    run_task2(participant)

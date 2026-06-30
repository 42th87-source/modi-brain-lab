"""TASK 1: reaction speed and input method."""

from __future__ import annotations

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
    COLOR_STIMULUS,
    COLOR_SUCCESS,
    COLOR_TEXT,
    COLOR_WARNING,
    FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TASK1_DELAYED_REACTION_MS,
    TASK1_MAX_RETRY_PER_TRIAL,
    TASK1_MIN_VALID_REACTION_MS,
    TASK1_PRACTICE_SEQUENCE,
    TASK1_RANDOM_WAIT_MS_MAX,
    TASK1_RANDOM_WAIT_MS_MIN,
    TASK1_REQUIRED_VALID_PER_CONDITION,
    TASK1_TRIAL_SEQUENCE,
)
from data_manager import save_task1_trials
from scoring import summarize_task1


@dataclass
class TrialResult:
    participant_id: str
    trial_index: int
    input_condition: str
    random_wait_ms: int
    stimulus_time: float | None
    response_start_time: float | None
    response_complete_time: float | None
    reaction_time_ms: float | None
    completion_time_ms: float | None
    gyro_pitch: float | None
    gyro_roll: float | None
    gyro_angular_velocity: float | None
    early_response: bool
    delayed_response: bool
    valid: bool
    retry_count: int
    technical_error: bool
    practice: bool

    def as_row(self) -> dict:
        return {
            "participant_id": self.participant_id,
            "trial_index": self.trial_index,
            "input_condition": self.input_condition,
            "random_wait_ms": self.random_wait_ms,
            "stimulus_time": _round_time(self.stimulus_time),
            "response_start_time": _round_time(self.response_start_time),
            "response_complete_time": _round_time(self.response_complete_time),
            "reaction_time_ms": _round_ms(self.reaction_time_ms),
            "completion_time_ms": _round_ms(self.completion_time_ms),
            "gyro_pitch": self.gyro_pitch,
            "gyro_roll": self.gyro_roll,
            "gyro_angular_velocity": self.gyro_angular_velocity,
            "early_response": self.early_response,
            "delayed_response": self.delayed_response,
            "valid": self.valid,
            "retry_count": self.retry_count,
            "technical_error": self.technical_error,
            "practice": self.practice,
        }


class Task1ReactionApp:
    """Run TASK 1 with keyboard controls standing in for MODI modules."""

    def __init__(self, participant_id: str) -> None:
        pygame.init()
        pygame.display.set_caption("MODI Brain Lab - TASK 1")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("malgungothic", 58)
        self.font_medium = pygame.font.SysFont("malgungothic", 34)
        self.font_small = pygame.font.SysFont("malgungothic", 24)
        self.participant_id = participant_id
        self.records: list[dict] = []

    def run(self) -> None:
        self._show_intro()

        for index, condition in enumerate(TASK1_PRACTICE_SEQUENCE, start=1):
            result = self._run_until_accepted(
                trial_index=index,
                condition=condition,
                practice=True,
            )
            self.records.append(result.as_row())

        for index, condition in enumerate(TASK1_TRIAL_SEQUENCE, start=1):
            result = self._run_until_accepted(
                trial_index=index,
                condition=condition,
                practice=False,
            )
            self.records.append(result.as_row())

        self._top_up_valid_trials()
        output_path = save_task1_trials(self.participant_id, self.records)
        summary = summarize_task1(self.records)
        self._show_summary(summary, output_path)
        pygame.quit()

    def _run_until_accepted(
        self,
        trial_index: int,
        condition: str,
        practice: bool,
    ) -> TrialResult:
        retry_count = 0
        while True:
            result = self._run_trial(
                trial_index=trial_index,
                condition=condition,
                retry_count=retry_count,
                practice=practice,
            )
            if practice or result.valid or retry_count >= TASK1_MAX_RETRY_PER_TRIAL:
                return result
            retry_count += 1
            self._show_message(
                "다시 한 번",
                "조기/예측 반응은 재시행합니다.",
                1100,
                COLOR_WARNING,
            )

    def _run_trial(
        self,
        trial_index: int,
        condition: str,
        retry_count: int,
        practice: bool,
    ) -> TrialResult:
        random_wait_ms = random.randint(TASK1_RANDOM_WAIT_MS_MIN, TASK1_RANDOM_WAIT_MS_MAX)
        trial_label = "연습" if practice else f"측정 {trial_index}/8"
        condition_label = "버튼" if condition == "button" else "자이로"

        self._flush_events()
        self._draw_screen(
            title=f"{trial_label} - {condition_label}",
            subtitle=self._condition_instruction(condition),
            accent=COLOR_READY,
            footer="준비하세요",
        )
        self._wait_ms(900)

        wait_start = time.perf_counter()
        early_response_time = self._wait_for_input_until(
            wait_start + random_wait_ms / 1000,
            condition,
            waiting_for_stimulus=True,
        )

        if early_response_time is not None:
            return TrialResult(
                participant_id=self.participant_id,
                trial_index=trial_index,
                input_condition=condition,
                random_wait_ms=random_wait_ms,
                stimulus_time=None,
                response_start_time=early_response_time,
                response_complete_time=early_response_time,
                reaction_time_ms=None,
                completion_time_ms=None,
                gyro_pitch=None,
                gyro_roll=None,
                gyro_angular_velocity=None,
                early_response=True,
                delayed_response=False,
                valid=False,
                retry_count=retry_count,
                technical_error=False,
                practice=practice,
            )

        stimulus_time = time.perf_counter()
        self._draw_screen(
            title="지금!",
            subtitle=self._condition_instruction(condition),
            accent=COLOR_STIMULUS,
            footer="입력하세요",
        )

        response_time = self._wait_for_input_until(
            stimulus_time + TASK1_DELAYED_REACTION_MS / 1000,
            condition,
            waiting_for_stimulus=False,
        )

        if response_time is None:
            response_time = time.perf_counter()

        reaction_time_ms = (response_time - stimulus_time) * 1000
        early_response = reaction_time_ms < TASK1_MIN_VALID_REACTION_MS
        delayed_response = reaction_time_ms > TASK1_DELAYED_REACTION_MS
        valid = not early_response

        return TrialResult(
            participant_id=self.participant_id,
            trial_index=trial_index,
            input_condition=condition,
            random_wait_ms=random_wait_ms,
            stimulus_time=stimulus_time,
            response_start_time=response_time,
            response_complete_time=response_time,
            reaction_time_ms=reaction_time_ms,
            completion_time_ms=0 if condition == "button" else reaction_time_ms,
            gyro_pitch=None,
            gyro_roll=None,
            gyro_angular_velocity=None,
            early_response=early_response,
            delayed_response=delayed_response,
            valid=valid,
            retry_count=retry_count,
            technical_error=False,
            practice=practice,
        )

    def _top_up_valid_trials(self) -> None:
        for condition in ("button", "gyro"):
            valid_count = self._valid_count(condition)
            while valid_count < TASK1_REQUIRED_VALID_PER_CONDITION:
                self._show_message(
                    "추가 시행",
                    f"{condition} 조건 유효 시행이 부족해서 1회 더 진행합니다.",
                    1400,
                    COLOR_WARNING,
                )
                result = self._run_until_accepted(
                    trial_index=len([r for r in self.records if not r["practice"]]) + 1,
                    condition=condition,
                    practice=False,
                )
                self.records.append(result.as_row())
                valid_count = self._valid_count(condition)

    def _valid_count(self, condition: str) -> int:
        return sum(
            1
            for record in self.records
            if record["input_condition"] == condition
            and record["valid"] is True
            and record["delayed_response"] is False
            and record["practice"] is False
        )

    def _wait_for_input_until(
        self,
        deadline: float,
        condition: str,
        waiting_for_stimulus: bool,
    ) -> float | None:
        while time.perf_counter() < deadline:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if self._matches_condition(event.key, condition):
                        return time.perf_counter()

            if waiting_for_stimulus:
                self._draw_waiting_frame(deadline)
            self.clock.tick(FPS)
        return None

    def _matches_condition(self, key: int, condition: str) -> bool:
        if condition == "button":
            return key == pygame.K_SPACE
        return key in (pygame.K_DOWN, pygame.K_g)

    def _condition_instruction(self, condition: str) -> str:
        if condition == "button":
            return "자극이 나오면 스페이스바를 누르세요."
        return "자극이 나오면 아래 방향키 또는 G 키를 누르세요."

    def _show_intro(self) -> None:
        self._draw_screen(
            title="TASK 1",
            subtitle="반응속도와 입력 방식",
            accent=COLOR_READY,
            footer="스페이스바로 시작",
        )
        self._wait_for_start()

    def _show_summary(self, summary: dict, output_path) -> None:
        lines = [
            f"버튼 대표값: {_format_value(summary['button_median_ms'])} ms",
            f"자이로 대표값: {_format_value(summary['gyro_median_ms'])} ms",
            f"입력 방식 차이: {_format_value(summary['input_method_difference_ms'])} ms",
            f"저장 위치: {output_path}",
        ]
        while True:
            self._fill()
            self._render_center("결과", self.font_large, COLOR_SUCCESS, 150)
            for offset, line in enumerate(lines):
                self._render_center(line, self.font_small, COLOR_TEXT, 245 + offset * 42)
            self._render_center("ESC로 종료", self.font_small, COLOR_MUTED, 540)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            self.clock.tick(FPS)

    def _show_message(self, title: str, subtitle: str, duration_ms: int, accent) -> None:
        self._draw_screen(title=title, subtitle=subtitle, accent=accent, footer="")
        self._wait_ms(duration_ms)

    def _draw_waiting_frame(self, deadline: float) -> None:
        remaining_ms = max(0, int((deadline - time.perf_counter()) * 1000))
        self._draw_screen(
            title="준비",
            subtitle="자극이 나오기 전에는 입력하지 마세요.",
            accent=COLOR_READY,
            footer=f"대기 중 {remaining_ms} ms",
        )

    def _draw_screen(self, title: str, subtitle: str, accent, footer: str) -> None:
        self._fill()
        pygame.draw.rect(self.screen, COLOR_PANEL, pygame.Rect(170, 115, 620, 360), border_radius=8)
        pygame.draw.circle(self.screen, accent, (SCREEN_WIDTH // 2, 210), 48)
        self._render_center(title, self.font_large, COLOR_TEXT, 300)
        self._render_center(subtitle, self.font_small, COLOR_TEXT, 372)
        if footer:
            self._render_center(footer, self.font_small, COLOR_MUTED, 520)
        pygame.display.flip()

    def _fill(self) -> None:
        self.screen.fill(COLOR_BACKGROUND)

    def _render_center(self, text: str, font, color, y: int) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def _wait_for_start(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if event.key == pygame.K_SPACE:
                        return
            self.clock.tick(FPS)

    def _wait_ms(self, duration_ms: int) -> None:
        end_time = time.perf_counter() + duration_ms / 1000
        while time.perf_counter() < end_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
            self.clock.tick(FPS)

    def _flush_events(self) -> None:
        pygame.event.clear()


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


def run_task1(participant_id: str) -> None:
    Task1ReactionApp(participant_id).run()


if __name__ == "__main__":
    participant = sys.argv[1] if len(sys.argv) > 1 else "P001"
    run_task1(participant)

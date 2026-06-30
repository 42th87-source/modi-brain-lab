"""pygame 기반 시작·안내·진행·결과·순위 화면을 정의한다."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from config import WINDOW_HEIGHT, WINDOW_WIDTH
from ui.widgets import (
    COLORS,
    Button,
    TextInput,
    draw_metric_rows,
    draw_text,
    draw_wrapped_text,
    validate_id_format,
)

if TYPE_CHECKING:
    from dashboard import App


class BaseScreen:
    """모든 화면이 공유하는 이벤트·그리기 인터페이스다."""

    name = "base"

    def __init__(self, app: "App") -> None:
        self.app = app
        self.buttons: list[Button] = []
        self.message = ""
        self.error = ""

    def on_show(self, **kwargs: Any) -> None:
        self.message = str(kwargs.get("message", ""))
        self.error = ""

    def handle_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            if button.handle_event(event):
                return

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["bg"])

    def draw_header(self, surface: pygame.Surface, title: str, subtitle: str = "") -> None:
        draw_text(surface, title, (64, 46), size=34, bold=True)
        if subtitle:
            draw_text(surface, subtitle, (66, 94), size=19, color=COLORS["muted"])

    def draw_buttons(self, surface: pygame.Surface) -> None:
        for button in self.buttons:
            button.draw(surface)


class StartScreen(BaseScreen):
    name = "start"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.input = TextInput(
            (WINDOW_WIDTH // 2 - 230, 330, 460, 62),
            placeholder="참가자 ID",
            on_submit=self.submit,
        )
        self.buttons = [
            Button((WINDOW_WIDTH // 2 - 120, 425, 240, 58), "시작하기", lambda: self.submit(self.input.value))
        ]

    def on_show(self, **kwargs: Any) -> None:
        super().on_show(**kwargs)
        self.input.value = ""
        self.input.focus()

    def submit(self, raw_id: str) -> None:
        valid, message = validate_id_format(raw_id)
        if not valid:
            self.error = message
            return
        try:
            self.app.start_session(raw_id)
        except ValueError as error:
            self.error = str(error)
            return
        self.input.blur()
        self.app.show_screen("overview")

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.input.handle_event(event):
            return
        super().handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        draw_text(surface, "MODI 인지 능력 체험", (WINDOW_WIDTH // 2, 155), size=42, bold=True, center=True)
        draw_text(
            surface,
            "결과 확인에 사용할 참가자 ID를 입력해 주세요.",
            (WINDOW_WIDTH // 2, 225),
            size=23,
            color=COLORS["muted"],
            center=True,
        )
        draw_text(
            surface,
            "실명 대신 기억하기 쉬운 별명을 권장합니다.",
            (WINDOW_WIDTH // 2, 265),
            size=18,
            color=COLORS["muted"],
            center=True,
        )
        self.input.draw(surface)
        if self.error:
            draw_text(surface, self.error, (WINDOW_WIDTH // 2, 408), size=17, color=COLORS["error"], center=True)
        self.draw_buttons(surface)


class OverviewScreen(BaseScreen):
    name = "overview"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.buttons = [Button((WINDOW_WIDTH - 290, WINDOW_HEIGHT - 95, 220, 56), "TASK 1 시작", self.start)]

    def start(self) -> None:
        self.app.show_task_instruction(1)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        participant = self.app.state.get("participant_id", "-")
        self.draw_header(surface, "전체 테스트 안내", f"참가자: {participant}")
        panel = pygame.Rect(62, 145, WINDOW_WIDTH - 124, 410)
        pygame.draw.rect(surface, COLORS["panel"], panel, border_radius=16)
        lines = [
            "1. 반응속도와 입력 방식",
            "2. 기억력과 감각 통합",
            "3. 선택적 주의와 감각 모순",
            "4. 운동 협응과 이중 과제",
        ]
        y = 185
        for line in lines:
            draw_text(surface, line, (100, y), size=25, bold=True)
            y += 72
        draw_text(surface, "연습 시행은 점수에 포함되지 않습니다.", (100, 492), size=19, color=COLORS["muted"])
        self.draw_buttons(surface)


TASK_INFO = {
    1: {
        "title": "TASK 1. 반응속도와 입력 방식",
        "body": "빛과 소리가 나오면 안내된 방식으로 빠르게 반응하세요. 버튼 조건에서는 버튼을 누르고, 자이로 조건에서는 손목을 아래쪽으로 한 번 뒤집습니다. 자극 전에 반응하면 다시 측정합니다.",
    },
    2: {
        "title": "TASK 2. 기억력과 감각 통합",
        "body": "제시되는 색상 순서를 기억하세요. 다이얼을 돌려 색상을 선택하고 버튼을 눌러 확정합니다. 일부 시행에서는 색상과 함께 소리가 제시됩니다.",
    },
    3: {
        "title": "TASK 3. 선택적 주의와 감각 모순",
        "body": "빛이 나오면 버튼을 누르세요. 소리만 나오면 누르지 마세요. 시각 목표에 집중하고 청각 방해 자극에 대한 반응을 억제합니다.",
    },
    4: {
        "title": "TASK 4. 운동 협응과 이중 과제",
        "body": "자이로로 화면 속 커서를 중앙 목표 안에 유지하면서 스피커 비트에 맞춰 버튼을 누르세요. 먼저 단독 기준을 측정한 뒤 두 동작을 함께 수행합니다.",
    },
}


class TaskInstructionScreen(BaseScreen):
    name = "task_instruction"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.task_number = 1
        self.buttons = [Button((WINDOW_WIDTH - 290, WINDOW_HEIGHT - 95, 220, 56), "테스트 시작", self.start)]

    def on_show(self, **kwargs: Any) -> None:
        super().on_show(**kwargs)
        self.task_number = int(kwargs["task_number"])

    def start(self) -> None:
        self.app.run_task(self.task_number)

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        info = TASK_INFO[self.task_number]
        self.draw_header(surface, info["title"], "안내를 읽고 준비되면 시작하세요.")
        panel = pygame.Rect(62, 155, WINDOW_WIDTH - 124, 360)
        pygame.draw.rect(surface, COLORS["panel"], panel, border_radius=16)
        draw_wrapped_text(surface, info["body"], panel.inflate(-70, -70), size=26, line_gap=14)
        if self.error:
            draw_text(surface, self.error, (70, 555), size=18, color=COLORS["error"])
        self.draw_buttons(surface)


class TaskProgressScreen(BaseScreen):
    name = "task_progress"

    def on_show(self, **kwargs: Any) -> None:
        super().on_show(**kwargs)
        self.task_number = int(kwargs.get("task_number", 1))
        self.status = str(kwargs.get("status", "준비 중입니다."))

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        self.draw_header(surface, f"TASK {self.task_number} 진행")
        draw_text(surface, self.status, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), size=38, bold=True, center=True)


class InterimResultScreen(BaseScreen):
    name = "interim_result"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.task_number = 1
        self.result: dict[str, Any] = {}
        self.buttons = [Button((WINDOW_WIDTH - 310, WINDOW_HEIGHT - 95, 240, 56), "다음", self.next)]

    def on_show(self, **kwargs: Any) -> None:
        super().on_show(**kwargs)
        self.task_number = int(kwargs["task_number"])
        self.result = dict(kwargs.get("result") or {})

    def next(self) -> None:
        if self.task_number < 4:
            self.app.show_task_instruction(self.task_number + 1)
        else:
            self.app.finish_current_session()

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        self.draw_header(surface, f"TASK {self.task_number} 결과")
        metrics = self.result.get("metrics") or {}
        if self.task_number == 1:
            rows = [
                ("버튼 대표 반응시간", f"{metrics.get('button_median_ms', '-')} ms"),
                ("자이로 대표 반응시간", f"{metrics.get('gyro_median_ms', '-')} ms"),
                ("TASK 1 점수", self.result.get("score", "-")),
            ]
        elif self.task_number == 2:
            rows = [
                ("시각 조건 정확도", f"{metrics.get('visual_accuracy', '-')}%"),
                ("시청각 조건 정확도", f"{metrics.get('audiovisual_accuracy', '-')}%"),
                ("TASK 2 점수", self.result.get("score", "-")),
            ]
        elif self.task_number == 3:
            rows = [
                ("적중률", f"{metrics.get('hit_rate', '-')}%"),
                ("억제 성공률", f"{metrics.get('inhibition_success_rate', '-')}%"),
                ("TASK 3 점수", self.result.get("score", "-")),
            ]
        else:
            rows = [
                ("커서 목표 유지율", f"{metrics.get('dual_cursor_hold_rate', '-')}%"),
                ("리듬 점수", metrics.get("rhythm_score", "-")),
                ("TASK 4 점수", self.result.get("score", "-")),
            ]
        draw_metric_rows(surface, rows, pygame.Rect(100, 175, WINDOW_WIDTH - 200, 220))
        self.draw_buttons(surface)


class FinalResultScreen(BaseScreen):
    name = "final_result"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.report: dict[str, Any] = {}
        self.buttons = [
            Button((70, WINDOW_HEIGHT - 95, 190, 56), "처음으로", app.restart, primary=False),
            Button((WINDOW_WIDTH - 280, WINDOW_HEIGHT - 95, 210, 56), "순위 보기", lambda: app.show_screen("ranking")),
        ]

    def on_show(self, **kwargs: Any) -> None:
        super().on_show(**kwargs)
        self.report = dict(kwargs.get("report") or self.app.current_report())

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        participant = self.report.get("participant_id", "-")
        rank = self.report.get("rank")
        count = self.report.get("participant_count", 0)
        self.draw_header(surface, f"{participant}님의 결과", f"현재 순위: {rank or '-'}위 / 전체 {count}명")
        scores = self.report.get("task_scores") or {}
        rows = [(f"TASK {index} 점수", scores.get(f"task{index}") if scores.get(f"task{index}") is not None else "미실시") for index in range(1, 5)]
        rows.append(("현재 종합점수", self.report.get("total_score", "-")))
        draw_metric_rows(surface, rows, pygame.Rect(80, 155, WINDOW_WIDTH - 160, 260))
        disclaimer = "이 결과는 체험 및 탐구를 위한 간이 측정이며, 의학적 진단이나 개인의 능력을 확정하는 자료가 아닙니다."
        draw_wrapped_text(surface, disclaimer, pygame.Rect(90, 455, WINDOW_WIDTH - 180, 80), size=18, color=COLORS["muted"])
        self.draw_buttons(surface)


class RankingScreen(BaseScreen):
    name = "ranking"

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.buttons = [
            Button((70, WINDOW_HEIGHT - 95, 190, 56), "처음으로", app.restart, primary=False),
            Button((WINDOW_WIDTH - 280, WINDOW_HEIGHT - 95, 210, 56), "결과로", lambda: app.show_screen("final_result"), primary=False),
        ]

    def draw(self, surface: pygame.Surface) -> None:
        super().draw(surface)
        self.draw_header(surface, "실시간 순위", "현재까지 완료된 참가자 기준")
        leaderboard = self.app.get_top_rankings()
        panel = pygame.Rect(100, 145, WINDOW_WIDTH - 200, 440)
        pygame.draw.rect(surface, COLORS["panel"], panel, border_radius=14)
        current_id = self.app.state.get("participant_id")
        y = panel.y + 22
        for entry in leaderboard[:10]:
            if entry["participant_id"] == current_id:
                pygame.draw.rect(surface, COLORS["highlight"], (panel.x + 12, y - 6, panel.width - 24, 36), border_radius=8)
            draw_text(surface, f"{entry['rank']}위", (panel.x + 30, y), size=20, bold=True)
            draw_text(surface, entry["participant_id"], (panel.x + 140, y), size=20)
            draw_text(surface, f"{entry['total_score']:.1f}", (panel.right - 100, y), size=20, bold=True)
            y += 39
        if not leaderboard:
            draw_text(surface, "아직 순위 자료가 없습니다.", panel.center, size=24, color=COLORS["muted"], center=True)
        self.draw_buttons(surface)


SCREEN_TYPES = (
    StartScreen,
    OverviewScreen,
    TaskInstructionScreen,
    TaskProgressScreen,
    InterimResultScreen,
    FinalResultScreen,
    RankingScreen,
)

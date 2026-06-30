"""pygame 화면 흐름과 TASK 실행, 데이터 저장을 연결하는 메인 컨트롤러다."""

from __future__ import annotations

import importlib
import os
from typing import Any, Callable

import pygame

from config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from data_manager import DataManager, get_data_manager
from ui.screens import SCREEN_TYPES


TaskRunner = Callable[[str], dict[str, Any]]


class App:
    """참가자 세션부터 결과·순위 화면까지 관리하는 pygame 애플리케이션이다."""

    def __init__(
        self,
        *,
        data_manager: DataManager | None = None,
        dev_mode: bool | None = None,
        task_runners: dict[int, TaskRunner] | None = None,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("MODI 인지 능력 체험")
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.data_manager = data_manager or get_data_manager()
        self.dev_mode = (
            os.environ.get("MODI_DEV_MODE", "1") == "1" if dev_mode is None else dev_mode
        )
        self.task_runners = task_runners or {}
        self.state: dict[str, Any] = {}
        self.running = False
        self.screens = {screen_type.name: screen_type(self) for screen_type in SCREEN_TYPES}
        self.current_screen = self.screens["start"]
        self.current_screen.on_show()

    def run(self) -> None:
        """종료 요청이 올 때까지 pygame 이벤트 루프를 실행한다."""

        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    self.current_screen.handle_event(event)
            self.current_screen.draw(self.surface)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def show_screen(self, name: str, **kwargs: Any) -> None:
        """이름으로 화면을 전환한다."""

        if name not in self.screens:
            raise ValueError(f"등록되지 않은 화면입니다: {name}")
        self.current_screen = self.screens[name]
        self.current_screen.on_show(**kwargs)

    def start_session(self, participant_id: str) -> dict[str, Any]:
        """ID를 검증해 참가자 세션을 생성하고 공통 상태에 저장한다."""

        session = self.data_manager.create_participant_session(participant_id)
        self.state = {
            "participant_id": session["participant_id"],
            "session_id": session["session_id"],
            "task_results": {},
        }
        return session

    def restart(self) -> None:
        """새 참가자를 받을 수 있도록 화면 상태를 초기화한다."""

        self.state = {}
        self.show_screen("start")

    def show_task_instruction(self, task_number: int) -> None:
        """TASK 번호에 맞는 안내 화면을 표시한다."""

        self.show_screen("task_instruction", task_number=task_number)

    def run_task(self, task_number: int) -> None:
        """TASK 실행기를 호출하고 결과를 채점·저장한 뒤 중간 결과를 표시한다."""

        participant_id = self.state.get("participant_id")
        session_id = self.state.get("session_id")
        if not participant_id or not session_id:
            raise RuntimeError("먼저 참가자 세션을 생성해야 합니다.")
        self.show_screen("task_progress", task_number=task_number, status="테스트를 실행하고 있습니다.")
        self.current_screen.draw(self.surface)
        pygame.display.flip()
        try:
            runner = self._get_task_runner(task_number)
            result = runner(participant_id)
            self._restore_display()
            saved = self.data_manager.save_task_result(session_id, result)
        except Exception as error:
            self._restore_display()
            self.show_screen("task_instruction", task_number=task_number)
            self.current_screen.error = f"TASK 실행 오류: {error}"
            return
        self.state["task_results"][f"task{task_number}"] = saved
        self.show_screen("interim_result", task_number=task_number, result=saved)

    def finish_current_session(self) -> dict[str, Any]:
        """현재 세션을 완료하고 개인 최종 결과 화면을 표시한다."""

        session_id = self.state.get("session_id")
        if not session_id:
            raise RuntimeError("진행 중인 세션이 없습니다.")
        report = self.data_manager.complete_session(session_id, require_all=False)
        self.state["last_report"] = report
        self.show_screen("final_result", report=report)
        return report

    def current_report(self) -> dict[str, Any]:
        """현재 참가자의 최신 개인 결과를 반환한다."""

        if self.state.get("last_report"):
            return dict(self.state["last_report"])
        session_id = self.state.get("session_id")
        return self.data_manager.build_participant_report(session_id) if session_id else {}

    def get_top_rankings(self) -> list[dict[str, Any]]:
        """UI 표시용 상위 10명 순위를 반환한다."""

        return self.data_manager.get_leaderboard(limit=10)

    def _get_task_runner(self, task_number: int) -> TaskRunner:
        if task_number in self.task_runners:
            return self.task_runners[task_number]
        candidates = {
            1: ("tasks.task1_reaction", ("run_task1", "run_task")),
            2: ("tasks.task2_memory", ("run_task2", "run_task")),
            3: ("tasks.task3_attention", ("run_task3", "run_task")),
            4: ("tasks.task4_coordination", ("run_task4", "run_task")),
        }
        if task_number not in candidates:
            raise ValueError(f"아직 지원하지 않는 TASK입니다: {task_number}")
        module_name, function_names = candidates[task_number]
        module = importlib.import_module(module_name)
        for function_name in function_names:
            runner = getattr(module, function_name, None)
            if callable(runner):
                return runner
        if self.dev_mode:
            return self._demo_runner(task_number)
        raise RuntimeError(f"{module_name}에 실행 함수가 없습니다.")

    @staticmethod
    def _demo_runner(task_number: int) -> TaskRunner:
        """실제 TASK가 병합되기 전 UI 연결을 확인하는 개발용 결과를 만든다."""

        def task1(_participant_id: str) -> dict[str, Any]:
            return {
                "task_id": "task1",
                "metrics": {"button_median_ms": 310, "gyro_median_ms": 365},
                "trials": [],
            }

        def task2(_participant_id: str) -> dict[str, Any]:
            return {
                "task_id": "task2",
                "metrics": {
                    "visual_accuracy": 78,
                    "audiovisual_accuracy": 84,
                    "visual_memory_span": 4,
                    "audiovisual_memory_span": 5,
                },
                "trials": [],
            }

        def task3(_participant_id: str) -> dict[str, Any]:
            trials = []
            for index, condition in enumerate(
                ("congruent", "visual_only", "audio_only", "none") * 2,
                start=1,
            ):
                has_light = condition in {"congruent", "visual_only"}
                trials.append(
                    {
                        "trial_index": index,
                        "stimulus_condition": condition,
                        "reaction_time_ms": 320 if has_light else None,
                        "hit": has_light,
                        "miss": False,
                        "false_alarm": False,
                        "correct_rejection": not has_light,
                    }
                )
            return {"task_id": "task3", "score": None, "metrics": {}, "trials": trials}

        def task4(_participant_id: str) -> dict[str, Any]:
            trials = []
            for index in range(30):
                trials.append({"phase": "cursor_baseline", "sample_time": index / 30, "inside_target": True})
                trials.append({"phase": "dual_task", "sample_time": index / 30, "inside_target": index % 5 != 0})
            for phase in ("rhythm_baseline", "dual_task"):
                for index in range(8):
                    trials.append({"phase": phase, "beat_index": index + 1, "beat_error_ms": 80, "missed_beat": False, "extra_press": False})
            return {"task_id": "task4", "score": None, "metrics": {}, "trials": trials}

        return {1: task1, 2: task2, 3: task3, 4: task4}[task_number]

    def _restore_display(self) -> None:
        """독립 pygame TASK 종료 후 대시보드 화면을 복구한다."""

        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            pygame.display.init()
        pygame.display.set_caption("MODI 인지 능력 체험")
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def run_dashboard() -> None:
    """기본 설정으로 대시보드를 실행한다."""

    App().run()


if __name__ == "__main__":
    run_dashboard()

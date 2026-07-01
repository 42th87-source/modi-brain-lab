"""참가자 세션과 테스트 결과를 일관된 형태로 표현한다."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """정렬 가능한 UTC ISO 8601 시각 문자열을 반환한다."""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class TaskResult:
    """하나의 테스트에서 생성된 점수, 측정값과 시행 자료다."""

    task_id: str
    score: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    trials: list[dict[str, Any]] = field(default_factory=list)
    completed_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "TaskResult":
        """TASK 코드가 반환한 딕셔너리를 표준 결과 객체로 변환한다."""

        return cls(
            task_id=str(value["task_id"]),
            score=value.get("score"),
            metrics=dict(value.get("metrics") or {}),
            trials=list(value.get("trials") or []),
            completed_at=str(value.get("completed_at") or utc_now_iso()),
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON 저장에 적합한 딕셔너리를 반환한다."""

        return asdict(self)

@dataclass(slots=True)
class ParticipantSession:
    """한 참가자가 네 테스트를 수행하는 전체 세션을 표현한다."""

    participant_id: str
    session_id: str
    started_at: str = field(default_factory=utc_now_iso)
    completed_at: str | None = None
    status: str = "in_progress"
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    total_score: float | None = None
    rank: int | None = None
    program_version: str = "0.1.0"

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "ParticipantSession":
        """저장된 세션 딕셔너리를 객체로 복원한다."""

        return cls(
            participant_id=str(value["participant_id"]),
            session_id=str(value["session_id"]),
            started_at=str(value.get("started_at") or utc_now_iso()),
            completed_at=value.get("completed_at"),
            status=str(value.get("status") or "in_progress"),
            task_results=dict(value.get("task_results") or {}),
            total_score=value.get("total_score"),
            rank=value.get("rank"),
            program_version=str(value.get("program_version") or "0.1.0"),
        )

    def add_task_result(self, result: TaskResult) -> None:
        """완료된 테스트 결과를 세션에 추가하거나 교체한다."""

        self.task_results[result.task_id] = result.to_dict()

    def to_dict(self) -> dict[str, Any]:
        """JSON 저장에 적합한 딕셔너리를 반환한다."""

        return asdict(self)

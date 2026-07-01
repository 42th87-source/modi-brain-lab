"""참가자 세션, 테스트 결과, 시행 자료와 순위를 안전하게 저장·조회한다."""

from __future__ import annotations

import csv
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from analysis.participant import ParticipantSession, TaskResult, utc_now_iso
from config import (
    DATA_DIR,
    PARTICIPANT_ID_MAX_LENGTH,
    PARTICIPANT_ID_MIN_LENGTH,
    PARTICIPANTS_CSV,
    SESSIONS_DIR,
    TASK_IDS,
    TRIALS_DIR,
)
from scoring import calculate_total_score, score_task


PARTICIPANT_COLUMNS = [
    "participant_id",
    "session_id",
    "started_at",
    "completed_at",
    "status",
    "task1_score",
    "task2_score",
    "task3_score",
    "task4_score",
    "total_score",
    "rank",
]

_ID_PATTERN = re.compile(r"^[가-힣A-Za-z0-9_-]+$")


class DataManager:
    """파일 기반 참가자 데이터 저장소를 관리한다."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.sessions_dir = self.data_dir / SESSIONS_DIR.name
        self.trials_dir = self.data_dir / TRIALS_DIR.name
        self.participants_csv = self.data_dir / PARTICIPANTS_CSV.name
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.trials_dir.mkdir(parents=True, exist_ok=True)
        if not self.participants_csv.exists():
            self._write_participant_rows([])

    @staticmethod
    def normalize_participant_id(participant_id: str) -> str:
        """참가자 ID의 앞뒤 공백을 제거한다."""

        return str(participant_id).strip()

    @classmethod
    def validate_participant_id(cls, participant_id: str) -> tuple[bool, str | None]:
        """UI에서 바로 표시할 수 있는 ID 검증 결과와 오류 메시지를 반환한다."""

        participant_id = cls.normalize_participant_id(participant_id)
        if not participant_id:
            return False, "ID를 입력해 주세요."
        if not PARTICIPANT_ID_MIN_LENGTH <= len(participant_id) <= PARTICIPANT_ID_MAX_LENGTH:
            return False, f"ID는 {PARTICIPANT_ID_MIN_LENGTH}~{PARTICIPANT_ID_MAX_LENGTH}자로 입력해 주세요."
        if not _ID_PATTERN.fullmatch(participant_id):
            return False, "ID에는 한글, 영문, 숫자, _, -만 사용할 수 있습니다."
        return True, None

    def is_participant_id_available(self, participant_id: str) -> bool:
        """형식이 올바르고 기존 완료·진행 세션에서 사용되지 않은 ID인지 확인한다."""

        valid, _ = self.validate_participant_id(participant_id)
        if not valid:
            return False
        normalized = self.normalize_participant_id(participant_id).casefold()
        return all(row["participant_id"].casefold() != normalized for row in self.load_participant_rows())

    def create_participant_session(self, participant_id: str) -> dict[str, Any]:
        """검증된 ID로 새 참가자 세션을 생성하고 저장한다."""

        participant_id = self.normalize_participant_id(participant_id)
        valid, message = self.validate_participant_id(participant_id)
        if not valid:
            raise ValueError(message)
        if not self.is_participant_id_available(participant_id):
            raise ValueError("이미 사용 중인 ID입니다. 다른 ID를 입력해 주세요.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        session = ParticipantSession(
            participant_id=participant_id,
            session_id=f"{timestamp}-{uuid4().hex[:8]}",
        )
        self._write_session(session)
        self._upsert_participant_row(self._session_to_row(session))
        return session.to_dict()

    def get_session(self, session_id: str) -> ParticipantSession:
        """세션 ID에 해당하는 저장 자료를 읽는다."""

        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"세션을 찾을 수 없습니다: {session_id}")
        return ParticipantSession.from_mapping(json.loads(path.read_text(encoding="utf-8")))

    def save_task_result(
        self,
        session_id: str,
        result: Mapping[str, Any],
        *,
        references: Mapping[str, Iterable[Any]] | None = None,
    ) -> dict[str, Any]:
        """TASK 결과를 채점하고 세션 JSON 및 시행 CSV에 즉시 저장한다."""

        session = self.get_session(session_id)
        standardized = score_task(result, references=references)
        task_result = TaskResult.from_mapping(standardized)
        if task_result.task_id not in TASK_IDS:
            raise ValueError(f"알 수 없는 task_id입니다: {task_result.task_id}")
        session.add_task_result(task_result)
        session.total_score = calculate_total_score(self._task_scores(session))
        self._write_session(session)
        self._write_trials(session, task_result)
        self._upsert_participant_row(self._session_to_row(session))
        self.refresh_rankings()
        refreshed = self.get_session(session_id)
        return refreshed.task_results[task_result.task_id]

    def complete_session(self, session_id: str, *, require_all: bool = False) -> dict[str, Any]:
        """세션을 완료 처리하고 최종 점수와 순위를 반환한다."""

        session = self.get_session(session_id)
        task_scores = self._task_scores(session)
        total_score = calculate_total_score(task_scores, require_all=require_all)
        if total_score is None:
            raise ValueError("종합점수를 계산할 테스트 결과가 부족합니다.")
        session.total_score = total_score
        session.status = "completed"
        session.completed_at = utc_now_iso()
        self._write_session(session)
        self._upsert_participant_row(self._session_to_row(session))
        self.refresh_rankings()
        return self.build_participant_report(session_id)

    def build_participant_report(self, session_id: str) -> dict[str, Any]:
        """개인 결과 화면에서 사용할 표준 리포트를 만든다."""

        session = self.get_session(session_id)
        task_scores = self._task_scores(session)
        metrics: dict[str, Any] = {}
        for result in session.task_results.values():
            metrics.update(result.get("metrics") or {})
        rows = self.load_participant_rows()
        return {
            "participant_id": session.participant_id,
            "session_id": session.session_id,
            "task_scores": task_scores,
            "total_score": session.total_score,
            "rank": session.rank,
            "participant_count": sum(row.get("total_score") not in (None, "") for row in rows),
            "metrics": metrics,
            "status": session.status,
        }

    def get_leaderboard(self, limit: int | None = 10) -> list[dict[str, Any]]:
        """종합점수 순으로 정렬된 순위 목록을 반환한다."""

        rows = [row for row in self.load_participant_rows() if row.get("total_score") not in (None, "")]
        rows.sort(
            key=lambda row: (
                -float(row["total_score"]),
                *(-float(row.get(f"{task_id}_score") or -1) for task_id in ("task2", "task3", "task4", "task1")),
                row["started_at"],
            )
        )
        leaderboard = [
            {
                "rank": index,
                "participant_id": row["participant_id"],
                "session_id": row["session_id"],
                "total_score": float(row["total_score"]),
            }
            for index, row in enumerate(rows, start=1)
        ]
        return leaderboard if limit is None else leaderboard[:limit]

    def get_group_analysis(self) -> dict[str, Any]:
        """완료된 전체 세션의 인지과학 조건 효과와 점수 통계를 반환한다."""

        from analysis.statistics import describe_scores, summarize_effects

        reports: list[dict[str, Any]] = []
        for path in sorted(self.sessions_dir.glob("*.json")):
            try:
                session = ParticipantSession.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            if session.task_results:
                reports.append(self.build_participant_report(session.session_id))

        frame = describe_scores_from_rows(self.load_participant_rows(), describe_scores)
        return {
            "participant_count": len(reports),
            "effects": summarize_effects(reports),
            "score_summary": frame,
        }

    def refresh_rankings(self) -> None:
        """현재 점수를 기준으로 참가자 CSV와 세션 JSON의 순위를 갱신한다."""

        rows = self.load_participant_rows()
        leaderboard = self.get_leaderboard(limit=None)
        rank_by_session = {item["session_id"]: item["rank"] for item in leaderboard}
        for row in rows:
            row["rank"] = rank_by_session.get(row["session_id"], "")
            path = self._session_path(row["session_id"])
            if path.exists():
                session = ParticipantSession.from_mapping(json.loads(path.read_text(encoding="utf-8")))
                session.rank = rank_by_session.get(session.session_id)
                self._write_session(session)
        self._write_participant_rows(rows)

    def load_participant_rows(self) -> list[dict[str, Any]]:
        """참가자 요약 CSV를 딕셔너리 목록으로 읽는다."""

        if not self.participants_csv.exists():
            return []
        with self.participants_csv.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _session_path(self, session_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", str(session_id)):
            raise ValueError("올바르지 않은 session_id입니다.")
        return self.sessions_dir / f"{session_id}.json"

    def _write_session(self, session: ParticipantSession) -> None:
        path = self._session_path(session.session_id)
        self._atomic_text_write(path, json.dumps(session.to_dict(), ensure_ascii=False, indent=2))

    def _write_trials(self, session: ParticipantSession, result: TaskResult) -> None:
        path = self.trials_dir / f"{session.session_id}_{result.task_id}.csv"
        trials = result.trials
        if not trials:
            return
        keys = sorted({key for trial in trials for key in trial})
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8-sig", newline="", delete=False, dir=path.parent
        ) as file:
            writer = csv.DictWriter(file, fieldnames=["participant_id", "session_id", "task_id", *keys])
            writer.writeheader()
            for trial in trials:
                row = {key: self._csv_value(value) for key, value in trial.items()}
                writer.writerow(
                    {
                        "participant_id": session.participant_id,
                        "session_id": session.session_id,
                        "task_id": result.task_id,
                        **row,
                    }
                )
            temp_path = Path(file.name)
        temp_path.replace(path)

    def _session_to_row(self, session: ParticipantSession) -> dict[str, Any]:
        scores = self._task_scores(session)
        return {
            "participant_id": session.participant_id,
            "session_id": session.session_id,
            "started_at": session.started_at,
            "completed_at": session.completed_at or "",
            "status": session.status,
            **{f"{task_id}_score": scores.get(task_id) if scores.get(task_id) is not None else "" for task_id in TASK_IDS},
            "total_score": session.total_score if session.total_score is not None else "",
            "rank": session.rank if session.rank is not None else "",
        }

    @staticmethod
    def _task_scores(session: ParticipantSession) -> dict[str, float | None]:
        return {
            task_id: (
                float(session.task_results[task_id]["score"])
                if task_id in session.task_results and session.task_results[task_id].get("score") is not None
                else None
            )
            for task_id in TASK_IDS
        }

    def _upsert_participant_row(self, new_row: dict[str, Any]) -> None:
        rows = self.load_participant_rows()
        for index, row in enumerate(rows):
            if row["session_id"] == new_row["session_id"]:
                rows[index] = new_row
                break
        else:
            rows.append(new_row)
        self._write_participant_rows(rows)

    def _write_participant_rows(self, rows: list[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8-sig", newline="", delete=False, dir=self.data_dir
        ) as file:
            writer = csv.DictWriter(file, fieldnames=PARTICIPANT_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            temp_path = Path(file.name)
        temp_path.replace(self.participants_csv)

    @staticmethod
    def _csv_value(value: Any) -> Any:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        return value

    @staticmethod
    def _atomic_text_write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=path.parent
        ) as file:
            file.write(text)
            temp_path = Path(file.name)
        temp_path.replace(path)


_default_manager: DataManager | None = None


def get_data_manager() -> DataManager:
    """UI와 main에서 공유할 기본 DataManager 인스턴스를 반환한다."""

    global _default_manager
    if _default_manager is None:
        _default_manager = DataManager()
    return _default_manager


def is_participant_id_available(participant_id: str) -> bool:
    """기본 저장소에서 참가자 ID 사용 가능 여부를 확인한다."""

    return get_data_manager().is_participant_id_available(participant_id)


def create_participant_session(participant_id: str) -> dict[str, Any]:
    """기본 저장소에 새 참가자 세션을 만든다."""

    return get_data_manager().create_participant_session(participant_id)


def describe_scores_from_rows(rows: list[dict[str, Any]], describe_function) -> dict[str, Any]:
    """CSV 행을 점수 요약 딕셔너리로 변환한다."""

    import pandas as pd

    description = describe_function(pd.DataFrame(rows))
    if description.empty:
        return {}
    return {
        index: {
            key: (None if pd.isna(value) else float(value))
            for key, value in values.items()
        }
        for index, values in description.to_dict(orient="index").items()
    }

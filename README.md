# MODI Brain Lab

MODI 센서를 활용한 체험형 인지 능력 측정 및 집단 데이터 분석 시스템입니다.

## 오늘 구현된 범위

- TASK 1 반응속도와 입력 방식 테스트
- TASK 2 기억력과 감각 통합 테스트
- 명세서의 고정 시행 순서 반영
- TASK 1 조기 반응, 예측 반응, 지연 반응 판정
- TASK 2 참가자 ID 기반 색상 순서 생성, 3연속 색상 방지
- 참가자별 CSV 저장
- 조건별 점수 요약
- MODI 연결 전 검증을 위한 키보드 입력 대체

## 실행

```powershell
python -m pip install -r requirements.txt
python main.py --task task1 --participant-id P001
python main.py --task task2 --participant-id P001
```

## TASK 1 키보드 대체 입력

- 버튼 조건: 스페이스바
- 자이로 조건: 아래 방향키 또는 `G`
- 종료: `ESC`

실제 MODI 연동 시에는 `modi_io.py`에서 센서 값을 읽고 `tasks/task1_reaction.py`의 입력 판정 부분을 교체합니다.

## TASK 2 키보드 대체 입력

- 빨강: `1`
- 초록: `2`
- 파랑: `3`
- 노랑: `4`
- 다이얼 대체: 좌우 방향키
- 버튼 확정 대체: 스페이스바 또는 엔터

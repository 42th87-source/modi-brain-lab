# MODI를 활용한 체험형 인지 능력 측정 및 집단 데이터 분석 시스템

## 프로젝트 소개

MODI 센서를 활용해 참가자가 네 가지 인지 능력 테스트를 직접 수행하는 체험형 부스 프로젝트입니다. 각 참가자의 측정 데이터를 실시간으로 저장·분석하고, 개인 결과와 전체 참가자의 집단 결과를 함께 제공합니다.

수집된 데이터는 감각 통합, 체화된 인지, 감각 모순 등 인지과학적 효과를 이해하기 쉬운 시각 자료로 표현하는 데 활용합니다.

## 프로젝트 목표

- MODI 센서를 이용한 네 가지 체험형 인지 능력 테스트 구성
- 참가자별 측정 데이터의 실시간 수집 및 안전한 저장
- 개인별 점수와 특성에 대한 즉각적인 피드백 제공
- 누적된 집단 데이터를 이용한 통계 분석 및 시각화
- 인지과학 개념을 직접 경험하고 탐구할 수 있는 교육 환경 조성

## 개발 환경

- Python 3.11
- pymodi-plus
- pygame
- pandas
- matplotlib
- numpy
- Git / GitHub

## 설치 방법

1. 저장소를 복제하고 프로젝트 폴더로 이동합니다.

   ```bash
   git clone https://github.com/<사용자명>/modi-brain-lab.git
   cd modi-brain-lab
   ```

2. Python 3.11 가상 환경을 생성하고 활성화합니다.

   Windows PowerShell:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS 또는 Linux:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. 필요한 패키지를 설치합니다.

   ```bash
   python -m pip install -r requirements.txt
   ```

## 프로젝트 폴더 구조

```text
modi-brain-lab/
├── main.py                 # 애플리케이션 진입점
├── modi_io.py              # MODI 센서 입출력
├── task_manager.py         # 테스트 실행 및 상태 관리
├── scoring.py              # 테스트 점수 계산
├── dashboard.py            # 분석 결과 대시보드
├── data_manager.py         # 참가자 데이터 관리
├── config.py               # 공통 설정
├── tasks/
│   ├── task1_reaction.py   # 반응 속도 테스트
│   ├── task2_memory.py     # 기억력 테스트
│   ├── task3_attention.py  # 주의력 테스트
│   └── task4_coordination.py # 감각·운동 협응 테스트
├── ui/
│   ├── screens.py          # 화면 구성
│   └── widgets.py          # 공통 UI 위젯
├── analysis/
│   ├── statistics.py       # 통계 분석
│   ├── visualization.py    # 데이터 시각화
│   └── participant.py      # 참가자별 분석
├── assets/                 # 이미지, 글꼴, 소리 등 정적 자원
├── data/                   # 실행 중 생성되는 측정 데이터
├── requirements.txt
├── README.md
└── .gitignore
```

## 팀 개발 규칙

- 기능 단위로 브랜치를 만들고 작업합니다. 예: `feature/reaction-test`
- `main` 브랜치에는 검토가 끝난 코드만 병합합니다.
- 커밋은 하나의 목적만 담고, 메시지에 변경 이유가 드러나도록 작성합니다.
- Python 코드는 PEP 8을 따르고 함수와 클래스의 역할을 명확하게 문서화합니다.
- 새로운 패키지를 추가하면 `requirements.txt`도 함께 갱신합니다.
- 참가자 원본 데이터와 개인정보는 Git에 커밋하지 않습니다.
- 병합 전 담당 기능을 실행해 오류가 없는지 확인하고 동료 검토를 진행합니다.

## 앞으로의 개발 로드맵

1. **기반 설계** — MODI 장치 구성, 데이터 형식, 테스트 공통 흐름 확정
2. **센서 연동** — pymodi-plus 기반 장치 연결 및 입력 검증
3. **인지 테스트 구현** — 반응 속도, 기억력, 주의력, 감각·운동 협응 테스트 개발
4. **데이터 관리** — 참가자 식별, 실시간 저장, 오류 복구 기능 개발
5. **점수 및 분석** — 개인 점수 산출과 집단 통계 분석 기준 수립
6. **시각화 및 UI** — 체험 화면, 개인 결과, 집단 대시보드 구현
7. **통합 시험** — 실제 부스 환경에서 사용성, 안정성, 측정 타당성 검증
8. **운영 준비** — 설치 안내, 운영 매뉴얼, 개인정보 보호 절차 정리

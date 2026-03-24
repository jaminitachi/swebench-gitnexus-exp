# SWE-bench GitNexus A/B/C Experiment

Claude Sonnet 4.6 + GitNexus MCP로 SWE-bench Django 50문제를 3가지 조건으로 비교하는 실험.

## 실험 조건

| 조건 | 이름 | 설명 |
|------|------|------|
| **A** | `baseline` | mini-swe-agent 기본. GitNexus 없음. bash 도구만. |
| **B** | `gitnexus-context` | system prompt에 GitNexus CLI 사용법 상세 가이드 + gitnexus CLI 사용 가능 + 기본 bash 도구도 사용 가능. |
| **C** | `gitnexus-forced` | system prompt에서 grep/find/cat 사용 금지. 코드 탐색은 반드시 gitnexus CLI만 사용. 파일 수정은 bash 허용. |

## 공통 조건

- 모델: `anthropic/claude-sonnet-4-6`
- 데이터: SWE-bench Lite Django 50문제
- 프레임워크: mini-swe-agent v2.2.7
- 환경: Docker (swebench 기본 이미지)
- 평가: SWE-bench harness (테스트 통과율)

## 설치 (맥미니)

```bash
# 1. Clone
git clone https://github.com/limdehan/swebench-gitnexus-exp.git
cd swebench-gitnexus-exp

# 2. Python 가상환경
python3.11 -m venv venv
source venv/bin/activate

# 3. 의존성
pip install -r requirements.txt

# 4. GitNexus 설치 (Node.js 필요)
npm install -g gitnexus

# 5. 환경변수
cp .env.example .env
# ANTHROPIC_API_KEY 설정

# 6. Django 레포 인덱싱 (한번만)
./scripts/setup_gitnexus_index.sh

# 7. 데이터셋 준비
python scripts/prepare_dataset.py

# 8. 실험 실행
python scripts/run_experiment.py --condition all --workers 3
```

## 디렉토리 구조

```
swebench-gitnexus-exp/
├── configs/
│   ├── condition_a.yaml          # Condition A: baseline
│   ├── condition_b.yaml          # Condition B: gitnexus context
│   └── condition_c.yaml          # Condition C: gitnexus forced
├── prompts/
│   ├── system_baseline.jinja     # A: 기본 시스템 프롬프트
│   ├── system_gitnexus.jinja     # B: GitNexus 가이드 포함
│   └── system_forced.jinja       # C: GitNexus 강제 사용
├── scripts/
│   ├── prepare_dataset.py        # 50문제 데이터셋 준비
│   ├── run_experiment.py         # 실험 실행기
│   ├── evaluate.py               # SWE-bench 평가
│   ├── compare_results.py        # A/B/C 결과 비교
│   └── setup_gitnexus_index.sh   # Django 레포 GitNexus 인덱싱
├── data/                         # 데이터셋 (git-ignored)
├── results/                      # 실험 결과 (git-ignored)
├── evaluation/                   # 평가 리포트
├── requirements.txt
├── .env.example
└── README.md
```

## 결과 비교

```bash
# 평가 실행
python scripts/evaluate.py --condition all

# 비교 리포트 생성
python scripts/compare_results.py
```

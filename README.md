# SWE-bench GitNexus A/B/C Experiment

Claude Code CLI (OAuth) + GitNexus로 SWE-bench Django 50문제를 3가지 조건으로 비교.

**API key 사용 안 함** — Claude Code OAuth 인증으로 실행.

## 실험 조건

| 조건 | 이름 | 설명 |
|------|------|------|
| **A** | `baseline` | GitNexus 없음. Claude Code 기본 도구만. |
| **B** | `gitnexus-context` | CLAUDE.md에 GitNexus 사용법 가이드 + gitnexus CLI 사용 가능 + 기본 도구도 사용 가능. |
| **C** | `gitnexus-forced` | grep/find/cat 금지. 코드 탐색은 gitnexus CLI만. 수정은 허용. |

## 아키텍처

```
[사전 준비]
  50개 커밋별 gitnexus analyze → indexes/{commit_hash}/.gitnexus/

[실험 실행]
  for each task:
    1. Django repo clone + 특정 커밋 checkout
    2. .gitnexus/ 인덱스 복사 (조건 B/C만)
    3. 조건별 CLAUDE.md 작성
    4. claude -p "이슈 설명" --model sonnet --permission-mode bypassPermissions
    5. git diff → 패치 수집
    6. 정리

[평가]
  SWE-bench harness로 패치 적용 + 테스트 실행 → pass/fail
```

## 설치 (맥미니)

```bash
# 1. 기본 도구
brew install git node python@3.11
npm install -g @anthropic-ai/claude-code gitnexus

# 2. Claude Code 로그인 (OAuth — 한번만)
claude
# → 로그인 프롬프트 따라가기

# 3. 레포 클론
git clone https://github.com/jaminitachi/swebench-gitnexus-exp.git
cd swebench-gitnexus-exp

# 4. Python 환경
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 데이터셋 준비
python scripts/prepare_dataset.py

# 6. GitNexus 사전 인덱싱 (50 커밋, 시간 걸림)
python scripts/preindex_gitnexus.py

# 7. 실험 실행
python scripts/run_claude.py --condition a --limit 5  # 테스트 5개
python scripts/run_claude.py --condition all           # 전체 실행
```

## 스크립트

| 스크립트 | 역할 |
|----------|------|
| `scripts/prepare_dataset.py` | SWE-bench Lite에서 Django 50문제 추출 |
| `scripts/preindex_gitnexus.py` | 50 커밋별 GitNexus 인덱스 사전 빌드 |
| `scripts/run_claude.py` | **메인 실험 러너** — claude -p로 각 조건 실행 |
| `scripts/compare_results.py` | A/B/C 결과 비교 리포트 생성 |

## 디렉토리

```
swebench-gitnexus-exp/
├── configs/              # mini-swe-agent YAML (레거시, 참고용)
├── prompts/              # 조건별 시스템 프롬프트 (CLAUDE.md로 주입)
│   ├── system_baseline.jinja     # A: 기본
│   ├── system_gitnexus.jinja     # B: GitNexus 가이드
│   └── system_forced.jinja       # C: GitNexus 강제
├── scripts/              # 실행 스크립트
├── indexes/              # 커밋별 .gitnexus/ (git-ignored)
├── data/                 # 데이터셋 (git-ignored)
├── results/              # 실험 결과 (git-ignored)
├── logs/                 # 로그 (git-ignored)
└── evaluation/           # 비교 리포트
```

## 비용

- API key 미사용 (OAuth)
- Claude Code Pro/Max 구독으로 실행
- 50문제 × 3조건 = 150 실행

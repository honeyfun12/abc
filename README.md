# 개인 비서 (Personal Assistant Secretary)

세훈 님 전담 비서. 텔레그램으로 하루에 4–6번 짧고 따뜻하게 chime in 합니다. 음성 메시지로도 읽어줍니다.

## 설계 원칙

행동신경과학과 비서학 두 축으로 설계했습니다. 자세한 출처와 적용 방식은 `src/prompts.py` 상단 docstring을 보세요. 짧게:

- **가변 보상 스케줄**: 도파민은 *예측 불가*한 보상에 가장 강하게 반응합니다. 매일 같은 시간 아닌, window 안에서 랜덤하게 발화. (`src/scheduler.py`)
- **인지부하 제한**: 한 메시지에 행동 항목 최대 3개. 보통 1~2개.
- **implementation intentions**: "할 일 X" 보다 "점심 먹고 자리 앉자마자 X" 식의 trigger→action 구조.
- **circadian 인식**: 아침=계획, 점심 후=가벼운 체크(코르티솔 dip), 저녁=회고 + 감사.
- **양방향 기억**: 텔레그램에 친 모든 채팅(텍스트/음성)은 DB에 저장되고 다음 호출의 컨텍스트로 들어갑니다. 비서가 "들었던 것"을 기억합니다.
- **장기 목표 = 행복**: "취직"이 아니라 일·건강·관계·배움·"오늘 살 만함" 다섯 축. `config.yaml`에서 편집.

## 구조

```
src/
├── main.py            # 엔트리포인트
├── prompts.py         # 시스템 프롬프트 (신경과학 + 비서학)
├── assistant.py       # Claude Opus 4.7 호출 + 컨텍스트 조립 + 프롬프트 캐싱
├── telegram_bot.py    # 텔레그램 양방향 I/O + Whisper 음성 전사
├── tts.py             # OpenAI TTS → ogg/opus (텔레그램 voice note)
├── scheduler.py       # APScheduler — slot + jitter
├── memory.py          # SQLite: 대화 기록, 비서의 self-note, 할 일
└── sources/
    ├── google_calendar.py
    ├── google_drive.py
    └── local_notes.py
```

## 셋업

### 1. Python 환경

```bash
cd /home/user/abc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`ffmpeg`이 시스템에 있어야 음성이 텔레그램 voice note 포맷으로 변환됩니다.
```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

### 2. 텔레그램 봇 만들기

1. 텔레그램에서 [@BotFather](https://t.me/BotFather) → `/newbot` → 이름 짓고 토큰 받기
2. 새 봇한테 아무 메시지 보내기
3. `https://api.telegram.org/bot<TOKEN>/getUpdates` 열어서 `chat.id` 찾기

### 3. 환경 변수

```bash
cp .env.example .env
# .env 편집:
#   ANTHROPIC_API_KEY=...
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
#   OPENAI_API_KEY=...   (음성 + Whisper 음성 입력용. 없으면 텍스트만.)
```

### 4. (선택) 구글 캘린더 / 드라이브

1. [Google Cloud Console](https://console.cloud.google.com/) → 프로젝트 만들기 → APIs & Services에서 Calendar API, Drive API 활성화
2. OAuth client (Desktop) 만들고 `client_secret.json`을 `/home/user/abc/`에 저장
3. `config.yaml`에서 `google_calendar.enabled: true` / `google_drive.enabled: true`
4. 한 번만 인증:
   ```bash
   python scripts/init_google_auth.py
   ```
   브라우저가 열려서 권한 승인 → `.google_token.json` 자동 저장

### 5. 노트 폴더 (이전 클로드 채팅용)

`./notes/` 디렉토리에 텍스트/마크다운 파일을 넣으면 비서가 최근 편집된 5개를 컨텍스트로 읽습니다.

이전 클로드 채팅을 여기 export 해두면 비서가 "들어두는" 효과:
```bash
mkdir -p notes
echo "오늘 클로드와 대화한 내용..." > notes/2026-05-26.md
```

### 6. 실행

먼저 단발 테스트 (텔레그램 안 거치고 메시지만 생성):
```bash
python scripts/test_one_message.py morning_brief
python scripts/test_one_message.py evening_reflection
```

좋으면 풀가동:
```bash
python -m src.main
```

처음 시작하면 5초 안에 오늘 일정을 스케줄링하고, 가장 가까운 window의 메시지부터 발화합니다.

## 사용법

텔레그램에서:
- 그냥 **아무 말이나** 치면 됩니다. 비서가 듣고 답하고 기억합니다.
- 음성 메시지도 보내면 됩니다 (Whisper로 전사).
- `/start` — 봇 소개
- `/brief` — 아침 브리프 강제 호출
- `/pulse` — 지금 컨디션 체크
- `/reflect` — 저녁 회고
- `/todos` — 열린 할 일 목록

## 프롬프트 튜닝

비서 톤이 안 맞으면 `src/prompts.py`의 `stable_system_prompt()` 안에서 톤·길이·금지어를 조정하세요. 시스템 프롬프트는 캐시되어서 (Anthropic prompt caching) 톤 실험 비용이 낮습니다.

장기 목표·가치관 변경은 `config.yaml`의 `A.long_term_goals` / `A.values` — 재시작하면 반영.

## 비용 메모

- Claude Opus 4.7 + adaptive thinking + 캐싱: 메시지 1개당 약 ¢2–5 (5분 캐시 윈도우 안에서 재호출하면 캐시 히트로 더 저렴).
- OpenAI TTS (`gpt-4o-mini-tts`): 1000자당 약 ¢0.6.
- Whisper 음성 전사: 분당 약 ¢0.6.

하루 6번 + 응답 몇 개 = 월 $5–15 수준.

## 안전·프라이버시

- SQLite DB는 로컬 파일. 어디로도 안 보냄.
- `.env`, `client_secret.json`, `.google_token.json`, `*.db`는 `.gitignore` 처리.
- 텔레그램 봇 토큰이 유출되면 BotFather → `/revoke`.

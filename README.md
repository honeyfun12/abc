# 개인 비서 (Personal Assistant Secretary)

세훈 님 전담 비서. 텔레그램으로 하루 5번 짧고 따뜻하게 chime in 합니다. 음성 메시지로도 읽어줍니다.

**비용 0** — Claude는 Max 20x 구독으로, TTS는 Microsoft Edge(무료) 사용. 어떤 추가 API 과금도 없음.

## 설계 원칙

행동신경과학과 비서학 두 축. 자세한 내용은 `src/prompts.py` 상단 docstring.

- **가변 보상 스케줄**: 도파민은 예측 불가한 보상에 가장 강하게 반응. 매일 같은 시간 아닌, window 안에서 랜덤하게 발화.
- **인지부하 제한**: 한 메시지에 행동 항목 최대 3개. 보통 1~2개.
- **implementation intentions**: "할 일 X" 보다 "점심 먹고 자리 앉자마자 X" 식.
- **circadian 인식**: 기상 직후=계획, 점심 후=가벼운 체크, 저녁=회고.
- **양방향 기억**: 텔레그램에서 친 모든 채팅이 DB에 저장되고 다음 호출의 컨텍스트로 들어감.
- **장기 목표 = 행복**: 일·건강·관계·배움·"오늘 살 만함" 다섯 축.

## 하루 스케줄 (기상 10시 기준)

| Slot | Window | 종류 |
|---|---|---|
| 아침 브리프 | 10:05~10:45 | morning_brief |
| 오전 집중 | 11:30~12:30 | focus_nudge |
| 점심 후 펄스 | 14:00~15:00 | pulse_check |
| 오후 마무리 | 16:30~18:00 | focus_nudge |
| 저녁 회고 | 22:00~23:30 | evening_reflection |

각 window 안에서 매일 다른 시각에 발화. 슬롯 5개 + (옵션) 랜덤 추가 nudge.

## 셋업

### 1. Claude Code CLI (Max 구독 사용)

```bash
# 이미 설치돼 있을 가능성 높음
which claude

# 없으면: https://claude.ai/code 에서 설치
# 그리고 Max 계정으로 로그인:
claude /login
```

이제 `claude-agent-sdk`가 이 CLI를 통해 Claude를 호출합니다 → **Max 구독 한도에서 차감, API 과금 없음**.

### 2. Python 환경

```bash
cd /home/user/abc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. ffmpeg (음성 변환용)

```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

### 4. 텔레그램 봇

1. [@BotFather](https://t.me/BotFather) → `/newbot` → 이름 짓고 토큰 받기
2. 새 봇한테 아무 메시지 보내기
3. `https://api.telegram.org/bot<TOKEN>/getUpdates` 에서 `chat.id` 확인

### 5. 환경 변수

```bash
cp .env.example .env
# .env 편집:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
# (ANTHROPIC_API_KEY 같은 거 필요 없음 — claude CLI가 알아서 함)
```

### 6. (선택) 구글 캘린더 / 드라이브

1. [Google Cloud Console](https://console.cloud.google.com/) → Calendar API, Drive API 활성화
2. OAuth client (Desktop) → `client_secret.json` 을 `/home/user/abc/` 에 저장
3. `config.yaml` 에서 `google_calendar.enabled: true` / `google_drive.enabled: true`
4. 한 번만 인증:
   ```bash
   python scripts/init_google_auth.py
   ```

### 7. 노트 폴더 (이전 클로드 채팅 등)

`./notes/` 에 텍스트/마크다운 파일을 넣으면 비서가 최근 5개를 컨텍스트로 읽습니다.

```bash
mkdir -p notes
echo "오늘 클로드와 대화한 내용..." > notes/2026-05-26.md
```

### 8. 실행

먼저 한 번 테스트 (텔레그램 안 거치고):
```bash
python scripts/test_one_message.py morning_brief
python scripts/test_one_message.py evening_reflection
```

좋으면 풀가동:
```bash
python -m src.main
```

## 사용법 (텔레그램)

- 그냥 **아무 말이나** 치면 됩니다. 비서가 듣고 답하고 기억합니다.
- 음성 메시지는 기록만 됩니다 (전사는 유료라 비활성화). 답이 필요하면 텍스트로.
- `/brief` `/pulse` `/reflect` `/todos` — 강제 호출 / 할 일 확인

## 프롬프트 튜닝

비서 톤은 `src/prompts.py` 의 `stable_system_prompt()` 에서 조정.
장기 목표·기상 시각은 `config.yaml` 의 `A.long_term_goals` / `A.wake_time`.

## TTS 음성 변경

`config.yaml` 의 `tts.voice` 를 바꾸면 됨:

| Voice ID | 설명 |
|---|---|
| `ko-KR-SunHiNeural` | 따뜻하고 차분한 여성 (기본) |
| `ko-KR-SeoHyeonNeural` | 차분한 여성 |
| `ko-KR-JiMinNeural` | 밝은 여성 |
| `ko-KR-InJoonNeural` | 부드러운 남성 |
| `ko-KR-BongJinNeural` | 활기찬 남성 |
| `ko-KR-GookMinNeural` | 신뢰감 있는 남성 |

전체 목록: `edge-tts --list-voices | grep ko-KR`

## 안전·프라이버시

- SQLite DB는 로컬 파일. 외부 전송 X.
- `.env`, `client_secret.json`, `.google_token.json`, `*.db` 는 `.gitignore` 처리.
- 텔레그램 봇 토큰 유출 시 BotFather → `/revoke`.

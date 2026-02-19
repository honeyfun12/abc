# IBD Voice Coach (Android)

데일리 3세션(아침/오후/저녁) 기반으로 질문 1개 → 답변 전사 입력 → 채점/피드백/리테이크를 진행하는 Android 앱입니다.

## 구현된 기능
- 세션 1/2/3 선택 및 시작 문구 자동 생성
- 질문 뱅크 로테이션(IBD Core, Valuation, BIWS Tech, UK IBD, ER/PE 확장)
- 난이도 자동 조절 로직
  - 2일 연속 고득점(7+) → HARD
  - 2일 연속 저득점(5-) → EASY
- 답변 시간(3~7분), 질문 카테고리(ER/PE 포함 여부) 설정
- Google AI Studio(Gemini) API를 이용한 루브릭 기반 피드백 생성

## API 키 설정
`~/.gradle/gradle.properties` 또는 프로젝트 `gradle.properties`에 아래를 추가하세요.

```properties
GOOGLE_AI_API_KEY=YOUR_KEY
```

## 실행
```bash
./gradlew :app:assembleDebug
```

## 향후 확장(권장)
- WorkManager + AlarmManager 기반 09:30/14:30/20:30 알림 스케줄링
- Android SpeechRecognizer 내장으로 전사 자동화
- 점수 이력 저장(Room) + 난이도 자동 반영 고도화

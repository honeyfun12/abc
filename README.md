# 색반전 타이머 (Inversion Timer)

유튜브 또는 인스타그램을 실행하면

1. **10초 동안 사용을 차단**하는 카운트다운 오버레이를 띄우고,
2. 잠금이 해제되면 **시스템 색반전**을 켜고,
3. 사용 시작 후 **5분이 지나면 자동으로 홈 화면으로 이동**시켜 사용을 종료합니다.

## 설치 & 권한

Android Studio에서 열고 디바이스로 빌드합니다. 처음 실행 시 아래 권한을 부여하세요.

1. **다른 앱 위에 표시** (`SYSTEM_ALERT_WINDOW`) — 카운트다운 오버레이용
2. **접근성 서비스** (`AppMonitorService`) — 유튜브/인스타그램 실행 감지용
3. **시스템 색반전** (`WRITE_SECURE_SETTINGS`) — 색반전 토글용. 보안상 일반 설치로는 부여할 수 없으며, ADB로 직접 부여해야 합니다.

```sh
adb shell pm grant com.example.inversiontimer android.permission.WRITE_SECURE_SETTINGS
```

이 권한이 없으면 색반전 대신 화면 위에 어둡게 처리되는 폴백 오버레이가 표시됩니다.

## 동작 흐름

```
유튜브/인스타 실행 감지
   ↓
10초 카운트다운 오버레이 표시 (사용 차단)
   ↓
오버레이 제거 + 색반전 ON
   ↓
5분 경과
   ↓
색반전 OFF + 홈 화면으로 이동 (사용 종료)
```

도중에 다른 앱으로 이동하면 세션이 즉시 종료되고 다시 진입하면 처음부터 다시 시작합니다.

## 대상 패키지

- `com.google.android.youtube`
- `com.instagram.android`

`app/src/main/res/xml/accessibility_service_config.xml`와 `AppMonitorService.kt` 양쪽에서 동시에 수정하면 다른 앱도 추가할 수 있습니다.

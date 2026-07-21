# 치지직 방송 알리미

팔로우한 치지직 스트리머가 방송을 켜면 Windows 토스트 알림을 보내주는 프로그램.

## 설치

```
pip install -r requirements.txt
```

## 실행

- `실행.bat` — 콘솔 창 없이 실행 (권장)
- 또는 `python app.py`

## 사용법

1. 상단 검색창에 스트리머 이름 입력 → 검색
2. 결과에서 더블클릭(또는 선택 후 추가 버튼)으로 알림 목록에 추가
3. 창을 닫으면 트레이로 최소화되어 백그라운드에서 계속 감시
4. 방송이 켜지면 토스트 알림 발생 — 클릭하면 방송 페이지가 열림
5. 완전히 종료하려면 트레이 아이콘 우클릭 → 종료

## 알림 방식

기본은 **자체 팝업** — 화면 우하단에 스팀 친구 접속 알림처럼 슬라이드 인으로 떴다가
몇 초 뒤 사라진다. Windows 알림 설정과 무관하게 동작하며, 팝업 클릭 시 방송 페이지가 열림.
`config.json`에서 `use_windows_toast`를 `true`로 바꾸면 Windows 토스트 알림으로 전환
(이 경우 Windows 설정 → 시스템 → 알림이 켜져 있어야 함).

## 설정 (config.json — 자동 생성)

새로고침 주기, 팝업 유지시간, 알림 소리는 창 하단 "설정" 패널에서 바로 변경 가능.
알림 소리는 기본 알림음(내장 notify.wav) / 무음 / 원하는 WAV 파일 중 선택 (winsound 특성상 .wav만 지원 —
mp3는 [온라인 변환기](https://cloudconvert.com/mp3-to-wav) 등으로 변환해서 사용).

- `poll_interval_sec`: 확인 주기 (기본 30초, 10~600초)
- `notify_on_startup`: 프로그램 시작 시 이미 방송 중인 채널도 알림 (기본 false)
- `use_windows_toast`: true면 Windows 토스트, false면 자체 팝업 (기본 false)
- `popup_duration_sec`: 자체 팝업 표시 시간 (기본 8초, 2~60초)
- `sound_mode`: default(내장 notify.wav) / none(무음) / file(WAV 파일)
- `sound_file`: sound_mode가 file일 때 재생할 .wav 경로
- `channels`: 알림 받을 채널 목록 (GUI에서 관리)

## 로고

`logo.png`(트레이·알림), `logo.ico`(창 아이콘·바로가기)는 `python gen_logo.py`로 생성.
디자인을 바꾸고 싶으면 `gen_logo.py`를 수정 후 재실행하면 됨.
바로가기에 아이콘을 입히려면: 바로가기 우클릭 → 속성 → 아이콘 변경 → `logo.ico` 선택.

## 부팅 시 자동 시작

`Win+R` → `shell:startup` → 열린 폴더에 `실행.bat`의 바로가기를 넣으면 됨.

## 사용 API (비공식)

- 검색: `GET /service/v1/search/channels?keyword=…&withFirstChannelContent=true`
- 방송 여부: `GET /service/v1/channels/{channelId}` 의 `openLive`
- 방송 제목/카테고리(부가): `GET /polling/v2/channels/{channelId}/live-status`

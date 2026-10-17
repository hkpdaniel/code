# 🎙️ 녹음 받아쓰기 & 핵심 정리

녹음 파일을 넣으면 **자동으로 텍스트로 변환**하고, 그 안에서 **중요한 점을 뽑아 알려주는** 앱입니다.

## 기능
- 📁 녹음 파일 업로드 (mp3, m4a, wav, ogg, webm, mp4, aac, flac …) 또는 🎤 브라우저에서 바로 녹음
- 📝 음성 → 텍스트 자동 변환 ([faster-whisper](https://github.com/SYSTRAN/faster-whisper), 내 컴퓨터에서 동작)
  - 구간별 시간 표시 `[03:12] …`, 한국어/영어/자동 감지
- ⭐ 중요한 점 정리
  - 한 줄 요약 · 핵심 포인트 · ✅ 해야 할 일/마감 · 🔑 키워드
  - `ANTHROPIC_API_KEY`가 있으면 **Claude**가 정리 (더 정확함)
  - 키가 없으면 인터넷 없이 **로컬 방식**(키워드 빈도 + "중요/시험/마감" 같은 강조 단어)으로 정리
- 💾 텍스트(.txt)와 정리본(.md) 다운로드

## 설치 & 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```
브라우저가 열리면 파일을 올리기만 하면 됩니다.

- 처음 변환할 때 음성 인식 모델을 자동으로 내려받습니다 (small 약 500MB).
- 왼쪽 설정에서 모델 크기를 고를 수 있습니다. `tiny`/`base`는 빠르고, `medium`/`large-v3`는 느리지만 정확합니다.

### (선택) Claude로 더 똑똑하게 정리하기
```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-..."
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```
키를 설정하고 앱을 실행하면 사이드바의 "Claude로 핵심 정리" 스위치가 켜집니다.

## 파일 구성
| 파일 | 역할 |
| --- | --- |
| `app.py` | Streamlit 화면 (업로드, 결과 표시, 다운로드) |
| `transcriber.py` | 음성 → 텍스트 변환 |
| `highlights.py` | 중요한 점 추출 (Claude / 로컬) |
| `test_highlights.py` | 테스트 (`python -m pytest`) |

"""녹음 → 텍스트 변환 + 중요한 점 알려주는 앱.

실행:  streamlit run app.py
"""
import os
import tempfile

import streamlit as st

from highlights import extract_highlights
from transcriber import format_time, transcribe

st.set_page_config(page_title="녹음 받아쓰기", page_icon="🎙️", layout="wide")
st.title("🎙️ 녹음 받아쓰기 & 핵심 정리")
st.caption("녹음 파일을 올리면 자동으로 텍스트로 바꾸고, 중요한 점을 뽑아 알려줍니다.")

# ------------------------------------------------------------------ 설정
with st.sidebar:
    st.header("⚙️ 설정")
    model_size = st.selectbox(
        "음성 인식 모델",
        ["tiny", "base", "small", "medium", "large-v3"],
        index=2,
        help="클수록 정확하지만 느립니다. 처음 사용할 때 모델을 내려받습니다.",
    )
    lang_label = st.selectbox("언어", ["한국어", "영어", "자동 감지"])
    language = {"한국어": "ko", "영어": "en", "자동 감지": None}[lang_label]

    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    use_claude = st.toggle(
        "Claude로 핵심 정리 (더 정확함)",
        value=has_key,
        disabled=not has_key,
        help="ANTHROPIC_API_KEY 환경 변수를 설정하면 켤 수 있습니다. 꺼져 있으면 인터넷 없이 로컬 방식으로 정리합니다.",
    )
    show_time = st.checkbox("시간 표시", value=True)

# ------------------------------------------------------------------ 입력
tab_upload, tab_record = st.tabs(["📁 파일 올리기", "🎤 바로 녹음하기"])
with tab_upload:
    uploaded = st.file_uploader(
        "녹음 파일 (mp3, m4a, wav, ogg, webm, mp4 …)",
        type=["mp3", "m4a", "wav", "ogg", "webm", "mp4", "aac", "flac", "wma"],
    )
with tab_record:
    recorded = st.audio_input("마이크로 녹음")

audio = uploaded or recorded
if audio is None:
    st.info("👆 녹음 파일을 올리거나 바로 녹음해 주세요.")
    st.stop()

st.audio(audio)
audio_id = f"{getattr(audio, 'name', 'rec')}-{audio.size}-{model_size}-{language}"

# 같은 파일을 다시 변환하지 않도록 결과를 세션에 저장
if st.session_state.get("audio_id") != audio_id:
    suffix = os.path.splitext(getattr(audio, "name", "") or "rec.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(audio.getvalue())
        path = f.name
    bar = st.progress(0.0, text="텍스트로 변환하는 중…")
    try:
        segments, detected = transcribe(
            path, model_size, language,
            on_progress=lambda p: bar.progress(p, text=f"텍스트로 변환하는 중… {p:.0%}"),
        )
    except Exception as e:
        st.error(f"변환에 실패했습니다: {e}")
        st.stop()
    finally:
        os.unlink(path)
    bar.empty()
    st.session_state.update(audio_id=audio_id, segments=segments, detected=detected, highlights=None)

segments = st.session_state["segments"]
full_text = " ".join(s.text for s in segments)
if not full_text.strip():
    st.warning("음성을 인식하지 못했습니다. 다른 파일이나 더 큰 모델로 시도해 보세요.")
    st.stop()

# ------------------------------------------------------------------ 결과
col_text, col_points = st.columns([3, 2], gap="large")

with col_text:
    st.subheader("📝 변환된 텍스트")
    st.caption(f"감지된 언어: {st.session_state['detected']} · 구간 {len(segments)}개")
    if show_time:
        lines = [f"[{format_time(s.start)}] {s.text}" for s in segments]
    else:
        lines = [full_text]
    transcript = "\n".join(lines)
    st.text_area("전체 텍스트", transcript, height=480, label_visibility="collapsed")
    st.download_button("💾 텍스트 저장 (.txt)", transcript, file_name="transcript.txt")

with col_points:
    st.subheader("⭐ 중요한 점")
    if st.session_state.get("highlights") is None or st.button("🔄 다시 정리하기"):
        with st.spinner("중요한 점을 찾는 중…"):
            st.session_state["highlights"] = extract_highlights(full_text, use_claude)
    h = st.session_state["highlights"]

    st.markdown("**한 줄 요약**")
    st.info(h.summary)

    st.markdown("**핵심 포인트**")
    for i, p in enumerate(h.key_points, 1):
        st.markdown(f"{i}. {p}")

    if h.action_items:
        st.markdown("**✅ 해야 할 일 / 마감**")
        for a in h.action_items:
            st.markdown(f"- [ ] {a}")

    if h.keywords:
        st.markdown("**🔑 키워드**")
        st.markdown(" ".join(f"`{k}`" for k in h.keywords))

    st.caption("정리 방식: " + ("Claude AI" if h.source == "claude" else "로컬(키워드 빈도 기반)"))

    report = "\n".join(
        ["# 요약", h.summary, "", "# 핵심 포인트", *[f"- {p}" for p in h.key_points]]
        + (["", "# 해야 할 일", *[f"- [ ] {a}" for a in h.action_items]] if h.action_items else [])
        + ["", "# 전체 텍스트", transcript]
    )
    st.download_button("💾 정리본 저장 (.md)", report, file_name="notes.md")

import os
from datetime import datetime

import requests
import streamlit as st


APP_TITLE = "Gwittim"
DEFAULT_MODEL = "gpt-5.6-luna"


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state():
    defaults = {
        "segments": [],
        "summary": "대화가 쌓이면 요약이 갱신됩니다.",
        "last_translation": "영어 문장을 입력하면 한국어 자막처럼 표시됩니다.",
        "last_english": "원문 영어는 여기에 함께 표시됩니다.",
        "reply_suggestion": "추천 영어 답변이 여기에 표시됩니다.",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def secret_value(name, fallback=""):
    try:
        return st.secrets.get(name, fallback)
    except Exception:
        return os.getenv(name, fallback)


def get_settings():
    configured_key = secret_value("OPENAI_API_KEY", "")
    model = secret_value("OPENAI_MODEL", os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    reasoning_effort = secret_value(
        "OPENAI_REASONING_EFFORT", os.getenv("OPENAI_REASONING_EFFORT", "none")
    )

    with st.sidebar:
        st.markdown("### Session")
        st.caption("Streamlit Cloud에서는 Settings > Secrets에 API 키를 넣으면 됩니다.")
        entered_key = st.text_input(
            "OpenAI API key",
            value="",
            type="password",
            placeholder="sk-...",
            help="Secrets에 키가 없을 때만 임시로 입력하세요.",
        )
        selected_model = st.text_input("Model", value=model)
        selected_effort = st.selectbox(
            "Reasoning effort",
            options=["none", "low", "medium", "high", "xhigh", "max"],
            index=["none", "low", "medium", "high", "xhigh", "max"].index(
                reasoning_effort if reasoning_effort in ["none", "low", "medium", "high", "xhigh", "max"] else "none"
            ),
        )
        save_audio = st.toggle("Store raw audio", value=False, disabled=True)
        st.caption("현재 Streamlit 데모는 원본 오디오를 저장하지 않습니다.")

    return {
        "api_key": entered_key or configured_key,
        "key_from_secret": bool(configured_key),
        "model": selected_model.strip() or DEFAULT_MODEL,
        "reasoning_effort": selected_effort,
        "save_audio": save_audio,
    }


def call_openai(settings, instructions, input_text, max_output_tokens=360):
    if not settings["api_key"]:
        raise RuntimeError("OPENAI_API_KEY가 필요합니다. Streamlit Secrets 또는 사이드바에 입력해주세요.")

    payload = {
        "model": settings["model"],
        "instructions": instructions,
        "input": input_text,
        "store": False,
        "max_output_tokens": max_output_tokens,
    }

    if settings["reasoning_effort"] and settings["reasoning_effort"] != "none":
        payload["reasoning"] = {"effort": settings["reasoning_effort"]}

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )

    data = response.json() if response.content else {}
    if not response.ok:
        message = data.get("error", {}).get("message") or data.get("message") or response.text
        raise RuntimeError(message)

    if isinstance(data.get("output_text"), str):
        return data["output_text"].strip()

    parts = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def context_text(limit=8):
    recent = st.session_state.segments[-limit:]
    lines = []
    for item in recent:
        lines.append(f"EN: {item['english']}\nKO: {item['korean']}")
    return "\n\n".join(lines)


def translate(settings, english_text):
    instructions = (
        "You are Gwittim, a quiet realtime English-to-Korean conversation assistant. "
        "Translate live English speech into natural Korean subtitles. Return only Korean text. "
        "Keep names, product names, technical terms, dates, and numbers precise. "
        "If the sentence is fragmentary, translate the intended meaning briefly without adding facts."
    )
    input_text = "\n\n".join(
        part
        for part in [
            f"Recent context:\n{context_text()}" if st.session_state.segments else "",
            f"Current English utterance:\n{english_text}",
        ]
        if part
    )
    return call_openai(settings, instructions, input_text, max_output_tokens=220)


def summarize(settings):
    transcript = "\n".join(
        f"{idx + 1}. EN: {item['english']}\n   KO: {item['korean']}"
        for idx, item in enumerate(st.session_state.segments[-24:])
    )
    instructions = (
        "You are Gwittim, a realtime meeting brief assistant. Summarize the current "
        "conversation in Korean for a user who is listening live. Keep it short, "
        "concrete, and useful. Use compact bullets. Include decisions and action items only if present."
    )
    return call_openai(settings, instructions, transcript, max_output_tokens=380)


def compose_reply(settings, korean_draft, mode):
    instructions = (
        "You are Gwittim, helping a Korean speaker respond naturally in an English conversation. "
        "Convert the user's Korean draft into concise, spoken English. Match the requested response mode. "
        "Return two options: one short direct version and one slightly warmer professional version. "
        "Do not add unsupported facts."
    )
    input_text = "\n\n".join(
        part
        for part in [
            f"Recent conversation context:\n{context_text()}" if st.session_state.segments else "",
            f"Response mode: {mode}",
            f"Korean draft:\n{korean_draft}",
        ]
        if part
    )
    return call_openai(settings, instructions, input_text, max_output_tokens=420)


def add_segment(english, korean):
    st.session_state.segments.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "english": english,
            "korean": korean,
        }
    )
    st.session_state.last_english = english
    st.session_state.last_translation = korean


def render_header(settings):
    left, right = st.columns([0.74, 0.26], vertical_alignment="center")
    with left:
        st.caption("Gwittim")
        st.title("조용히 듣고, 필요한 순간만 귀띔합니다.")
        st.write("영어 대화를 한국어로 따라가고, 필요한 답변을 영어로 다듬는 배포용 MVP입니다.")
    with right:
        if settings["api_key"]:
            st.success("API ready")
        else:
            st.error("API key required")
        st.caption(f"Model: {settings['model']}")


def render_live_panel(settings):
    st.subheader("한국어 자막")
    st.markdown(
        f"""
        <div style="border:1px solid #d8ded9;border-radius:8px;background:#ffffff;padding:28px 30px;margin-bottom:12px;">
          <div style="font-size:2.1rem;font-weight:850;line-height:1.25;color:#17211c;word-break:break-word;">{st.session_state.last_translation}</div>
          <div style="margin-top:14px;color:#647067;line-height:1.5;word-break:break-word;">{st.session_state.last_english}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("translate_form", clear_on_submit=True):
        english_text = st.text_area(
            "영어 발화 입력",
            placeholder="예: Could you walk me through the next milestone?",
            height=110,
        )
        submitted = st.form_submit_button("한국어로 귀띔", type="primary")

    if submitted:
        if not english_text.strip():
            st.warning("영어 문장을 먼저 입력해주세요.")
        else:
            with st.spinner("번역 중..."):
                try:
                    korean = translate(settings, english_text.strip())
                    add_segment(english_text.strip(), korean)
                    if len(st.session_state.segments) >= 3:
                        st.session_state.summary = summarize(settings)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    if st.session_state.segments:
        st.markdown("#### Transcript")
        for item in reversed(st.session_state.segments[-12:]):
            with st.container(border=True):
                st.caption(item["time"])
                st.write(f"**{item['korean']}**")
                st.caption(item["english"])


def render_assistant_panel(settings):
    st.subheader("실시간 요약")
    st.info(st.session_state.summary)

    if st.button("요약 새로고침", use_container_width=True, disabled=not st.session_state.segments):
        with st.spinner("요약 중..."):
            try:
                st.session_state.summary = summarize(settings)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("답변 귀띔")
    mode = st.radio(
        "답변 모드",
        options=["neutral", "agree", "disagree", "question"],
        index=0,
        horizontal=True,
        format_func={
            "neutral": "일반",
            "agree": "동의",
            "disagree": "반박",
            "question": "질문",
        }.get,
    )
    korean_draft = st.text_area(
        "한국어 초안",
        placeholder="예: 그 일정은 괜찮지만, 위험 요소를 먼저 확인하고 싶습니다.",
        height=120,
    )
    if st.button("영어 답변 만들기", use_container_width=True):
        if not korean_draft.strip():
            st.warning("한국어 초안을 먼저 입력해주세요.")
        else:
            with st.spinner("답변 생성 중..."):
                try:
                    st.session_state.reply_suggestion = compose_reply(
                        settings, korean_draft.strip(), mode
                    )
                except Exception as exc:
                    st.error(str(exc))
    st.code(st.session_state.reply_suggestion, language="text")

    st.divider()
    if st.button("세션 지우기", use_container_width=True):
        st.session_state.segments = []
        st.session_state.summary = "대화가 쌓이면 요약이 갱신됩니다."
        st.session_state.last_translation = "영어 문장을 입력하면 한국어 자막처럼 표시됩니다."
        st.session_state.last_english = "원문 영어는 여기에 함께 표시됩니다."
        st.session_state.reply_suggestion = "추천 영어 답변이 여기에 표시됩니다."
        st.rerun()


def main():
    init_state()
    settings = get_settings()
    render_header(settings)

    st.warning(
        "Streamlit 배포용 MVP는 텍스트 입력 기반입니다. 실시간 마이크 자막은 로컬 Node 웹앱에서 먼저 지원합니다."
    )

    main_col, side_col = st.columns([0.64, 0.36], gap="large")
    with main_col:
        render_live_panel(settings)
    with side_col:
        render_assistant_panel(settings)


if __name__ == "__main__":
    main()

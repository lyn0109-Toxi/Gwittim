import os
import re
from io import BytesIO
from html import escape

import requests
import streamlit as st

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


APP_TITLE = "Gwittim"
APP_MODE = "Nature Reviews Drug Discovery 수준 영작"
DEFAULT_WRITING_RESULT = "한글 문장을 입력하면 Nature Reviews Drug Discovery 수준의 과학 영어 문장으로 표시됩니다."
DEFAULT_WRITING_SOURCE = "영작 원문은 기록하지 않습니다."
DEFAULT_VOCABULARY_REVIEW = "영작을 실행하면 핵심 어휘의 의미, 인사이트, 재검증 포인트를 다시 확인할 수 있습니다."
DEFAULT_PAPER_ANALYSIS = "나의 목적과 논문 텍스트 또는 PDF를 추가하면 목적 매칭, Abs 요약, 섹터/섹션별 이슈, 결과 처리, 인사이트 발췌, 재검증 체크, 결론이 여기에 표시됩니다."
DEFAULT_MODEL = "gemini-3.6-flash"
PAPER_INPUT_LIMIT = 90000
PAPER_REQUIRED_HEADINGS = [
    "## 목적 매칭",
    "## Abs 요약",
    "## 섹터/섹션별 이슈",
    "## 결과 처리",
    "## 인사이트 발췌",
    "## 재검증 체크",
    "## 결론",
    "## 확인 질문",
]
PAPER_HEADING_ALIASES = {
    "abstract": "Abstract",
    "summary": "Abstract",
    "introduction": "Introduction",
    "background": "Background",
    "materials and methods": "Methods",
    "methods": "Methods",
    "methodology": "Methods",
    "results": "Results",
    "findings": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "limitations": "Limitations",
    "references": "References",
}
GEMINI_FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
GEMINI_TRANSIENT_ERROR_MARKERS = [
    "high demand",
    "temporarily unavailable",
    "try again later",
    "overloaded",
    "rate limit",
]
WRITING_DASH_REPLACEMENTS = {
    "dose-response": "dose response",
    "drug-like": "drug like",
    "first-in-human": "first in human",
    "follow-up": "follow up",
    "high-throughput": "high throughput",
    "in-depth": "in depth",
    "late-stage": "late stage",
    "non-clinical": "nonclinical",
    "pre-clinical": "preclinical",
    "proof-of-concept": "proof of concept",
    "state-of-the-art": "state of the art",
    "well-characterized": "well characterized",
}
LOCAL_REALTIME_URL = "http://127.0.0.1:3000"
GITHUB_REPO_URL = "https://github.com/lyn0109-Toxi/Gwittim"
GITHUB_CODESPACES_GUIDE_URL = (
    "https://github.com/lyn0109-Toxi/Gwittim/blob/main/docs/github-codespaces.md"
)


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state():
    defaults = {
        "segments": [],
        "summary": "대화 기록이 쌓이면 핵심 표현이 요약됩니다.",
        "last_translation": DEFAULT_WRITING_RESULT,
        "last_english": DEFAULT_WRITING_SOURCE,
        "last_vocabulary_review": DEFAULT_VOCABULARY_REVIEW,
        "live_reply_suggestion": "통역 내용이 쌓이면 지금 말할 수 있는 영어 표현을 자동으로 제안합니다.",
        "live_reply_signature": "",
        "reply_suggestion": "추천 영어 답변이 여기에 표시됩니다.",
        "paper_analysis": DEFAULT_PAPER_ANALYSIS,
        "paper_source_name": "",
        "paper_source_chars": 0,
        "paper_section_count": 0,
        "paper_user_purpose": "",
        "paper_match_score": "",
        "paper_extraction_notice": "",
        "paper_extracted_preview": "",
        "auto_compose": True,
        "session_api_key": "",
        "active_session": "텍스트 세션",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def secret_value(name, fallback=""):
    try:
        secret = st.secrets.get(name, "")
        if secret:
            return secret
    except Exception:
        pass

    env_value = os.getenv(name, "")
    if env_value:
        return env_value

    return local_env_values().get(name, fallback)


def local_env_values():
    values = {}
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for line in env_file:
                trimmed = line.strip()
                if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
                    continue
                key, value = trimmed.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    return values


def normalize_model_name(model):
    return model.strip().removeprefix("models/")


def inject_global_styles():
    st.markdown(
        """
        <style>
          .stApp {
            background:
              linear-gradient(90deg, rgba(63, 169, 232, 0.08) 1px, transparent 1px),
              linear-gradient(0deg, rgba(63, 169, 232, 0.055) 1px, transparent 1px),
              linear-gradient(135deg, #fbfdff 0%, #edf8ff 46%, #f7fcff 100%);
            background-size: 48px 48px, 48px 48px, auto;
            color: #10243d;
            font-size: 14px;
          }
          .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.2rem;
            max-width: 1220px;
          }
          div[data-testid="stMarkdownContainer"] p,
          div[data-testid="stMarkdownContainer"] li,
          div[data-testid="stMarkdownContainer"] td,
          div[data-testid="stMarkdownContainer"] th {
            font-size: .9rem;
            line-height: 1.55;
          }
          div[data-testid="stMarkdownContainer"] h1 {
            font-size: 1.45rem;
            line-height: 1.25;
            margin: .45rem 0 .35rem;
          }
          div[data-testid="stMarkdownContainer"] h2 {
            font-size: 1.18rem;
            line-height: 1.3;
            margin: 1rem 0 .35rem;
          }
          div[data-testid="stMarkdownContainer"] h3 {
            font-size: 1rem;
            line-height: 1.35;
            margin: .9rem 0 .35rem;
          }
          div[data-testid="stMarkdownContainer"] table {
            font-size: .84rem;
            line-height: 1.45;
            border-collapse: collapse;
          }
          div[data-testid="stMarkdownContainer"] th,
          div[data-testid="stMarkdownContainer"] td {
            padding: .42rem .5rem;
            vertical-align: top;
          }
          textarea,
          input,
          .stTextInput input {
            font-size: .9rem !important;
          }
          section[data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.88);
            border-right: 1px solid rgba(123, 190, 234, 0.32);
            backdrop-filter: blur(18px);
          }
          div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: rgba(123, 190, 234, 0.32);
            background: rgba(255, 255, 255, 0.78);
            box-shadow: 0 8px 22px rgba(64, 146, 207, 0.075);
          }
          .gw-brand {
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            gap: 12px;
            align-items: center;
            margin: 2px 0 8px;
          }
          .gw-brand-mark {
            width: 42px;
            height: 42px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            align-items: end;
            gap: 4px;
            padding: 7px;
            border: 1px solid rgba(63, 169, 232, 0.42);
            border-radius: 8px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(230, 247, 255, 0.9));
            box-shadow: 0 8px 20px rgba(39, 143, 214, 0.14);
          }
          .gw-brand-mark span {
            display: block;
            border-radius: 6px 6px 2px 2px;
          }
          .gw-brand-mark span:nth-child(1) {
            height: 42%;
            background: #2563eb;
          }
          .gw-brand-mark span:nth-child(2) {
            height: 76%;
            background: #1da9e8;
          }
          .gw-brand-mark span:nth-child(3) {
            height: 56%;
            background: #3bd6c6;
          }
          .gw-brand small {
            display: block;
            color: #1da9e8;
            font-weight: 850;
            letter-spacing: 0;
            text-transform: uppercase;
          }
          .gw-brand strong {
            display: block;
            margin-top: 2px;
            color: #10243d;
            font-size: 1.26rem;
            line-height: 1.18;
          }
          .gw-flow {
            display: grid;
            grid-template-columns: minmax(120px, 1fr) 42px minmax(120px, 1fr) 42px minmax(120px, 1fr) minmax(120px, .8fr);
            gap: 8px;
            align-items: center;
            margin: 12px 0 14px;
            padding: 10px;
            border: 1px solid rgba(123, 190, 234, 0.4);
            border-radius: 8px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(231, 247, 255, 0.76));
            box-shadow: 0 8px 22px rgba(64, 146, 207, 0.075);
            backdrop-filter: blur(18px);
          }
          .gw-flow-step {
            min-height: 58px;
            display: grid;
            align-content: center;
            gap: 3px;
            padding: 10px;
            border-left: 4px solid rgba(123, 190, 234, 0.4);
            background: rgba(255, 255, 255, 0.62);
          }
          .gw-flow-step.is-active {
            border-left-color: #1da9e8;
            background: #e6f7ff;
            box-shadow: inset 0 0 0 1px rgba(29, 169, 232, 0.12), 0 8px 18px rgba(29, 169, 232, 0.12);
          }
          .gw-flow-step span {
            color: #5e758f;
            font-size: .72rem;
            font-weight: 900;
          }
          .gw-flow-step strong {
            font-size: .9rem;
            color: #10243d;
          }
          .gw-flow-line {
            height: 2px;
            background: linear-gradient(90deg, rgba(37, 99, 235, .2), rgba(18, 191, 213, .56), rgba(59, 214, 198, .24));
          }
          .gw-meter {
            height: 58px;
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            align-items: end;
            gap: 6px;
            padding: 10px;
            border-left: 1px solid rgba(123, 190, 234, 0.32);
            background: repeating-linear-gradient(90deg, rgba(63, 169, 232, 0.12) 0, rgba(63, 169, 232, 0.12) 1px, transparent 1px, transparent 9px);
          }
          .gw-meter span {
            min-height: 12px;
            border-radius: 5px 5px 2px 2px;
          }
          .gw-meter span:nth-child(1) { height: 24%; background: #2563eb; }
          .gw-meter span:nth-child(2) { height: 58%; background: #1da9e8; }
          .gw-meter span:nth-child(3) { height: 38%; background: #12bfd5; }
          .gw-meter span:nth-child(4) { height: 76%; background: #6ea8ff; }
          .gw-meter span:nth-child(5) { height: 48%; background: #3bd6c6; }
          .gw-kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 4px 0 14px;
          }
          .gw-kpi-grid.gw-kpi-grid-four {
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }
          .gw-kpi-grid.gw-kpi-grid-five {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
          .gw-kpi {
            min-height: 66px;
            display: grid;
            align-content: center;
            gap: 4px;
            padding: 11px;
            border: 1px solid rgba(123, 190, 234, 0.32);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.74);
            box-shadow: 0 8px 20px rgba(64, 146, 207, 0.075);
          }
          .gw-kpi span {
            color: #5e758f;
            font-size: .76rem;
            font-weight: 850;
          }
          .gw-kpi strong {
            color: #10243d;
            font-size: .98rem;
          }
          .gw-live-card {
            margin: 10px 0 16px;
            padding: 14px;
            border: 1px solid rgba(123, 190, 234, 0.32);
            border-radius: 8px;
            background: #e8f8ff;
            box-shadow: 0 12px 32px rgba(64, 146, 207, 0.1);
          }
          .gw-live-card small {
            display: block;
            margin-bottom: 8px;
            color: #0876b2;
            font-weight: 900;
            letter-spacing: 0;
            text-transform: uppercase;
          }
          .gw-live-card pre {
            margin: 0;
            color: #143a52;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: inherit;
            font-size: .9rem;
            line-height: 1.48;
          }
          .gw-session-card {
            min-height: 112px;
            padding: 13px;
            border: 1px solid rgba(123, 190, 234, 0.32);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.74);
            box-shadow: 0 8px 20px rgba(64, 146, 207, 0.075);
          }
          .gw-subtitle-card {
            border: 1px solid rgba(123, 190, 234, 0.32);
            border-radius: 8px;
            background:
              linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(226, 246, 255, 0.62)),
              repeating-linear-gradient(90deg, rgba(63, 169, 232, 0.08) 0, rgba(63, 169, 232, 0.08) 1px, transparent 1px, transparent 18px);
            padding: 20px 22px;
            margin-bottom: 10px;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55), 0 8px 20px rgba(64, 146, 207, 0.075);
          }
          .gw-subtitle-card strong {
            display: block;
            color: #10243d;
            font-size: 1.45rem;
            font-weight: 850;
            line-height: 1.32;
            word-break: break-word;
          }
          .gw-subtitle-card span {
            display: block;
            margin-top: 14px;
            color: #5e758f;
            font-size: .9rem;
            line-height: 1.5;
            word-break: break-word;
          }
          .stButton > button,
          .stFormSubmitButton > button,
          .stLinkButton a {
            border-radius: 8px;
            border-color: rgba(29, 169, 232, 0.42) !important;
          }
          .stButton > button,
          .stFormSubmitButton > button {
            background: linear-gradient(135deg, #12bfd5, #2563eb) !important;
            border: 0 !important;
            color: #ffffff !important;
            box-shadow: 0 12px 26px rgba(29, 169, 232, 0.24);
          }
          .stButton > button:disabled,
          .stFormSubmitButton > button:disabled {
            background: rgba(226, 246, 255, 0.86) !important;
            color: #5e758f !important;
            box-shadow: none;
          }
          input[type="radio"],
          input[type="checkbox"] {
            accent-color: #1da9e8;
          }
          @media (max-width: 900px) {
            .gw-flow,
            .gw-kpi-grid {
              grid-template-columns: 1fr;
            }
            .gw-flow-line {
              display: none;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_settings():
    configured_key = secret_value("GEMINI_API_KEY", "")
    session_key = st.session_state.get("session_api_key", "")
    model = secret_value("GEMINI_TEXT_MODEL", os.getenv("GEMINI_TEXT_MODEL", DEFAULT_MODEL))
    translation_target = secret_value(
        "GEMINI_TRANSLATION_TARGET", os.getenv("GEMINI_TRANSLATION_TARGET", "ko")
    )

    with st.sidebar:
        st.markdown("### Session")
        session_options = ["텍스트 세션", "번역 세션", "통역 세션"]
        current_index = (
            session_options.index(st.session_state.active_session)
            if st.session_state.active_session in session_options
            else 0
        )
        active_session = st.radio(
            "들어갈 세션",
            options=session_options,
            index=current_index,
            horizontal=True,
        )
        st.session_state.active_session = active_session
        if active_session == "텍스트 세션":
            clear_text_session_records()

        if active_session == "텍스트 세션":
            st.info("Nature Reviews Drug Discovery 수준 영작")
            st.caption("한글 원문을 저널 제출 수준의 과학 영어 문장으로 다듬고, 영작 기록은 저장하지 않습니다.")
        elif active_session == "번역 세션":
            st.info("논문 바로 정리")
            st.caption("논문 텍스트나 PDF에서 Abs 요약, 이슈, 결과 처리, 인사이트, 재검증 체크를 정리합니다.")
        else:
            st.info("실시간 통역 세션")
            st.caption("마이크 통역은 로컬 또는 Codespaces 앱에서 엽니다.")

        if configured_key:
            st.info("API key connected")
            api_key = configured_key
            key_source = "secret"
        elif session_key:
            st.info("API key applied for this session")
            st.caption("이 브라우저 세션 동안 번역에 사용됩니다.")
            if st.button("API key 지우기", use_container_width=True):
                st.session_state.session_api_key = ""
                st.rerun()
            api_key = session_key
            key_source = "session"
        else:
            st.caption("Gemini API key를 한 번 붙여넣고 적용하세요.")
            with st.form("api_key_setup_form"):
                entered_key = st.text_input(
                    "Gemini API key",
                    value="",
                    type="password",
                    placeholder="AIza...",
                    help="Streamlit Secrets가 없을 때 이 브라우저 세션에서만 사용합니다.",
                )
                submitted_key = st.form_submit_button("API key 한번에 적용", type="primary")

            if submitted_key:
                cleaned_key = entered_key.strip()
                if cleaned_key:
                    st.session_state.session_api_key = cleaned_key
                    st.rerun()
                st.warning("Gemini API key를 먼저 붙여넣어주세요.")

            api_key = ""
            key_source = "missing"

        st.caption("영구 적용은 Streamlit Cloud Settings > Secrets에서 설정합니다.")
        selected_model = st.text_input("Model", value=model)
        selected_target = st.text_input("Translation target", value=translation_target)
        save_audio = st.toggle("Store raw audio", value=False, disabled=True)
        voice_output = st.toggle("Voice output", value=False, disabled=True)
        st.caption("현재 배포 앱은 오디오를 저장하지 않고, 통역 음성도 출력하지 않습니다.")

    return {
        "api_key": api_key,
        "key_from_secret": bool(configured_key),
        "key_source": key_source,
        "active_session": active_session,
        "model": normalize_model_name(selected_model) or DEFAULT_MODEL,
        "translation_target": selected_target.strip() or "ko",
        "save_audio": save_audio,
        "voice_output": voice_output,
    }


def call_gemini(settings, instructions, input_text, max_output_tokens=360):
    if not settings["api_key"]:
        raise RuntimeError("Gemini API key가 필요합니다. 사이드바에서 한 번 붙여넣고 적용해주세요.")

    primary_model = normalize_model_name(settings["model"])
    candidate_models = [primary_model]
    candidate_models.extend(
        model_name for model_name in GEMINI_FALLBACK_MODELS if model_name != primary_model
    )

    errors = []
    for model_name in candidate_models:
        generation_config = {
            "maxOutputTokens": max_output_tokens,
        }
        if model_name.startswith("gemini-3"):
            generation_config["thinkingConfig"] = {"thinkingLevel": "low"}

        payload = {
            "systemInstruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
            "generationConfig": generation_config,
        }

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            headers={
                "x-goog-api-key": settings["api_key"],
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )

        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}

        if not response.ok:
            message = data.get("error", {}).get("message") or data.get("message") or response.text
            errors.append(f"{model_name}: {message}")
            if is_transient_gemini_error(message, response.status_code):
                continue
            raise RuntimeError(message)

        parts = []
        finish_reasons = []
        for candidate in data.get("candidates", []):
            finish_reason = candidate.get("finishReason")
            if finish_reason:
                finish_reasons.append(finish_reason)
            for content in candidate.get("content", {}).get("parts", []):
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)

        result = "\n".join(parts).strip()
        if not result:
            reason = ", ".join(finish_reasons) or str(data.get("promptFeedback") or "unknown")
            errors.append(f"{model_name}: empty result ({reason})")
            if is_transient_gemini_error(reason, response.status_code):
                continue
            raise RuntimeError(f"Gemini가 결과 텍스트를 반환하지 않았습니다. 처리 상태: {reason}")

        if "MAX_TOKENS" in finish_reasons:
            result = (
                f"{result}\n\n"
                "## 처리 메모\n"
                "- 출력 길이 제한에 가까워져 일부 내용이 짧게 정리되었을 수 있습니다. "
                "논문 텍스트를 나누어 넣거나 정리 깊이를 낮춰 다시 시도하세요."
            )

        return result

    raise RuntimeError("Gemini 요청이 일시적으로 실패했습니다. " + " | ".join(errors[-3:]))


def is_transient_gemini_error(message, status_code):
    lowered = str(message).lower()
    if status_code in {408, 429, 500, 502, 503, 504}:
        return True
    return any(marker in lowered for marker in GEMINI_TRANSIENT_ERROR_MARKERS)


def context_text(limit=8):
    recent = st.session_state.segments[-limit:]
    lines = []
    for item in recent:
        lines.append(f"EN: {item['english']}\nKO: {item['korean']}")
    return "\n\n".join(lines)


def extract_pdf_text(uploaded_file):
    if uploaded_file is None:
        return ""

    if PdfReader is None:
        raise RuntimeError("PDF 처리를 위해 pypdf가 필요합니다. 배포 환경에서는 requirements.txt로 자동 설치됩니다.")

    reader = PdfReader(BytesIO(uploaded_file.getvalue()))
    pages = []
    for page_index, page in enumerate(reader.pages[:80]):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {page_index + 1}]\n{text.strip()}")
    return "\n\n".join(pages)


def normalize_paper_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_text(text, max_chars):
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)].rstrip()
    tail = text[-int(max_chars * 0.3) :].lstrip()
    return f"{head}\n\n[중간 본문 일부 생략]\n\n{tail}"


def identify_paper_heading(line):
    cleaned = re.sub(r"^\s*(\d+(\.\d+)*\.?|[IVX]+\.?)\s+", "", line.strip(), flags=re.I)
    cleaned = cleaned.strip(" :-–—.")
    lower = cleaned.lower()
    if lower in PAPER_HEADING_ALIASES:
        return PAPER_HEADING_ALIASES[lower]
    if len(cleaned) <= 72:
        for alias, label in PAPER_HEADING_ALIASES.items():
            if lower.startswith(f"{alias}:"):
                return label
    return ""


def extract_paper_sections(text):
    normalized = normalize_paper_text(text)
    if not normalized:
        return []

    sections = []
    current_label = "Front matter"
    current_lines = []

    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        heading = identify_paper_heading(line)
        if heading:
            if current_lines:
                sections.append(
                    {
                        "label": current_label,
                        "text": "\n".join(current_lines).strip(),
                    }
                )
            current_label = heading
            current_lines = []
            remainder = re.sub(
                r"^\s*(\d+(\.\d+)*\.?|[IVX]+\.?)?\s*[A-Za-z ]+\s*[:.-]\s*",
                "",
                line,
            ).strip()
            if remainder and remainder.lower() != line.lower():
                current_lines.append(remainder)
            continue
        current_lines.append(raw_line)

    if current_lines:
        sections.append({"label": current_label, "text": "\n".join(current_lines).strip()})

    return [section for section in sections if section["text"]]


def build_section_digest(sections):
    if not sections:
        return "감지된 논문 섹션 없음"

    rows = []
    for index, section in enumerate(sections[:18], start=1):
        section_text = section["text"]
        rows.append(
            f"{index}. {section['label']} ({len(section_text):,} chars)\n"
            f"{truncate_text(section_text, 2600)}"
        )
    return "\n\n".join(rows)


def paper_extraction_notice(source_chars, section_count, uploaded_pdf):
    notices = []
    if uploaded_pdf and source_chars < 1500:
        notices.append(
            "PDF에서 추출된 텍스트가 적습니다. 스캔 PDF이거나 표/이미지 중심 논문이면 텍스트를 직접 붙여넣는 편이 정확합니다."
        )
    if source_chars < 900:
        notices.append("입력 텍스트가 짧아 논문 전체 결론과 한계를 충분히 판단하기 어렵습니다.")
    if section_count < 2:
        notices.append("섹션 제목을 충분히 감지하지 못했습니다. Abstract, Results, Discussion, Conclusion이 포함된 본문을 넣으면 정리가 좋아집니다.")
    return " ".join(notices)


def normalize_paper_analysis_output(analysis, source_chars, section_count):
    text = analysis.strip()
    missing = [heading for heading in PAPER_REQUIRED_HEADINGS if heading not in text]
    if missing:
        text = (
            f"{text}\n\n"
            "## 처리 메모\n"
            f"- 결과 형식에서 누락된 항목: {', '.join(missing)}\n"
            "- 논문 텍스트가 짧거나 섹션 구분이 불명확하면 일부 항목이 간략해질 수 있습니다."
        )

    if "## 처리 메모" not in text:
        text = (
            f"{text}\n\n"
            "## 처리 메모\n"
            f"- 입력 텍스트: {source_chars:,}자\n"
            f"- 감지한 섹터/섹션: {section_count}개\n"
            "- 위 정리는 입력된 텍스트에 근거하며, PDF에서 추출되지 않은 표/그림 정보는 반영되지 않을 수 있습니다."
        )
    return text


def extract_purpose_match_score(analysis):
    match = re.search(r"목적\s*매칭\s*점수\s*[:：]\s*(\d{1,3})\s*/\s*100", analysis)
    if not match:
        match = re.search(r"목적\s*매칭\s*점수\s*[:：]\s*(\d{1,3})\s*점", analysis)
    if not match:
        return ""
    score = max(0, min(100, int(match.group(1))))
    return f"{score}/100"


def paper_depth_instruction(depth):
    if depth == "빠른":
        return "Keep the answer compact: 2 to 4 bullets per section and at least 4 issue rows if evidence is available."
    if depth == "표준":
        return "Write a balanced review: 4 to 6 bullets per section and at least 6 issue rows if evidence is available."
    return "Write a detailed review: 5 to 8 bullets per section and at least 8 issue rows if evidence is available. Include concrete evidence, endpoints, models, numbers, and limitations whenever present."


def analyze_paper(settings, paper_text, source_name, depth="상세", user_purpose=""):
    normalized_text = normalize_paper_text(paper_text)
    sections = extract_paper_sections(normalized_text)
    section_digest = build_section_digest(sections)
    compact_text = truncate_text(normalized_text, PAPER_INPUT_LIMIT)
    section_count = len(sections)
    purpose_text = user_purpose.strip()
    instructions = (
        "You are Gwittim, a scientific paper translation and analysis assistant for Korean readers in drug discovery, toxicology, regulatory science, and pharmaceutical development. "
        "Analyze the supplied paper text in Korean with enough detail for a scientist to decide what to read next. "
        "Do not invent facts, numbers, claims, limitations, methods, or conclusions that are not supported by the supplied text. "
        "If the abstract, section headings, methods, results, figures, tables, or conclusion are missing, explicitly say that the information is not clearly available. "
        "Prioritize abstract, introduction, methods, results, discussion, conclusion, limitations, figures/tables mentioned in text, and safety or translational-development implications. "
        "Preserve key English terms, target names, modality names, drug names, assay names, endpoints, biomarkers, species, cell lines, doses, concentrations, p values, confidence intervals, dates, and numerical values. "
        "For the Results section, explain how the evidence was processed or interpreted: models, assays, cohorts, endpoints, controls, comparators, statistical signals, and what remains uncertain. "
        "Extract insights only from the inspected text. Separate direct observations from interpretation. "
        "For each insight, cite the supporting section or exact source phrase in Korean summary form and assign confidence as 높음, 중간, or 낮음. "
        "Add a revalidation checklist for claims, numbers, endpoints, figures, tables, statistical signals, translational implications, limitations, and any conclusion that could change after checking the original paper. "
        "If a Korean user purpose is provided, compare it with the paper's apparent research objective, model, endpoint, modality, development stage, and practical use. "
        "Calculate a purpose match score from 0 to 100. Use 80 to 100 only for direct alignment, 60 to 79 for partial but useful alignment, 40 to 59 for broad topical overlap, and below 40 for weak alignment. "
        "List concrete matching points and mismatches. Cite the paper section or source phrase that supports each point. "
        "If the user purpose is not provided, write 목적 매칭 점수: 미입력 and ask the user to add a purpose. "
        "If a point cannot be verified from the supplied text, label it 근거 부족 rather than filling the gap. "
        "Use clear Korean, but keep essential scientific terms in English in parentheses when helpful. "
        f"{paper_depth_instruction(depth)} "
        "Return only this Markdown structure and use every heading: "
        "## 목적 매칭 "
        "## Abs 요약 "
        "## 섹터/섹션별 이슈 "
        "## 결과 처리 "
        "## 인사이트 발췌 "
        "## 재검증 체크 "
        "## 결론 "
        "## 확인 질문."
    )
    input_text = "\n\n".join(
        [
            f"Source name: {source_name or 'pasted text'}",
            f"User purpose in Korean:\n{purpose_text or '미입력'}",
            f"Analysis depth: {depth}",
            f"Detected section count: {section_count}",
            "Required output format:",
            "## 목적 매칭\n목적 매칭 점수: <0-100>/100 또는 미입력\n| 매칭 포인트 | 논문 근거/섹션 | 나의 목적과 연결 | 재검증 필요성 |",
            "## Abs 요약\n- 연구 질문\n- 배경/미충족 수요\n- 접근법\n- 핵심 결과\n- 의미\n- 한계",
            "## 섹터/섹션별 이슈\n| 섹터/섹션 | 핵심 주장/결과 | 근거 | 이슈/한계 | 확인할 포인트 |",
            "## 결과 처리\n- 주요 결과가 어떤 실험/분석/비교로 도출됐는지\n- 통계/정량값/endpoint가 어떻게 해석되는지\n- 표/그림에서 확인해야 할 부분\n- 과잉 해석 위험",
            "## 인사이트 발췌\n| 인사이트 | 원문 근거/섹션 | 왜 중요한가 | 신뢰도 |",
            "## 재검증 체크\n| 재검증 항목 | 현재 근거 | 확인 방법 | 틀렸을 때 위험 |",
            "## 결론\n- 논문의 결론\n- 개발/규제/독성 관점의 시사점\n- 후속 연구 또는 검증 포인트\n- 과도하게 해석하면 안 되는 부분",
            "## 확인 질문\n- 추가로 읽어야 할 질문 5개",
            f"Detected section digest:\n{section_digest}",
            f"Full paper text excerpt:\n{compact_text}",
        ]
    )
    raw_analysis = call_gemini(settings, instructions, input_text, max_output_tokens=7600)
    return normalize_paper_analysis_output(raw_analysis, len(normalized_text), section_count)


def live_compose_signature(mode):
    if not st.session_state.segments:
        return ""

    recent = st.session_state.segments[-3:]
    parts = [mode]
    for item in recent:
        parts.append(f"{item['time']}|{item['english']}|{item['korean']}")
    return "\n".join(parts)


def live_compose(settings, mode):
    if not st.session_state.segments:
        return "통역 내용이 쌓이면 지금 말할 수 있는 영어 표현을 자동으로 제안합니다."

    transcript = "\n".join(
        f"{idx + 1}. EN: {item['english']}\n   KO: {item['korean']}"
        for idx, item in enumerate(st.session_state.segments[-10:])
    )
    instructions = (
        "You are Gwittim, a discreet live response coach for a Korean speaker in an English conversation. "
        "Read the recent English/Korean transcript and suggest useful spoken English responses the user can say now. "
        "Do not invent facts, commitments, numbers, or decisions. "
        "If the next response is unclear, suggest a natural clarification question. "
        "Return exactly three complete lines in plain text with no Markdown. "
        "Use this exact format: 지금 말할 수 있는 표현: "
        "1. <short English sentence> 2. <warmer English sentence> "
        "확인 질문: <English clarification question>. "
        "Keep every English sentence compact and immediately speakable. "
        "Prefer natural phrasal verbs for live spoken cues when they fit, especially follow up, look into, walk through, bring up, point out, move forward, rule out, narrow down, set up, carry out, and circle back. "
        "Do not force a phrasal verb if it would make the sentence vague or too casual. "
        "Do not use contractions or apostrophes."
    )
    input_text = "\n\n".join(
        [
            f"Response mode: {mode}",
            f"Recent live conversation:\n{transcript}",
            "\n".join(
                [
                    "Return this structure:",
                    "지금 말할 수 있는 표현",
                    "1. <short English sentence>",
                    "2. <slightly warmer English sentence>",
                    "확인 질문: <English clarification question>",
                ]
            ),
        ]
    )
    suggestion = call_gemini(settings, instructions, input_text, max_output_tokens=820)
    return normalize_live_compose_suggestion(suggestion, mode)


def normalize_live_compose_suggestion(suggestion, mode):
    text = suggestion.strip()
    if is_complete_live_compose_suggestion(text):
        return text

    templates = {
        "agree": [
            "지금 말할 수 있는 표현:",
            "1. I agree that we should look into the risks first.",
            "2. That makes sense, and I would like to walk through the potential risks before we move forward.",
            "확인 질문: Could you clarify the main risk we should focus on?",
        ],
        "disagree": [
            "지금 말할 수 있는 표현:",
            "1. I see your point, but I would like to look into the risks first.",
            "2. I understand the plan, but I think we should walk through the potential risks before we decide.",
            "확인 질문: Could you explain why this timing feels safe to commit to?",
        ],
        "question": [
            "지금 말할 수 있는 표현:",
            "1. Could we check the risks before we commit?",
            "2. Could you walk me through the main risks before we move forward?",
            "확인 질문: What is the biggest risk we should confirm first?",
        ],
        "neutral": [
            "지금 말할 수 있는 표현:",
            "1. I understand. I would like to look into the risks first.",
            "2. That makes sense, and I would like to walk through the potential risks before we move forward.",
            "확인 질문: Could you clarify the main risk we should focus on?",
        ],
    }
    return "\n".join(templates.get(mode, templates["neutral"]))


def is_complete_live_compose_suggestion(text):
    return (
        "1." in text
        and "2." in text
        and "확인 질문:" in text
        and text.rstrip().endswith("?")
    )


def maybe_refresh_live_compose(settings, mode):
    if not st.session_state.get("auto_compose", True):
        st.session_state.live_reply_signature = ""
        return "꺼짐"

    signature = live_compose_signature(mode)
    if not signature:
        st.session_state.live_reply_suggestion = (
            "통역 내용이 쌓이면 지금 말할 수 있는 영어 표현을 자동으로 제안합니다."
        )
        st.session_state.live_reply_signature = ""
        return "대기"

    if signature == st.session_state.live_reply_signature:
        return "갱신됨"

    if not settings["api_key"]:
        st.session_state.live_reply_suggestion = "Gemini API key를 연결하면 실시간 귀띔이 켜집니다."
        st.session_state.live_reply_signature = ""
        return "API key 필요"

    with st.spinner("실시간 귀띔 갱신 중..."):
        try:
            st.session_state.live_reply_suggestion = live_compose(settings, mode)
            st.session_state.live_reply_signature = signature
            return "갱신됨"
        except Exception as exc:
            st.session_state.live_reply_suggestion = f"오류: {exc}"
            st.session_state.live_reply_signature = signature
            return "오류"


def translate(settings, korean_text):
    instructions = (
        "You are Gwittim, a senior scientific editor for drug discovery and development manuscripts. "
        "Rewrite the Korean draft into publication-grade English calibrated to Nature Reviews Drug Discovery and Nature Portfolio expectations. "
        "Target professional scientists across drug discovery, pharmacology, toxicology, translational medicine, regulatory science, and adjacent disciplines. "
        "Make the sentence clear enough for readers outside the immediate specialty while preserving technical precision. "
        "Prefer active voice, direct syntax, concise sentence structure, logical flow, and strong signposting. "
        "Convert Korean-first structure into idiomatic scientific English rather than translating literally. "
        "Unpack dense noun strings, remove filler, reduce unnecessary acronyms, and avoid jargon-heavy phrasing unless the term is field-standard. "
        "Use careful scientific hedging: avoid overstating causality, efficacy, novelty, clinical relevance, regulatory readiness, or mechanism unless the input explicitly supports it. "
        "Emphasize the scientific meaning, translational implication, and development relevance of the statement. "
        "Preserve technical terms, target names, gene/protein nomenclature, assay names, endpoints, drug names, dates, numbers, statistics, and SI units exactly unless the Korean clearly asks for revision. "
        "Use International Nonproprietary Names for drugs when the input provides or clearly implies them, and specify species or model systems when ambiguity could affect interpretation. "
        "Do not use hyphens, en dashes, or em dashes as sentence punctuation or stylistic compound modifiers. "
        "For ranges, use 'to' rather than a dash. Rephrase with commas, parentheses, or plain spaces where needed. "
        "Preserve a hyphen only when removing it would alter an established scientific identifier, such as PD-1, IL-6, a compound code, or a gene/protein name. "
        "Do not add unsupported data, citations, mechanisms, limitations, regulatory claims, or clinical claims. "
        "If the Korean text is fragmentary, produce the best polished manuscript sentence without inventing missing context. "
        "Return only the polished English text, with no explanation, no bullets, and no quotation marks."
    )
    input_text = f"Current Korean draft:\n{korean_text}"
    english = call_gemini(settings, instructions, input_text, max_output_tokens=1200)
    return remove_sentence_dashes(english)


def review_vocabulary(settings, korean_text, english_text):
    instructions = (
        "You are Gwittim, a scientific vocabulary coach for Korean researchers writing drug discovery and development manuscripts. "
        "Review the polished English sentence and help the user reconsider the meaning of important vocabulary choices. "
        "Focus on semantic precision, nuance, register, and whether the word is appropriate for Nature Reviews Drug Discovery-level scientific writing. "
        "Choose 4 to 6 important words or phrases from the English result, prioritizing verbs, hedging words, development terms, endpoints, and terms that could be mistranslated from Korean. "
        "After the vocabulary review, extract practical insights from the checked vocabulary, such as how the wording frames evidence strength, uncertainty, development relevance, or claim boundaries. "
        "Then add a revalidation checklist that tells the user which terms or claims should be checked against the original data, methods, results, or target journal context before use. "
        "Do not invent scientific facts or suggest claims not supported by the Korean source. "
        "Do not use hyphens, en dashes, em dashes, or bullet markers. Use numbered items only. "
        "Preserve established scientific identifiers if present. "
        "Return Korean text only, using this exact structure: "
        "## 어휘 점검 "
        "1. <English term>: 의미 <Korean meaning>. 선택 이유 <why it fits>. 다시 생각할 점 <nuance or caution>. 대체 가능 표현 <alternative if useful>. "
        "## 인사이트 발췌 "
        "1. <insight from the reviewed vocabulary>. 근거 <source wording or English term>. 적용 의미 <why it matters>. "
        "## 재검증 체크 "
        "1. <term or claim to recheck>. 확인할 내용 <what to verify>. 확인 방법 <how to verify>. 위험 <risk if wrong>. "
        "## 전체 뉘앙스 "
        "<one short Korean paragraph on whether the sentence is cautious, assertive, translational, mechanistic, or developmental>."
    )
    input_text = "\n\n".join(
        [
            f"Korean source:\n{korean_text}",
            f"Polished English:\n{english_text}",
        ]
    )
    review = call_gemini(settings, instructions, input_text, max_output_tokens=1600)
    return clean_vocabulary_review(review)


def clean_vocabulary_review(text):
    cleaned = text.strip()
    cleaned = re.sub(r"(?m)^\s*[-•]\s+", "", cleaned)
    for source, target in WRITING_DASH_REPLACEMENTS.items():
        cleaned = re.sub(re.escape(source), target, cleaned, flags=re.IGNORECASE)

    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = re.sub(r"(?<=[a-z])[-‐‑‒](?=[a-z])", " ", cleaned)
    cleaned = re.sub(r"[ \t]+[-‐‑‒–—][ \t]+", ", ", cleaned)
    cleaned = re.sub(r"[ \t]*[–—][ \t]*", ", ", cleaned)
    cleaned = re.sub(r"[ \t]+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def remove_sentence_dashes(text):
    cleaned = text.strip()
    for source, target in WRITING_DASH_REPLACEMENTS.items():
        cleaned = re.sub(re.escape(source), target, cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"(?<=\d)\s*[-‐‑‒–—]\s*(?=\d)", " to ", cleaned)
    cleaned = re.sub(r"\s+[-‐‑‒–—]\s+", ", ", cleaned)
    cleaned = re.sub(r"\s*[–—]\s*", ", ", cleaned)
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = re.sub(r"(?<=[a-z])[-‐‑‒](?=[a-z])", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,")


def summarize(settings):
    transcript = "\n".join(
        f"{idx + 1}. EN: {item['english']}\n   KO: {item['korean']}"
        for idx, item in enumerate(st.session_state.segments[-24:])
    )
    instructions = (
        "You are Gwittim, a scientific writing brief assistant. Summarize the current "
        "Korean-to-English writing history in Korean. Keep it short, concrete, and useful. "
        "Use compact bullets. Highlight recurring terminology, phrasing choices, and possible style risks only if present."
    )
    return call_gemini(settings, instructions, transcript, max_output_tokens=380)


def compose_reply(settings, korean_draft, mode):
    instructions = (
        "You are Gwittim, helping a Korean speaker respond naturally in an English conversation. "
        "Convert the user's Korean draft into concise, spoken English. Match the requested response mode. "
        "Return exactly two complete English sentences. "
        "Use this exact plain-text format with no Markdown: "
        "1. <short direct sentence> 2. <slightly warmer professional sentence>. "
        "Prefer a natural phrasal verb when it is precise and appropriate, such as follow up, look into, walk through, bring up, point out, move forward, rule out, narrow down, set up, carry out, or circle back. "
        "Do not force phrasal verbs if they would sound informal or reduce scientific precision. "
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
    return call_gemini(settings, instructions, input_text, max_output_tokens=720)


def show_current_writing_result(english):
    st.session_state.last_translation = english
    st.session_state.last_english = DEFAULT_WRITING_SOURCE


def clear_text_session_records():
    st.session_state.segments = []
    st.session_state.summary = "대화 기록이 쌓이면 핵심 표현이 요약됩니다."
    st.session_state.live_reply_signature = ""


def render_brand_mark():
    st.markdown(
        """
        <div class="gw-brand">
          <div class="gw-brand-mark" aria-hidden="true">
            <span></span><span></span><span></span>
          </div>
          <div>
            <small>Gwittim</small>
            <strong>조용히 듣고, 필요한 순간만 귀띔합니다.</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_flow_graph(active_stage="compose", flow="interpretation"):
    if flow == "writing":
        steps = [
            ("listen", "01", "Korean"),
            ("translate", "02", "Rewrite"),
            ("compose", "03", "Compose"),
        ]
    elif flow == "paper":
        steps = [
            ("listen", "01", "Paper"),
            ("translate", "02", "Results"),
            ("compose", "03", "Conclusion"),
        ]
    else:
        steps = [
            ("listen", "01", "Listen"),
            ("translate", "02", "Translate"),
            ("compose", "03", "Compose"),
        ]
    step_html = []
    for stage, index, label in steps:
        active = " is-active" if stage == active_stage else ""
        step_html.append(
            f'<div class="gw-flow-step{active}"><span>{index}</span><strong>{label}</strong></div>'
        )
    st.markdown(
        f"""
        <div class="gw-flow" aria-label="Gwittim flow">
          {step_html[0]}
          <div class="gw-flow-line" aria-hidden="true"></div>
          {step_html[1]}
          <div class="gw-flow-line" aria-hidden="true"></div>
          {step_html[2]}
          <div class="gw-meter" aria-hidden="true">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_session_metrics(cue_status):
    st.markdown(
        f"""
        <div class="gw-kpi-grid">
          <div class="gw-kpi">
            <span>문장</span>
            <strong>{len(st.session_state.segments)}</strong>
          </div>
          <div class="gw-kpi">
            <span>최근 귀띔</span>
            <strong>{escape(cue_status)}</strong>
          </div>
          <div class="gw-kpi">
            <span>출력</span>
            <strong>Text</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_paper_metrics(status):
    source_name = st.session_state.paper_source_name or "대기"
    source_chars = st.session_state.paper_source_chars
    section_count = st.session_state.paper_section_count
    match_score = st.session_state.paper_match_score or "대기"
    st.markdown(
        f"""
        <div class="gw-kpi-grid gw-kpi-grid-five">
          <div class="gw-kpi">
            <span>논문</span>
            <strong>{escape(source_name[:24])}</strong>
          </div>
          <div class="gw-kpi">
            <span>추출 텍스트</span>
            <strong>{source_chars:,}</strong>
          </div>
          <div class="gw-kpi">
            <span>감지 섹션</span>
            <strong>{section_count}</strong>
          </div>
          <div class="gw-kpi">
            <span>목적 매칭</span>
            <strong>{escape(match_score)}</strong>
          </div>
          <div class="gw-kpi">
            <span>상태</span>
            <strong>{escape(status)}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_cue(cue_status):
    suggestion = escape(st.session_state.live_reply_suggestion)
    st.markdown(
        f"""
        <div class="gw-live-card">
          <small>Live Cue · {escape(cue_status)}</small>
          <pre>{suggestion}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(settings):
    left, right = st.columns([0.74, 0.26], vertical_alignment="center")
    with left:
        render_brand_mark()
        if settings["active_session"] == "통역 세션":
            st.write("실시간 영어 대화를 한국어 문장 번역으로 따라가는 통역 세션입니다.")
            st.info("Streamlit에서는 실행 입구를 제공하고, 실제 마이크 통역은 로컬 또는 Codespaces 앱에서 엽니다.")
        elif settings["active_session"] == "번역 세션":
            st.write("논문 텍스트나 PDF를 읽고 Abs 요약, 섹터/섹션별 이슈, 결과 처리, 인사이트 발췌, 재검증 체크를 바로 정리하는 번역 세션입니다.")
            st.info("현재 모드: 논문 정리. PDF는 텍스트 추출 후 분석합니다.")
        else:
            st.write("한글 원문을 Nature Reviews Drug Discovery 수준의 과학 영어로 다듬는 텍스트 세션입니다.")
            st.info("현재 모드: 기록 없는 NRDD 수준 한글→영문 영작. 통역 목소리는 출력하지 않습니다.")
    with right:
        if settings["api_key"]:
            st.info("Gemini ready")
        else:
            st.error("API key required")
        st.caption(f"Model: {settings['model']}")
        st.caption(
            settings["active_session"]
            if settings["active_session"] in ["번역 세션", "통역 세션"]
            else APP_MODE
        )

    if settings["active_session"] == "텍스트 세션" and not settings["api_key"]:
        st.warning("왼쪽 사이드바에서 Gemini API key를 한 번 붙여넣고 `API key 한번에 적용`을 눌러주세요.")


def render_live_panel(settings):
    st.subheader("Nature Reviews Drug Discovery 수준 영작")
    st.markdown(
        f"""
        <div class="gw-subtitle-card">
          <strong>{escape(st.session_state.last_translation)}</strong>
          <span>{escape(st.session_state.last_english)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("translate_form", clear_on_submit=True):
        korean_text = st.text_area(
            "한글 원문 입력",
            placeholder="예: 이 후보물질은 전임상 단계에서 선택성과 안전성 측면에서 개선 가능성을 보였다.",
            height=110,
        )
        submitted = st.form_submit_button("NRDD 수준 영어로 영작", type="primary")

    if submitted:
        if not korean_text.strip():
            st.warning("한글 원문을 먼저 입력해주세요.")
        else:
            with st.spinner("영작 중..."):
                try:
                    english = translate(settings, korean_text.strip())
                    try:
                        vocabulary_review = review_vocabulary(
                            settings,
                            korean_text.strip(),
                            english,
                        )
                    except Exception as vocab_exc:
                        vocabulary_review = f"## 어휘 점검\n어휘 점검을 완료하지 못했습니다. 오류: {vocab_exc}"
                    show_current_writing_result(english)
                    st.session_state.last_vocabulary_review = vocabulary_review
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    st.info("영작 기록은 저장하지 않습니다. 입력한 원문은 이전 문맥으로 재사용하지 않고, 현재 결과만 화면에 표시됩니다.")
    st.subheader("어휘 점검 및 재검증")
    st.markdown(st.session_state.last_vocabulary_review)


def render_no_record_panel():
    st.subheader("NRDD 기준")
    st.markdown(
        """
        <div class="gw-session-card">
          <strong>저널 제출 문장에 가까운 영작</strong>
          <p>전문가 독자를 대상으로 하되 인접 분야 연구자도 읽을 수 있게 명확성, 능동태, 간결성, 논리적 연결을 우선합니다.</p>
          <p>영작 후 핵심 어휘의 의미, 뉘앙스, 대체 가능 표현, 인사이트, 재검증 포인트를 함께 점검합니다.</p>
          <p>과장된 novelty, 임상적 의미, 규제 가능성, 기전 설명은 원문 근거가 없으면 추가하지 않습니다.</p>
          <p>gene/protein nomenclature, assay, endpoint, SI unit, INN drug name은 가능한 한 보존합니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("기록 없는 영작")
    st.markdown(
        """
        <div class="gw-session-card">
          <strong>현재 세션 기록 없음</strong>
          <p>영작 결과를 히스토리에 쌓지 않고, 원문을 요약이나 다음 영작 문맥으로 재사용하지 않습니다.</p>
          <p>단, Gemini API 처리를 위해 입력 문장은 요청 순간 외부 API로 전송됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.caption("화면에 남은 현재 결과도 바로 지울 수 있습니다.")
    if st.button("현재 영작 결과 지우기", use_container_width=True):
        st.session_state.last_translation = DEFAULT_WRITING_RESULT
        st.session_state.last_english = DEFAULT_WRITING_SOURCE
        st.session_state.last_vocabulary_review = DEFAULT_VOCABULARY_REVIEW
        st.rerun()


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
    live_enabled = st.toggle("실시간 귀띔", key="auto_compose")
    cue_status = maybe_refresh_live_compose(settings, mode) if live_enabled else "꺼짐"
    render_session_metrics(cue_status)
    render_live_cue(cue_status)

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
        st.session_state.summary = "대화 기록이 쌓이면 핵심 표현이 요약됩니다."
        st.session_state.last_translation = DEFAULT_WRITING_RESULT
        st.session_state.last_english = DEFAULT_WRITING_SOURCE
        st.session_state.last_vocabulary_review = DEFAULT_VOCABULARY_REVIEW
        st.session_state.live_reply_suggestion = (
            "통역 내용이 쌓이면 지금 말할 수 있는 영어 표현을 자동으로 제안합니다."
        )
        st.session_state.live_reply_signature = ""
        st.session_state.reply_suggestion = "추천 영어 답변이 여기에 표시됩니다."
        st.rerun()


def render_text_session(settings):
    st.caption("텍스트 세션은 한글 원문을 Nature Reviews Drug Discovery 수준의 과학 영어로 다듬습니다. 영작 기록은 저장하지 않습니다.")
    active_stage = "compose" if st.session_state.last_translation != DEFAULT_WRITING_RESULT else "translate"
    render_flow_graph(active_stage, flow="writing")
    main_col, side_col = st.columns([0.64, 0.36], gap="large")
    with main_col:
        render_live_panel(settings)
    with side_col:
        render_no_record_panel()


def render_translation_session(settings):
    st.caption("번역 세션은 논문 텍스트나 PDF에서 Abs 요약, 섹터/섹션별 이슈, 결과 처리, 인사이트 발췌, 재검증 체크, 결론을 바로 정리합니다.")
    active_stage = "compose" if st.session_state.paper_source_chars else "translate"
    render_flow_graph(active_stage, flow="paper")
    analysis_ready = bool(
        st.session_state.paper_source_chars
        and st.session_state.paper_analysis != DEFAULT_PAPER_ANALYSIS
    )
    render_paper_metrics("분석 완료" if analysis_ready else "대기")

    input_col, result_col = st.columns([0.44, 0.56], gap="large")
    with input_col:
        st.subheader("논문 추가")
        user_purpose = st.text_area(
            "나의 목적",
            placeholder="예: 이 논문이 내 후보물질의 전임상 독성 평가 전략 수립에 얼마나 직접적으로 도움이 되는지 확인하고 싶습니다.",
            height=96,
        )
        uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"])
        analysis_depth = st.radio(
            "정리 깊이",
            options=["상세", "표준", "빠른"],
            index=0,
            horizontal=True,
        )
        paper_text = st.text_area(
            "논문 텍스트 붙여넣기",
            placeholder="Abstract, Introduction, Results, Discussion, Conclusion 등을 붙여넣으세요.",
            height=180,
        )
        analyze_clicked = st.button("논문 바로 정리", use_container_width=True)

        if analyze_clicked:
            if not settings["api_key"]:
                st.warning("Gemini API key를 먼저 연결해주세요.")
            else:
                try:
                    extracted_pdf_text = extract_pdf_text(uploaded_pdf)
                    combined_text = "\n\n".join(
                        part for part in [extracted_pdf_text, paper_text.strip()] if part
                    )
                    if not combined_text.strip():
                        if uploaded_pdf:
                            st.warning("PDF에서 텍스트를 추출하지 못했습니다. 스캔 PDF라면 논문 텍스트를 직접 붙여넣어주세요.")
                        else:
                            st.warning("PDF를 업로드하거나 논문 텍스트를 붙여넣어주세요.")
                    else:
                        source_name = uploaded_pdf.name if uploaded_pdf else "붙여넣은 논문 텍스트"
                        normalized_text = normalize_paper_text(combined_text)
                        sections = extract_paper_sections(normalized_text)
                        with st.spinner("논문을 정리하는 중..."):
                            analysis = analyze_paper(
                                settings,
                                normalized_text,
                                source_name,
                                analysis_depth,
                                user_purpose,
                            )
                        if not analysis.strip():
                            raise RuntimeError("논문 분석 결과를 받지 못했습니다. 입력 텍스트를 조금 더 길게 넣어 다시 시도해주세요.")
                        st.session_state.paper_source_name = source_name
                        st.session_state.paper_source_chars = len(normalized_text)
                        st.session_state.paper_section_count = len(sections)
                        st.session_state.paper_user_purpose = user_purpose.strip()
                        st.session_state.paper_match_score = extract_purpose_match_score(analysis)
                        st.session_state.paper_extraction_notice = paper_extraction_notice(
                            len(normalized_text),
                            len(sections),
                            bool(uploaded_pdf),
                        )
                        st.session_state.paper_extracted_preview = truncate_text(normalized_text, 2800)
                        st.session_state.paper_analysis = analysis
                        st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        if st.button("논문 세션 지우기", use_container_width=True):
            st.session_state.paper_analysis = DEFAULT_PAPER_ANALYSIS
            st.session_state.paper_source_name = ""
            st.session_state.paper_source_chars = 0
            st.session_state.paper_section_count = 0
            st.session_state.paper_user_purpose = ""
            st.session_state.paper_match_score = ""
            st.session_state.paper_extraction_notice = ""
            st.session_state.paper_extracted_preview = ""
            st.rerun()

    with result_col:
        st.subheader("논문 정리")
        if st.session_state.paper_extraction_notice:
            st.info(st.session_state.paper_extraction_notice)
        st.markdown(st.session_state.paper_analysis)
        if st.session_state.paper_extracted_preview:
            with st.expander("추출 텍스트 미리보기"):
                st.text(st.session_state.paper_extracted_preview)


def render_interpretation_session(settings):
    st.subheader("실시간 통역 세션 열기")
    st.write(
        "실시간 마이크 통역은 작은 Node 서버가 필요합니다. 아래 둘 중 하나로 열 수 있습니다."
    )
    render_flow_graph("listen")
    render_session_metrics("자동 대기")

    local_col, github_col = st.columns(2, gap="large")

    with local_col:
        with st.container(border=True):
            st.markdown("#### 내 Mac에서 열기")
            st.code(
                "\n".join(
                    [
                        "cd /Users/leeyoung-nam/Documents/Translater",
                        "npm run doctor",
                        "npm start",
                    ]
                ),
                language="bash",
            )
            st.link_button("로컬 통역 세션 열기", LOCAL_REALTIME_URL, use_container_width=True)
            st.caption("이미 서버가 켜져 있으면 바로 열립니다. 꺼져 있으면 위 명령을 먼저 실행하세요.")

    with github_col:
        with st.container(border=True):
            st.markdown("#### GitHub Codespaces에서 열기")
            st.write("GitHub 저장소에서 임시 클라우드 개발환경을 만들고, 3000번 포트를 열어 통역 세션에 들어갑니다.")
            st.link_button("Codespaces 안내 보기", GITHUB_CODESPACES_GUIDE_URL, use_container_width=True)
            st.link_button("GitHub 저장소 열기", GITHUB_REPO_URL, use_container_width=True)
            st.caption("Codespaces에는 `GEMINI_API_KEY`를 Codespaces Secret으로 넣어야 합니다.")

    st.divider()
    st.markdown("#### 통역 세션 흐름")
    st.write("1. 통역 앱 열기")
    st.write("2. `통역 시작` 클릭")
    st.write("3. 마이크 권한 허용")
    st.write("4. 영어로 말하면 한국어 문장 번역과 답변 귀띔이 텍스트로 표시")


def main():
    init_state()
    inject_global_styles()
    settings = get_settings()
    render_header(settings)

    if settings["active_session"] == "통역 세션":
        render_interpretation_session(settings)
    elif settings["active_session"] == "번역 세션":
        render_translation_session(settings)
    else:
        render_text_session(settings)


if __name__ == "__main__":
    main()

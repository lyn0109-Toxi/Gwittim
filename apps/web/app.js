const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

const state = {
  recognition: null,
  listening: false,
  selectedMode: "neutral",
  segments: [],
  pendingSummaryAt: 0,
  config: null,
};

const elements = {
  connectionStatus: document.querySelector("#connectionStatus"),
  startButton: document.querySelector("#startButton"),
  stopButton: document.querySelector("#stopButton"),
  confirmStartButton: document.querySelector("#confirmStartButton"),
  consentDialog: document.querySelector("#consentDialog"),
  listeningBadge: document.querySelector("#listeningBadge"),
  koreanSubtitle: document.querySelector("#koreanSubtitle"),
  englishInterim: document.querySelector("#englishInterim"),
  transcriptList: document.querySelector("#transcriptList"),
  summaryBox: document.querySelector("#summaryBox"),
  composeInput: document.querySelector("#composeInput"),
  composeButton: document.querySelector("#composeButton"),
  composeOutput: document.querySelector("#composeOutput"),
  modeButtons: [...document.querySelectorAll(".mode-button")],
  modelName: document.querySelector("#modelName"),
  speechSupport: document.querySelector("#speechSupport"),
  clearButton: document.querySelector("#clearButton"),
};

init();

async function init() {
  bindEvents();
  updateSpeechSupport();
  await loadConfig();
}

function bindEvents() {
  elements.startButton.addEventListener("click", () => {
    if (!SpeechRecognition) {
      showError("이 브라우저에서는 음성 인식을 사용할 수 없습니다.");
      return;
    }
    elements.consentDialog.showModal();
  });

  elements.consentDialog.addEventListener("close", () => {
    if (elements.consentDialog.returnValue === "start") {
      startListening();
    }
  });

  elements.stopButton.addEventListener("click", stopListening);
  elements.composeButton.addEventListener("click", composeResponse);
  elements.clearButton.addEventListener("click", clearSession);

  elements.modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedMode = button.dataset.mode || "neutral";
      elements.modeButtons.forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
    });
  });
}

async function loadConfig() {
  try {
    const config = await requestJson("/api/config");
    state.config = config;
    elements.modelName.textContent = config.model || "-";

    if (config.keyConfigured) {
      setStatus("API 준비됨", "ready");
    } else {
      setStatus("API 키 필요", "error");
      elements.summaryBox.textContent =
        ".env 파일에 OPENAI_API_KEY를 설정하면 번역과 요약이 동작합니다.";
    }
  } catch (error) {
    setStatus("서버 연결 실패", "error");
    elements.summaryBox.textContent = error.message;
  }
}

function updateSpeechSupport() {
  elements.speechSupport.textContent = SpeechRecognition ? "지원됨" : "미지원";
}

function startListening() {
  if (state.listening) {
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    state.listening = true;
    elements.startButton.disabled = true;
    elements.stopButton.disabled = false;
    setListening("듣는 중", "live");
  };

  recognition.onend = () => {
    state.listening = false;
    elements.startButton.disabled = false;
    elements.stopButton.disabled = true;
    setListening("대기", "idle");
  };

  recognition.onerror = (event) => {
    setListening("오류", "error");
    showError(`음성 인식 오류: ${event.error}`);
  };

  recognition.onresult = (event) => {
    let interim = "";
    const finalTexts = [];

    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      const text = result[0]?.transcript?.trim();
      if (!text) {
        continue;
      }

      if (result.isFinal) {
        finalTexts.push(text);
      } else {
        interim += `${text} `;
      }
    }

    if (interim.trim()) {
      elements.englishInterim.textContent = interim.trim();
    }

    finalTexts.forEach((text) => {
      void handleFinalTranscript(text);
    });
  };

  state.recognition = recognition;
  recognition.start();
}

function stopListening() {
  if (state.recognition) {
    state.recognition.stop();
  }
}

async function handleFinalTranscript(english) {
  const segment = {
    id: crypto.randomUUID(),
    at: new Date(),
    english,
    korean: "번역 중...",
  };

  state.segments.push(segment);
  elements.englishInterim.textContent = english;
  elements.koreanSubtitle.textContent = "번역 중...";
  renderTranscript();

  try {
    const result = await requestJson("/api/translate", {
      method: "POST",
      body: JSON.stringify({
        text: english,
        context: state.segments.slice(-8),
      }),
    });

    segment.korean = result.translation || "";
    elements.koreanSubtitle.textContent = segment.korean || "번역 결과가 없습니다.";
    renderTranscript();
    maybeRefreshSummary();
  } catch (error) {
    segment.korean = "번역 실패";
    elements.koreanSubtitle.textContent = error.message;
    renderTranscript();
  }
}

function maybeRefreshSummary() {
  const enoughNewSegments = state.segments.length - state.pendingSummaryAt >= 3;
  const enoughTotalSegments = state.segments.length >= 3;

  if (!enoughNewSegments || !enoughTotalSegments) {
    return;
  }

  state.pendingSummaryAt = state.segments.length;
  void refreshSummary();
}

async function refreshSummary() {
  elements.summaryBox.textContent = "요약 갱신 중...";

  try {
    const result = await requestJson("/api/summarize", {
      method: "POST",
      body: JSON.stringify({ segments: state.segments }),
    });
    elements.summaryBox.textContent = result.summary || "요약 결과가 없습니다.";
  } catch (error) {
    elements.summaryBox.textContent = error.message;
  }
}

async function composeResponse() {
  const text = elements.composeInput.value.trim();
  if (!text) {
    elements.composeOutput.textContent = "한국어 문장을 먼저 입력해주세요.";
    return;
  }

  elements.composeButton.disabled = true;
  elements.composeOutput.textContent = "답변 생성 중...";

  try {
    const result = await requestJson("/api/compose", {
      method: "POST",
      body: JSON.stringify({
        text,
        mode: state.selectedMode,
        context: state.segments.slice(-8),
      }),
    });
    elements.composeOutput.textContent = result.suggestion || "추천 문장이 없습니다.";
  } catch (error) {
    elements.composeOutput.textContent = error.message;
  } finally {
    elements.composeButton.disabled = false;
  }
}

function renderTranscript() {
  const items = state.segments
    .slice()
    .reverse()
    .map((segment) => {
      const time = segment.at.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });

      return `
        <article class="transcript-item">
          <time class="transcript-time">${escapeHtml(time)}</time>
          <div class="transcript-text">
            <p class="transcript-ko">${escapeHtml(segment.korean)}</p>
            <p class="transcript-en">${escapeHtml(segment.english)}</p>
          </div>
        </article>
      `;
    })
    .join("");

  elements.transcriptList.innerHTML = items;
}

function clearSession() {
  state.segments = [];
  state.pendingSummaryAt = 0;
  elements.koreanSubtitle.textContent = "세션을 지웠습니다.";
  elements.englishInterim.textContent = "새 대화를 시작할 수 있습니다.";
  elements.summaryBox.textContent = "대화가 쌓이면 요약이 갱신됩니다.";
  elements.composeOutput.textContent = "추천 문장이 여기에 표시됩니다.";
  renderTranscript();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || data.error || `요청 실패: ${response.status}`);
  }

  return data;
}

function setStatus(text, tone) {
  elements.connectionStatus.textContent = text;
  elements.connectionStatus.classList.toggle("is-ready", tone === "ready");
  elements.connectionStatus.classList.toggle("is-error", tone === "error");
}

function setListening(text, tone) {
  elements.listeningBadge.textContent = text;
  elements.listeningBadge.classList.toggle("is-live", tone === "live");
  elements.listeningBadge.classList.toggle("is-error", tone === "error");
}

function showError(message) {
  elements.koreanSubtitle.textContent = message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

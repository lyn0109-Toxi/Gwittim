const INPUT_SAMPLE_RATE = 16000;
const INPUT_MIME_TYPE = `audio/pcm;rate=${INPUT_SAMPLE_RATE}`;

const state = {
  socket: null,
  localStream: null,
  audioContext: null,
  inputSource: null,
  inputProcessor: null,
  socketClosedByUser: false,
  listening: false,
  selectedMode: "neutral",
  segments: [],
  pendingSummaryAt: 0,
  config: null,
  activeInputTranscript: "",
  activeOutputTranscript: "",
  finalizeTimer: null,
  lastFinalizedKorean: "",
};

const elements = {
  connectionStatus: document.querySelector("#connectionStatus"),
  startButton: document.querySelector("#startButton"),
  stopButton: document.querySelector("#stopButton"),
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
  updateRuntimeSupport();
  await loadConfig();
}

function bindEvents() {
  elements.startButton.addEventListener("click", () => {
    if (!canUseRealtime()) {
      showError("이 브라우저에서는 실시간 마이크 통역을 사용할 수 없습니다.");
      return;
    }
    elements.consentDialog.showModal();
  });

  elements.consentDialog.addEventListener("close", () => {
    if (elements.consentDialog.returnValue === "start") {
      void startRealtimeInterpretation();
    }
  });

  elements.stopButton.addEventListener("click", () => {
    stopRealtimeInterpretation();
  });
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
    elements.modelName.textContent =
      config.geminiLiveModel || config.realtimeModel || config.model || "-";

    if (config.keyConfigured) {
      setStatus("통역 준비됨", "ready");
    } else {
      setStatus("Gemini API 키 필요", "error");
      elements.summaryBox.textContent =
        ".env 파일에 GEMINI_API_KEY를 설정하면 실시간 통역이 동작합니다.";
    }
  } catch (error) {
    setStatus("서버 연결 실패", "error");
    elements.summaryBox.textContent = error.message;
  }
}

function updateRuntimeSupport() {
  elements.speechSupport.textContent = canUseRealtime()
    ? "Gemini Live 텍스트"
    : "미지원";
}

function canUseRealtime() {
  return Boolean(
    navigator.mediaDevices?.getUserMedia &&
      window.WebSocket &&
      (window.AudioContext || window.webkitAudioContext),
  );
}

async function startRealtimeInterpretation() {
  if (state.listening) {
    return;
  }

  if (!state.config?.keyConfigured) {
    showError("GEMINI_API_KEY를 먼저 설정해주세요.");
    return;
  }

  resetRealtimeState();
  setListening("마이크 준비", "live");
  setStatus("연결 중", "ready");
  elements.startButton.disabled = true;
  elements.stopButton.disabled = false;
  elements.koreanSubtitle.textContent = "영어로 말하면 한국어 통역이 여기에 표시됩니다.";
  elements.englishInterim.textContent = "마이크 권한을 확인하고 있습니다.";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    state.localStream = stream;

    const session = await requestJson("/api/gemini/live-token", {
      method: "POST",
      body: JSON.stringify({
        targetLanguage: state.config.translationTarget || "ko",
      }),
    });

    if (!session.token || !session.webSocketEndpoint || !session.setup) {
      throw new Error("Gemini 실시간 통역 세션 키를 받지 못했습니다.");
    }

    const audioContext = createAudioContext();
    state.audioContext = audioContext;
    await audioContext.resume();

    const socket = new WebSocket(createGeminiWebSocketUrl(session));
    state.socket = socket;
    state.socketClosedByUser = false;

    socket.addEventListener("message", (event) => {
      void handleGeminiMessage(event.data);
    });
    socket.addEventListener("error", () => {
      if (!state.socketClosedByUser) {
        setStatus("통역 오류", "error");
        showError("Gemini Live 연결 중 오류가 발생했습니다.");
      }
    });
    socket.addEventListener("close", (event) => {
      const wasListening = state.listening;
      const closedByUser = state.socketClosedByUser;
      stopRealtimeInterpretation({ fromSocketClose: true });

      if (wasListening && !closedByUser) {
        setStatus("연결 종료", "error");
        const reason = event.reason ? ` ${event.reason}` : "";
        showError(`Gemini Live 연결이 종료되었습니다.${reason}`);
      }
    });

    await waitForSocketOpen(socket, session.setup);

    state.listening = true;
    startMicrophoneStreaming(stream);
    setStatus("실시간 연결됨", "ready");
    setListening("듣는 중", "live");
    elements.englishInterim.textContent =
      "말하는 동안 영어 전사와 한국어 통역이 표시됩니다.";
  } catch (error) {
    stopRealtimeInterpretation();
    setStatus("연결 실패", "error");
    setListening("오류", "error");
    showError(formatRealtimeStartError(error));
  }
}

function stopRealtimeInterpretation(options = {}) {
  const socket = state.socket;
  state.listening = false;
  state.socketClosedByUser = true;

  if (!options.fromSocketClose && socket && socket.readyState < WebSocket.CLOSING) {
    if (socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify({ realtimeInput: { audioStreamEnd: true } }));
      } catch {
        // The socket may already be closing; cleanup below still handles local state.
      }
    }
    socket.close();
  }

  stopMicrophoneStreaming();

  if (state.localStream) {
    state.localStream.getTracks().forEach((track) => track.stop());
  }

  if (state.audioContext && state.audioContext.state !== "closed") {
    void state.audioContext.close().catch(() => {});
  }

  state.socket = null;
  state.localStream = null;
  state.audioContext = null;
  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  clearFinalizeTimer();
  elements.startButton.disabled = false;
  elements.stopButton.disabled = true;
  setListening("대기", "idle");

  if (state.config?.keyConfigured && !options.fromSocketClose) {
    setStatus("통역 준비됨", "ready");
  }
}

function resetRealtimeState() {
  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  state.lastFinalizedKorean = "";
  clearFinalizeTimer();
}

function createAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  return new AudioContextClass();
}

function createGeminiWebSocketUrl(session) {
  return `${session.webSocketEndpoint}?access_token=${encodeURIComponent(
    session.token,
  )}`;
}

function waitForSocketOpen(socket, setup) {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      reject(new Error("Gemini Live 연결 시간이 초과되었습니다."));
    }, 12000);

    socket.addEventListener(
      "open",
      () => {
        window.clearTimeout(timeout);
        socket.send(JSON.stringify(setup));
        resolve();
      },
      { once: true },
    );

    socket.addEventListener(
      "error",
      () => {
        window.clearTimeout(timeout);
        reject(new Error("Gemini Live 연결을 열지 못했습니다."));
      },
      { once: true },
    );

    socket.addEventListener(
      "close",
      () => {
        window.clearTimeout(timeout);
        reject(new Error("Gemini Live 연결이 시작 전에 닫혔습니다."));
      },
      { once: true },
    );
  });
}

function startMicrophoneStreaming(stream) {
  const audioContext = state.audioContext;
  const socket = state.socket;

  if (!audioContext || !socket) {
    return;
  }

  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  processor.onaudioprocess = (event) => {
    const output = event.outputBuffer.getChannelData(0);
    output.fill(0);

    if (!state.listening || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    const input = event.inputBuffer.getChannelData(0);
    const pcmBuffer = resampleFloat32ToPCM16(
      input,
      audioContext.sampleRate,
      INPUT_SAMPLE_RATE,
    );

    if (pcmBuffer.byteLength > 0) {
      sendGeminiAudio(pcmBuffer);
    }
  };

  source.connect(processor);
  processor.connect(audioContext.destination);
  state.inputSource = source;
  state.inputProcessor = processor;
}

function stopMicrophoneStreaming() {
  if (state.inputProcessor) {
    state.inputProcessor.onaudioprocess = null;
    state.inputProcessor.disconnect();
  }

  if (state.inputSource) {
    state.inputSource.disconnect();
  }

  state.inputProcessor = null;
  state.inputSource = null;
}

function sendGeminiAudio(arrayBuffer) {
  const socket = state.socket;
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    return;
  }

  socket.send(
    JSON.stringify({
      realtimeInput: {
        audio: {
          data: arrayBufferToBase64(arrayBuffer),
          mimeType: INPUT_MIME_TYPE,
        },
      },
    }),
  );
}

async function handleGeminiMessage(rawData) {
  const rawText = typeof rawData === "string" ? rawData : await rawData.text();
  let message;

  try {
    message = JSON.parse(rawText);
  } catch {
    return;
  }

  if (message.error) {
    const errorMessage =
      message.error.message || "Gemini Live 통역 중 오류가 발생했습니다.";
    setStatus("통역 오류", "error");
    showError(errorMessage);
    return;
  }

  if (message.setupComplete) {
    setStatus("통역 세션 준비됨", "ready");
  }

  if (message.goAway?.timeLeft) {
    setStatus("세션 만료 예정", "error");
  }

  const serverContent = message.serverContent;
  if (!serverContent) {
    return;
  }

  if (serverContent.interrupted) {
    clearFinalizeTimer();
  }

  const inputText = serverContent.inputTranscription?.text;
  if (inputText) {
    state.activeInputTranscript = mergeTranscript(
      state.activeInputTranscript,
      inputText,
    );
    elements.englishInterim.textContent =
      state.activeInputTranscript || "음성을 인식하는 중...";
  }

  const outputText = serverContent.outputTranscription?.text;
  if (outputText) {
    state.activeOutputTranscript = mergeTranscript(
      state.activeOutputTranscript,
      outputText,
    );
    elements.koreanSubtitle.textContent =
      state.activeOutputTranscript || "통역 중...";
    scheduleRealtimeSegmentFinalize();
  }

  const textParts = (serverContent.modelTurn?.parts || [])
    .map((part) => part.text)
    .filter(Boolean)
    .join("");

  if (textParts) {
    state.activeOutputTranscript = mergeTranscript(
      state.activeOutputTranscript,
      textParts,
    );
    elements.koreanSubtitle.textContent =
      state.activeOutputTranscript || "통역 중...";
    scheduleRealtimeSegmentFinalize();
  }

  if (serverContent.turnComplete) {
    clearFinalizeTimer();
    finalizeRealtimeSegment(state.activeOutputTranscript);
  }
}

function mergeTranscript(current, incoming) {
  const text = String(incoming || "");
  if (!text) {
    return current;
  }
  if (!current) {
    return text;
  }
  if (text.startsWith(current)) {
    return text;
  }
  if (current.endsWith(text)) {
    return current;
  }
  return `${current}${text}`;
}

function finalizeRealtimeSegment(text) {
  const korean = (text || state.activeOutputTranscript).trim();
  const english = state.activeInputTranscript.trim() || "음성 인식 중";

  if (!korean) {
    return;
  }

  if (korean === state.lastFinalizedKorean) {
    state.activeInputTranscript = "";
    state.activeOutputTranscript = "";
    clearFinalizeTimer();
    return;
  }

  const segment = {
    id: createId(),
    at: new Date(),
    english,
    korean,
  };

  state.segments.push(segment);
  elements.koreanSubtitle.textContent = korean;
  elements.englishInterim.textContent = english;
  renderTranscript();
  maybeRefreshSummary();

  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  state.lastFinalizedKorean = korean;
  clearFinalizeTimer();
}

function scheduleRealtimeSegmentFinalize() {
  clearFinalizeTimer();
  state.finalizeTimer = window.setTimeout(() => {
    finalizeRealtimeSegment(state.activeOutputTranscript);
  }, 1100);
}

function clearFinalizeTimer() {
  if (state.finalizeTimer) {
    window.clearTimeout(state.finalizeTimer);
    state.finalizeTimer = null;
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
  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  state.lastFinalizedKorean = "";
  clearFinalizeTimer();
  elements.koreanSubtitle.textContent = "세션을 지웠습니다.";
  elements.englishInterim.textContent = "새 통역을 시작할 수 있습니다.";
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

function resampleFloat32ToPCM16(input, inputSampleRate, outputSampleRate) {
  if (!input.length) {
    return new ArrayBuffer(0);
  }

  const ratio = inputSampleRate / outputSampleRate;
  const outputLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Int16Array(outputLength);

  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(input.length, Math.floor((index + 1) * ratio));
    let total = 0;
    let count = 0;

    for (let sampleIndex = start; sampleIndex < end; sampleIndex += 1) {
      total += input[sampleIndex];
      count += 1;
    }

    const sample = clamp(count > 0 ? total / count : input[start] || 0, -1, 1);
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }

  return output.buffer;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;

  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return btoa(binary);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function createId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
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

function formatRealtimeStartError(error) {
  const name = error?.name || "";
  const message = error?.message || "실시간 통역을 시작하지 못했습니다.";

  if (name === "NotAllowedError" || name === "SecurityError") {
    return [
      "마이크 권한이 차단되었습니다.",
      "Chrome 주소창 왼쪽의 사이트 설정에서 마이크를 허용하거나, macOS 시스템 설정 > 개인정보 보호 및 보안 > 마이크에서 Chrome을 허용해주세요.",
    ].join(" ");
  }

  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "사용 가능한 마이크를 찾지 못했습니다. 마이크 연결을 확인한 뒤 다시 시작해주세요.";
  }

  if (name === "NotReadableError" || name === "TrackStartError") {
    return "마이크를 열 수 없습니다. 다른 앱이 마이크를 사용 중이면 종료한 뒤 다시 시도해주세요.";
  }

  return message;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

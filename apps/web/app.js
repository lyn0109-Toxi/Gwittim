const state = {
  peerConnection: null,
  dataChannel: null,
  localStream: null,
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
  translatedAudio: document.querySelector("#translatedAudio"),
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

  elements.stopButton.addEventListener("click", stopRealtimeInterpretation);
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
    elements.modelName.textContent = config.realtimeModel || config.model || "-";

    if (config.keyConfigured) {
      setStatus("통역 준비됨", "ready");
    } else {
      setStatus("API 키 필요", "error");
      elements.summaryBox.textContent =
        ".env 파일에 OPENAI_API_KEY를 설정하면 실시간 통역이 동작합니다.";
    }
  } catch (error) {
    setStatus("서버 연결 실패", "error");
    elements.summaryBox.textContent = error.message;
  }
}

function updateRuntimeSupport() {
  elements.speechSupport.textContent = canUseRealtime() ? "WebRTC 통역" : "미지원";
}

function canUseRealtime() {
  return Boolean(
    navigator.mediaDevices?.getUserMedia &&
      window.RTCPeerConnection &&
      window.RTCSessionDescription,
  );
}

async function startRealtimeInterpretation() {
  if (state.listening) {
    return;
  }

  if (!state.config?.keyConfigured) {
    showError("OPENAI_API_KEY를 먼저 설정해주세요.");
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

    const peerConnection = new RTCPeerConnection();
    const dataChannel = peerConnection.createDataChannel("oai-events");

    peerConnection.addEventListener("track", (event) => {
      const [remoteStream] = event.streams;
      if (remoteStream) {
        elements.translatedAudio.srcObject = remoteStream;
        void elements.translatedAudio.play().catch(() => {});
      }
    });

    stream.getAudioTracks().forEach((track) => {
      peerConnection.addTrack(track, stream);
    });

    dataChannel.addEventListener("open", () => {
      state.listening = true;
      setStatus("실시간 연결됨", "ready");
      setListening("듣는 중", "live");
      elements.englishInterim.textContent = "말하는 동안 영어 전사와 한국어 통역이 표시됩니다.";
    });

    dataChannel.addEventListener("message", (event) => {
      handleRealtimeEvent(event.data);
    });

    dataChannel.addEventListener("close", () => {
      if (state.listening) {
        stopRealtimeInterpretation();
      }
    });

    peerConnection.addEventListener("connectionstatechange", () => {
      if (["failed", "disconnected", "closed"].includes(peerConnection.connectionState)) {
        if (state.listening) {
          stopRealtimeInterpretation();
        }
      }
    });

    state.peerConnection = peerConnection;
    state.dataChannel = dataChannel;
    state.localStream = stream;

    const session = await requestJson("/api/realtime/translation-session", {
      method: "POST",
      body: JSON.stringify({ targetLanguage: state.config.translationTarget || "ko" }),
    });

    if (!session.client_secret) {
      throw new Error("실시간 통역 세션 키를 받지 못했습니다.");
    }

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    const sdpResponse = await fetch(
      "https://api.openai.com/v1/realtime/translations/calls",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.client_secret}`,
          "Content-Type": "application/sdp",
        },
        body: offer.sdp,
      },
    );

    if (!sdpResponse.ok) {
      throw new Error(await readOpenAIRealtimeError(sdpResponse));
    }

    await peerConnection.setRemoteDescription({
      type: "answer",
      sdp: await sdpResponse.text(),
    });
  } catch (error) {
    stopRealtimeInterpretation();
    setStatus("연결 실패", "error");
    setListening("오류", "error");
    showError(error.message);
  }
}

function stopRealtimeInterpretation() {
  state.listening = false;

  if (state.dataChannel && state.dataChannel.readyState === "open") {
    state.dataChannel.close();
  }

  if (state.peerConnection) {
    state.peerConnection.close();
  }

  if (state.localStream) {
    state.localStream.getTracks().forEach((track) => track.stop());
  }

  state.dataChannel = null;
  state.peerConnection = null;
  state.localStream = null;
  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  clearFinalizeTimer();
  elements.translatedAudio.srcObject = null;
  elements.startButton.disabled = false;
  elements.stopButton.disabled = true;
  setListening("대기", "idle");

  if (state.config?.keyConfigured) {
    setStatus("통역 준비됨", "ready");
  }
}

function resetRealtimeState() {
  state.activeInputTranscript = "";
  state.activeOutputTranscript = "";
  clearFinalizeTimer();
}

function handleRealtimeEvent(rawData) {
  let event;
  try {
    event = JSON.parse(rawData);
  } catch {
    return;
  }

  if (event.type === "error") {
    const message = event.error?.message || "실시간 통역 중 오류가 발생했습니다.";
    setStatus("통역 오류", "error");
    showError(message);
    return;
  }

  if (event.type === "session.input_transcript.delta") {
    state.activeInputTranscript += event.delta || "";
    elements.englishInterim.textContent =
      state.activeInputTranscript || "음성을 인식하는 중...";
    return;
  }

  if (event.type === "session.output_transcript.delta") {
    state.activeOutputTranscript += event.delta || "";
    elements.koreanSubtitle.textContent = state.activeOutputTranscript || "통역 중...";
    scheduleRealtimeSegmentFinalize();
    return;
  }

  if (event.type === "session.input_transcript.done" && event.transcript) {
    state.activeInputTranscript = event.transcript;
    elements.englishInterim.textContent = event.transcript;
    return;
  }

  if (event.type === "session.output_transcript.done") {
    clearFinalizeTimer();
    finalizeRealtimeSegment(event.transcript || state.activeOutputTranscript);
    return;
  }

  if (event.type === "session.updated") {
    setStatus("통역 세션 준비됨", "ready");
  }
}

function finalizeRealtimeSegment(text) {
  const korean = (text || state.activeOutputTranscript).trim();
  const english = state.activeInputTranscript.trim() || "음성 인식 중";

  if (!korean || korean === state.lastFinalizedKorean) {
    return;
  }

  const segment = {
    id: crypto.randomUUID(),
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
  }, 900);
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

async function readOpenAIRealtimeError(response) {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    return data?.error?.message || data?.message || `통역 연결 실패: ${response.status}`;
  } catch {
    return text || `통역 연결 실패: ${response.status}`;
  }
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

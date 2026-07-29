import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "../..");
const webRoot = path.join(repoRoot, "apps/web");

loadDotEnv(path.join(repoRoot, ".env"));

const config = {
  host: process.env.HOST || "127.0.0.1",
  port: Number(process.env.PORT || 3000),
  apiVersion: process.env.GEMINI_API_VERSION || "v1beta",
  geminiApiKey: process.env.GEMINI_API_KEY || "",
  geminiLiveModel:
    process.env.GEMINI_LIVE_MODEL || "gemini-3.5-live-translate-preview",
  geminiTextModel: process.env.GEMINI_TEXT_MODEL || "gemini-3.6-flash",
  translationTarget: process.env.GEMINI_TRANSLATION_TARGET || "ko",
  echoTargetLanguage: parseBoolean(process.env.GEMINI_ECHO_TARGET_LANGUAGE, false),
};

const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".ico", "image/x-icon"],
]);

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url || "/", `http://${request.headers.host}`);

    if (request.method === "GET" && url.pathname === "/api/config") {
      return sendJson(response, 200, {
        provider: "gemini",
        keyConfigured: Boolean(config.geminiApiKey),
        apiVersion: config.apiVersion,
        geminiLiveModel: modelId(config.geminiLiveModel),
        geminiTextModel: modelId(config.geminiTextModel),
        translationTarget: config.translationTarget,
        echoTargetLanguage: config.echoTargetLanguage,
        inputSampleRate: 16000,
        outputSampleRate: 24000,
      });
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return sendJson(response, 200, { ok: true });
    }

    if (request.method === "POST" && url.pathname === "/api/translate") {
      return await handleTranslate(request, response);
    }

    if (request.method === "POST" && url.pathname === "/api/summarize") {
      return await handleSummarize(request, response);
    }

    if (request.method === "POST" && url.pathname === "/api/compose") {
      return await handleCompose(request, response);
    }

    if (request.method === "POST" && url.pathname === "/api/gemini/live-token") {
      return await handleGeminiLiveToken(request, response);
    }

    if (request.method === "GET") {
      return serveStatic(url.pathname, response);
    }

    sendJson(response, 405, { error: "Method not allowed" });
  } catch (error) {
    console.error(error);
    const statusCode = Number(error?.statusCode || 500);
    sendJson(response, statusCode, {
      error: "Unexpected server error",
      detail: error instanceof Error ? error.message : String(error),
    });
  }
});

server.listen(config.port, config.host, () => {
  console.log(`Gwittim is running at http://${config.host}:${config.port}`);
});

async function handleTranslate(request, response) {
  const body = await readJson(request);
  const text = cleanInput(body.text);
  const context = Array.isArray(body.context) ? body.context.slice(-6) : [];

  if (!text) {
    return sendJson(response, 400, { error: "Text is required" });
  }

  const contextText = context
    .map((item) => `EN: ${item.english || ""}\nKO: ${item.korean || ""}`)
    .join("\n\n");

  const translated = await callGemini({
    systemInstruction: [
      "You are Gwittim, a quiet realtime English-to-Korean conversation assistant.",
      "Translate live English speech into natural Korean subtitles.",
      "Return only Korean text.",
      "Keep names, product names, technical terms, dates, and numbers precise.",
      "If the sentence is fragmentary, translate the intended meaning briefly without adding facts.",
    ].join(" "),
    input: [
      contextText ? `Recent context:\n${contextText}` : "",
      `Current English utterance:\n${text}`,
    ]
      .filter(Boolean)
      .join("\n\n"),
    maxOutputTokens: 220,
  });

  sendJson(response, 200, { translation: translated.trim() });
}

async function handleGeminiLiveToken(request, response) {
  const body = await readJson(request);
  const targetLanguage = cleanInput(body.targetLanguage || config.translationTarget);
  const echoTargetLanguage =
    typeof body.echoTargetLanguage === "boolean"
      ? body.echoTargetLanguage
      : config.echoTargetLanguage;

  if (!config.geminiApiKey) {
    return sendJson(response, 503, {
      error: "GEMINI_API_KEY is not configured",
    });
  }

  if (!isSafeLanguageCode(targetLanguage)) {
    return sendJson(response, 400, {
      error: `Unsupported translation target: ${targetLanguage}`,
    });
  }

  const setup = createLiveTranslationSetup({
    targetLanguage,
    echoTargetLanguage,
  });
  const expireTime = new Date(Date.now() + 30 * 60 * 1000).toISOString();
  const newSessionExpireTime = new Date(Date.now() + 60 * 1000).toISOString();

  const geminiResponse = await fetch(
    `https://generativelanguage.googleapis.com/${config.apiVersion}/auth_tokens`,
    {
      method: "POST",
      headers: {
        "x-goog-api-key": config.geminiApiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        uses: 1,
        expireTime,
        newSessionExpireTime,
      }),
    },
  );

  const { data, rawText } = await readResponse(geminiResponse);

  if (!geminiResponse.ok) {
    const error = new Error(parseGeminiError(data, rawText, geminiResponse.status));
    error.statusCode = geminiResponse.status;
    throw error;
  }

  const token = extractGeminiToken(data);
  if (!token) {
    const error = new Error("Gemini did not return an ephemeral Live API token");
    error.statusCode = 502;
    throw error;
  }

  sendJson(response, 200, {
    token,
    setup,
    targetLanguage,
    echoTargetLanguage,
    expireTime,
    newSessionExpireTime,
    webSocketEndpoint:
      "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained",
  });
}

async function handleSummarize(request, response) {
  const body = await readJson(request);
  const segments = Array.isArray(body.segments) ? body.segments.slice(-24) : [];

  if (segments.length === 0) {
    return sendJson(response, 400, { error: "Segments are required" });
  }

  const transcript = segments
    .map((item, index) => {
      const english = cleanInput(item.english);
      const korean = cleanInput(item.korean);
      return `${index + 1}. EN: ${english}\n   KO: ${korean}`;
    })
    .join("\n");

  const summary = await callGemini({
    systemInstruction: [
      "You are Gwittim, a realtime meeting brief assistant.",
      "Summarize the current conversation in Korean for a user who is listening live.",
      "Keep it short, concrete, and useful while the conversation is still happening.",
      "Use compact bullets. Include decisions and action items only if they are present.",
    ].join(" "),
    input: transcript,
    maxOutputTokens: 360,
  });

  sendJson(response, 200, { summary: summary.trim() });
}

async function handleCompose(request, response) {
  const body = await readJson(request);
  const text = cleanInput(body.text);
  const mode = cleanInput(body.mode || "neutral");
  const context = Array.isArray(body.context) ? body.context.slice(-8) : [];

  if (!text) {
    return sendJson(response, 400, { error: "Text is required" });
  }

  const contextText = context
    .map((item) => `EN: ${item.english || ""}\nKO: ${item.korean || ""}`)
    .join("\n\n");

  const suggestion = await callGemini({
    systemInstruction: [
      "You are Gwittim, helping a Korean speaker respond naturally in an English conversation.",
      "Convert the user's Korean draft into concise, spoken English.",
      "Match the requested response mode.",
      "Return two options: one short direct version and one slightly warmer professional version.",
      "Do not add unsupported facts.",
    ].join(" "),
    input: [
      contextText ? `Recent conversation context:\n${contextText}` : "",
      `Response mode: ${mode}`,
      `Korean draft:\n${text}`,
    ]
      .filter(Boolean)
      .join("\n\n"),
    maxOutputTokens: 420,
  });

  sendJson(response, 200, { suggestion: suggestion.trim() });
}

async function callGemini({ systemInstruction, input, maxOutputTokens }) {
  if (!config.geminiApiKey) {
    const error = new Error("GEMINI_API_KEY is not configured");
    error.statusCode = 503;
    throw error;
  }

  const modelName = normalizeModelName(config.geminiTextModel);
  const geminiResponse = await fetch(
    `https://generativelanguage.googleapis.com/${config.apiVersion}/${modelName}:generateContent`,
    {
      method: "POST",
      headers: {
        "x-goog-api-key": config.geminiApiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        systemInstruction: {
          parts: [{ text: systemInstruction }],
        },
        contents: [
          {
            role: "user",
            parts: [{ text: input }],
          },
        ],
        generationConfig: {
          maxOutputTokens,
          temperature: 0.25,
        },
      }),
    },
  );

  const { data, rawText } = await readResponse(geminiResponse);

  if (!geminiResponse.ok) {
    const error = new Error(parseGeminiError(data, rawText, geminiResponse.status));
    error.statusCode = geminiResponse.status;
    throw error;
  }

  const text = extractGeminiText(data);
  if (!text) {
    throw new Error("Gemini returned no text output");
  }

  return text;
}

function createLiveTranslationSetup({ targetLanguage, echoTargetLanguage }) {
  return {
    setup: {
      model: normalizeModelName(config.geminiLiveModel),
      generationConfig: {
        responseModalities: ["AUDIO"],
        translationConfig: {
          targetLanguageCode: targetLanguage,
          echoTargetLanguage,
        },
      },
      inputAudioTranscription: {},
      outputAudioTranscription: {},
    },
  };
}

function extractGeminiToken(data) {
  if (typeof data?.name === "string") {
    return data.name;
  }
  if (typeof data?.token === "string") {
    return data.token;
  }
  if (typeof data?.token?.name === "string") {
    return data.token.name;
  }
  if (typeof data?.value === "string") {
    return data.value;
  }
  return "";
}

function extractGeminiText(data) {
  const parts = [];
  for (const candidate of data?.candidates || []) {
    for (const part of candidate?.content?.parts || []) {
      if (typeof part?.text === "string") {
        parts.push(part.text);
      }
    }
  }
  return parts.join("\n").trim();
}

function parseGeminiError(data, rawText, statusCode) {
  return (
    data?.error?.message ||
    data?.message ||
    rawText ||
    `Gemini request failed with status ${statusCode}`
  );
}

async function readResponse(response) {
  const rawText = await response.text();
  if (!rawText) {
    return { data: {}, rawText: "" };
  }

  try {
    return { data: JSON.parse(rawText), rawText };
  } catch {
    return { data: {}, rawText };
  }
}

function normalizeModelName(model) {
  const value = modelId(model);
  return `models/${value}`;
}

function modelId(model) {
  return cleanInput(model).replace(/^models\//, "");
}

function isSafeLanguageCode(language) {
  return /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(language);
}

function parseBoolean(value, fallback) {
  if (value === undefined) {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(String(value).trim().toLowerCase());
}

async function serveStatic(urlPath, response) {
  const safePath = urlPath === "/" ? "/index.html" : urlPath;
  const decodedPath = decodeURIComponent(safePath);
  const requested = path.normalize(decodedPath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(webRoot, requested);

  if (!filePath.startsWith(webRoot)) {
    return sendText(response, 403, "Forbidden");
  }

  try {
    const content = await readFile(filePath);
    const extension = path.extname(filePath);
    response.writeHead(200, {
      "Content-Type": mimeTypes.get(extension) || "application/octet-stream",
      "Cache-Control": "no-store",
    });
    response.end(content);
  } catch {
    const fallback = path.join(webRoot, "index.html");
    const content = await readFile(fallback);
    response.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    });
    response.end(content);
  }
}

function loadDotEnv(envPath) {
  if (!existsSync(envPath)) {
    return;
  }

  const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }

    const separator = trimmed.indexOf("=");
    const key = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim().replace(/^["']|["']$/g, "");

    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

function cleanInput(value) {
  return typeof value === "string" ? value.trim() : "";
}

function readJson(request) {
  return new Promise((resolve, reject) => {
    let raw = "";
    request.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) {
        request.destroy(new Error("Request body is too large"));
      }
    });
    request.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch (error) {
        reject(error);
      }
    });
    request.on("error", reject);
  });
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(JSON.stringify(payload));
}

function sendText(response, statusCode, text) {
  response.writeHead(statusCode, {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(text);
}

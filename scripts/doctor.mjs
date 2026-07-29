import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(__filename), "..");

const checks = [];

await checkNodeVersion();
await checkFile("apps/api/server.mjs");
await checkFile("apps/web/index.html");
await checkFile("apps/web/app.js");
await checkFile("apps/web/styles.css");
await checkEnv();

const failed = checks.filter((check) => !check.ok);
for (const check of checks) {
  console.log(`${check.ok ? "OK" : "MISSING"} ${check.message}`);
}

if (failed.length > 0) {
  console.log("");
  console.log("Run `npm run setup`, then add GEMINI_API_KEY to .env.");
  process.exit(1);
}

console.log("");
console.log("Gwittim is ready to run with `npm start`.");

async function checkNodeVersion() {
  const major = Number(process.versions.node.split(".")[0]);
  checks.push({
    ok: major >= 20,
    message: `Node.js ${process.versions.node} detected; Node 20 or newer is required.`,
  });
}

async function checkFile(relativePath) {
  try {
    await access(path.join(repoRoot, relativePath));
    checks.push({ ok: true, message: `${relativePath} exists.` });
  } catch {
    checks.push({ ok: false, message: `${relativePath} is missing.` });
  }
}

async function checkEnv() {
  const envPath = path.join(repoRoot, ".env");

  try {
    const envText = await readFile(envPath, "utf8");
    checks.push({ ok: true, message: ".env exists." });

    const settings = parseEnv(envText);
    const apiKey = settings.GEMINI_API_KEY || "";
    checks.push({
      ok: Boolean(apiKey && !apiKey.includes("your_api_key_here")),
      message: "GEMINI_API_KEY is set in .env.",
    });
    checks.push({
      ok: settings.GEMINI_LIVE_MODEL === "gemini-3.5-live-translate-preview",
      message: "GEMINI_LIVE_MODEL is gemini-3.5-live-translate-preview.",
    });
    checks.push({
      ok: settings.GEMINI_TEXT_MODEL === "gemini-3.6-flash",
      message: "GEMINI_TEXT_MODEL is gemini-3.6-flash.",
    });
    checks.push({
      ok: settings.GEMINI_TRANSLATION_TARGET === "ko",
      message: "GEMINI_TRANSLATION_TARGET is ko.",
    });
    checks.push({
      ok: settings.GEMINI_API_VERSION === "v1beta",
      message: "GEMINI_API_VERSION is v1beta.",
    });
  } catch {
    checks.push({ ok: false, message: ".env is missing." });
  }
}

function parseEnv(text) {
  const values = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const separator = trimmed.indexOf("=");
    const key = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim().replace(/^["']|["']$/g, "");
    values[key] = value;
  }
  return values;
}

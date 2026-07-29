import { copyFile, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(__filename), "..");
const envPath = path.join(repoRoot, ".env");
const examplePath = path.join(repoRoot, ".env.example");

try {
  const [envText, exampleText] = await Promise.all([
    readFile(envPath, "utf8"),
    readFile(examplePath, "utf8"),
  ]);
  const merged = mergeMissingEnvValues(envText, exampleText);

  if (merged === envText) {
    console.log(".env already exists and has all required keys.");
  } else {
    await writeFile(envPath, merged);
    console.log("Updated .env with missing non-secret defaults.");
  }
} catch {
  await copyFile(examplePath, envPath);
  console.log("Created .env from .env.example.");
  console.log("Add your GEMINI_API_KEY to .env before starting realtime interpretation.");
}

function mergeMissingEnvValues(envText, exampleText) {
  const existingKeys = new Set();

  for (const line of envText.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    existingKeys.add(trimmed.slice(0, trimmed.indexOf("=")).trim());
  }

  const missingLines = [];
  for (const line of exampleText.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const key = trimmed.slice(0, trimmed.indexOf("=")).trim();
    if (!existingKeys.has(key)) {
      missingLines.push(line);
    }
  }

  if (missingLines.length === 0) {
    return envText;
  }

  const suffix = envText.endsWith("\n") ? "" : "\n";
  return `${envText}${suffix}\n# Added by npm run setup\n${missingLines.join("\n")}\n`;
}

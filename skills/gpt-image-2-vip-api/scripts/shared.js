import path from "node:path";
import process from "node:process";
import { homedir } from "node:os";
import { mkdir, readFile, writeFile } from "node:fs/promises";

export const DEFAULT_IMAGE_DIR = "gpt-image-2-vip-output/image";
export const DEFAULT_PROMPT_DIR = "gpt-image-2-vip-output/prompt";
export const DEFAULT_BASE_URL = "https://aifast.site/v1";
export const DEFAULT_MODEL = "gpt-image-2-vip";
export const DEFAULT_SIZE = "2048x2048";
export const DEFAULT_QUALITY = "high";
export const DEFAULT_TIMEOUT_MS = 300_000;
export const DEFAULT_MAX_RETRIES = 2;

const VALID_QUALITIES = new Set(["auto", "low", "medium", "high"]);

export async function readEnvFile(filePath) {
  try {
    const text = await readFile(filePath, "utf8");
    const result = {};
    for (const line of text.split("\n")) {
      const trimmed = line.replace(/^\uFEFF/, "").trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const normalized = trimmed.startsWith("export ") ? trimmed.slice(7).trim() : trimmed;
      const pivot = normalized.indexOf("=");
      if (pivot === -1) continue;
      const key = normalized.slice(0, pivot).trim();
      let value = normalized.slice(pivot + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      result[key] = value;
    }
    return result;
  } catch {
    return {};
  }
}

export async function loadAmbientEnv() {
  const places = [
    path.join(process.cwd(), ".env"),
    path.join(process.cwd(), ".gateway.env"),
    path.join(homedir(), ".gateway.env"),
  ];
  for (const filePath of places) {
    const pairs = await readEnvFile(filePath);
    for (const [key, value] of Object.entries(pairs)) {
      if (!process.env[key]) process.env[key] = value;
    }
  }
}

export function buildBaseUrl() {
  const raw = (process.env.OPENAI_BASE_URL || DEFAULT_BASE_URL).trim().replace(/\/+$/, "");
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`OPENAI_BASE_URL is not a valid URL: ${raw}`);
  }
  if (!parsed.pathname || parsed.pathname === "/") {
    parsed.pathname = "/v1";
    return parsed.toString().replace(/\/$/, "");
  }
  return raw;
}

export function requireApiKey() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is required.");
  return apiKey;
}

function parseInteger(value, fallback, label, minimum = 0) {
  const parsed = value === undefined || value === null || value === "" ? fallback : Number(value);
  if (!Number.isInteger(parsed) || parsed < minimum) {
    throw new Error(`${label} must be an integer >= ${minimum}.`);
  }
  return parsed;
}

export function resolveImageOptions({ model, size, quality, n } = {}) {
  const resolved = {
    model: model || process.env.OPENAI_IMAGE_MODEL || DEFAULT_MODEL,
    size: size || process.env.OPENAI_IMAGE_SIZE || DEFAULT_SIZE,
    quality: quality || process.env.OPENAI_IMAGE_QUALITY || DEFAULT_QUALITY,
    n: parseInteger(n ?? process.env.OPENAI_IMAGE_N, 1, "n", 1),
  };
  if (!VALID_QUALITIES.has(resolved.quality)) {
    throw new Error(`quality must be one of: ${[...VALID_QUALITIES].join(", ")}.`);
  }
  if (!/^\d{3,5}x\d{3,5}$/.test(resolved.size)) {
    throw new Error("size must use pixel dimensions such as 2048x2048 or 3840x2160.");
  }
  return resolved;
}

export async function readPromptInput(prompt, promptFile) {
  if (prompt) return prompt.trim();
  if (promptFile) return (await readFile(path.resolve(promptFile), "utf8")).trim();
  throw new Error("Prompt is required. Use --prompt or --promptfile.");
}

export function slugify(value, fallback = "image-task") {
  const ascii = String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return ascii || fallback;
}

function timestamp() {
  const now = new Date();
  const parts = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    "-",
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0"),
  ];
  return parts.join("");
}

export function buildDefaultImagePath(kind, hint) {
  return path.join(
    DEFAULT_IMAGE_DIR,
    `${slugify(hint, kind === "edit" ? "edited-image" : "generated-image")}-${timestamp()}.png`,
  );
}

export function buildDefaultPromptPath(hint) {
  return path.join(DEFAULT_PROMPT_DIR, `${slugify(hint, "prompt")}-${timestamp()}.md`);
}

export function resolveOutput(raw, fallbackPath) {
  const full = path.resolve(raw || fallbackPath);
  return path.extname(full) ? full : `${full}.png`;
}

export function addOutputIndex(outputPath, index, total) {
  if (total <= 1) return outputPath;
  const ext = path.extname(outputPath);
  return `${outputPath.slice(0, -ext.length)}-${index + 1}${ext}`;
}

export async function savePrompt(prompt, rawPath, hint) {
  const finalPath = path.resolve(rawPath || buildDefaultPromptPath(hint));
  await mkdir(path.dirname(finalPath), { recursive: true });
  await writeFile(finalPath, `${prompt.trim()}\n`, "utf8");
  return finalPath;
}

export async function saveImage(outputPath, bytes) {
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, bytes);
}

export function mimeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  return "image/png";
}

export async function ensureFilesExist(files) {
  for (const file of files) {
    try {
      await readFile(path.resolve(file));
    } catch {
      throw new Error(`Image file not found: ${path.resolve(file)}`);
    }
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function retryDelay(attempt, retryAfter) {
  const seconds = Number(retryAfter);
  return Number.isFinite(seconds) && seconds >= 0
    ? seconds * 1000
    : Math.min(1000 * 2 ** attempt, 8000);
}

function errorMessage(text, status) {
  try {
    const parsed = JSON.parse(text);
    return parsed?.error?.message || parsed?.message || text || `HTTP ${status}`;
  } catch {
    return text || `HTTP ${status}`;
  }
}

async function postWithRetry(url, buildRequest) {
  const apiKey = requireApiKey();
  const timeoutMs = parseInteger(
    process.env.OPENAI_IMAGE_TIMEOUT_MS,
    DEFAULT_TIMEOUT_MS,
    "OPENAI_IMAGE_TIMEOUT_MS",
    1000,
  );
  const maxRetries = parseInteger(
    process.env.OPENAI_IMAGE_MAX_RETRIES,
    DEFAULT_MAX_RETRIES,
    "OPENAI_IMAGE_MAX_RETRIES",
  );

  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, {
        ...buildRequest(apiKey),
        signal: controller.signal,
      });
      if (response.ok) return await response.json();
      const text = await response.text();
      if ((response.status === 429 || response.status >= 500) && attempt < maxRetries) {
        await sleep(retryDelay(attempt, response.headers.get("retry-after")));
        continue;
      }
      throw new Error(`Image API error (${response.status}): ${errorMessage(text, response.status)}`);
    } catch (error) {
      const retryable = error?.name === "AbortError" || error instanceof TypeError;
      if (retryable && attempt < maxRetries) {
        await sleep(retryDelay(attempt));
        continue;
      }
      if (error?.name === "AbortError") {
        throw new Error(`Image API request timed out after ${timeoutMs} ms.`);
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
  throw new Error("Image API request failed after retries.");
}

export function postJson(url, payload) {
  return postWithRetry(url, (apiKey) => ({
    method: "POST",
    headers: {
      authorization: `Bearer ${apiKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  }));
}

export function postMultipart(url, form) {
  return postWithRetry(url, (apiKey) => ({
    method: "POST",
    headers: { authorization: `Bearer ${apiKey}` },
    body: form,
  }));
}

async function downloadImage(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to download generated image (${response.status}).`);
  return Buffer.from(await response.arrayBuffer());
}

export async function extractGeneratedImages(json) {
  if (!Array.isArray(json?.data) || json.data.length === 0) {
    throw new Error("API response did not include a non-empty data array.");
  }
  return Promise.all(
    json.data.map((item, index) => {
      if (item?.b64_json) return Buffer.from(item.b64_json, "base64");
      if (item?.url) return downloadImage(item.url);
      throw new Error(`API response data[${index}] did not include b64_json or url.`);
    }),
  );
}

export function responseSummary(json) {
  return {
    created: json?.created ?? null,
    imageCount: Array.isArray(json?.data) ? json.data.length : 0,
    responseFormats: Array.isArray(json?.data)
      ? json.data.map((item) => (item?.b64_json ? "b64_json" : item?.url ? "url" : "unknown"))
      : [],
  };
}

export function appendFormValue(form, key, value) {
  if (value !== undefined && value !== null && value !== "") {
    form.append(key, String(value));
  }
}

export function printJson(value) {
  console.log(JSON.stringify(value, null, 2));
}

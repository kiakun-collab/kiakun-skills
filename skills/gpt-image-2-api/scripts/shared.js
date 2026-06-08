import path from "node:path";
import process from "node:process";
import { homedir } from "node:os";
import { mkdir, readFile, writeFile } from "node:fs/promises";

export const DEFAULT_OUTPUT_ROOT = "gpt-image-2-output";
export const DEFAULT_PROMPT_DIR = path.join(DEFAULT_OUTPUT_ROOT, "prompts");
export const DEFAULT_BASE_URL = "https://aifast.site/v1";
export const STANDARD_MODEL = "gpt-image-2";
export const VIP_MODEL = "gpt-image-2-vip";
export const DEFAULT_PROFILE = "auto";
export const DEFAULT_STANDARD_SIZE = "1024x1024";
export const DEFAULT_VIP_SIZE = "2048x2048";
export const DEFAULT_VIP_QUALITY = "high";
export const DEFAULT_TIMEOUT_MS = 300_000;
export const DEFAULT_MAX_RETRIES = 2;

const VALID_PROFILES = new Set(["auto", "standard", "vip"]);
const VALID_QUALITIES = new Set(["auto", "low", "medium", "high"]);
const RATIO_SIZES = new Set([
  "auto",
  "1:1",
  "3:2",
  "2:3",
  "4:3",
  "3:4",
  "5:4",
  "4:5",
  "16:9",
  "9:16",
  "21:9",
  "9:21",
  "2:1",
  "1:2",
  "3:1",
  "1:3",
]);
const STANDARD_PIXEL_SIZES = new Set([
  "256x256",
  "512x512",
  "1024x1024",
  "1536x1024",
  "1792x1024",
  "1024x1536",
  "1024x1792",
  "1280x720",
  "720x1280",
]);
const VIP_PIXEL_SIZES = new Set([
  "2048x2048",
  "2880x2880",
  "2560x1440",
  "3840x2160",
  "1440x2560",
  "2160x3840",
  "2304x1728",
  "3264x2448",
  "1728x2304",
  "2448x3264",
  "2496x1664",
  "3504x2336",
  "1664x2496",
  "2336x3504",
  "2240x1792",
  "3200x2560",
  "1792x2240",
  "2560x3200",
  "3024x1296",
  "3696x1584",
]);

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

function normalizeModel(model) {
  if (!model) return null;
  if (model !== STANDARD_MODEL && model !== VIP_MODEL) {
    throw new Error(`model must be ${STANDARD_MODEL} or ${VIP_MODEL}.`);
  }
  return model;
}

function validateSize(size, tier) {
  if (tier === "standard") {
    if (!STANDARD_PIXEL_SIZES.has(size) && !RATIO_SIZES.has(size)) {
      throw new Error(
        `Unsupported standard output preset: ${size}. Use a documented preset or ratio; arbitrary resolutions are not supported.`,
      );
    }
    return;
  }
  if (!VIP_PIXEL_SIZES.has(size)) {
    throw new Error(
      `Unsupported VIP output preset: ${size}. Use a documented 2K/4K preset such as ${DEFAULT_VIP_SIZE} or 3840x2160; arbitrary resolutions are not supported.`,
    );
  }
}

export function resolveImageOptions(
  { profile, model, size, quality, n } = {},
  { referenceCount = 0 } = {},
) {
  const requestedProfile = profile || process.env.GPT_IMAGE_PROFILE || DEFAULT_PROFILE;
  if (!VALID_PROFILES.has(requestedProfile)) {
    throw new Error(`profile must be one of: ${[...VALID_PROFILES].join(", ")}.`);
  }

  const explicitModel = normalizeModel(model);
  const requestedSize = size || null;
  const requestedQuality = quality || null;
  if (requestedQuality && !VALID_QUALITIES.has(requestedQuality)) {
    throw new Error(`quality must be one of: ${[...VALID_QUALITIES].join(", ")}.`);
  }
  if (
    explicitModel &&
    requestedProfile !== "auto" &&
    ((requestedProfile === "standard" && explicitModel === VIP_MODEL) ||
      (requestedProfile === "vip" && explicitModel === STANDARD_MODEL))
  ) {
    throw new Error(`profile ${requestedProfile} conflicts with explicit model ${explicitModel}.`);
  }

  const vipReasons = [];
  if (referenceCount >= 2) vipReasons.push("multiple-reference-images");
  if (requestedQuality) vipReasons.push("quality-control-requested");
  if (requestedSize && VIP_PIXEL_SIZES.has(requestedSize)) {
    vipReasons.push("2k-or-4k-preset-requested");
  }

  let tier;
  if (explicitModel) {
    tier = explicitModel === VIP_MODEL ? "vip" : "standard";
  } else if (requestedProfile === "standard" || requestedProfile === "vip") {
    tier = requestedProfile;
  } else {
    tier = vipReasons.length > 0 ? "vip" : "standard";
  }

  if (tier === "standard" && referenceCount >= 2) {
    throw new Error("Two or more reference images require profile vip or profile auto.");
  }
  if (tier === "standard" && requestedQuality) {
    throw new Error("quality is only supported by gpt-image-2-vip.");
  }
  if (tier === "standard" && requestedSize && VIP_PIXEL_SIZES.has(requestedSize)) {
    throw new Error("2K/4K output presets require profile vip or profile auto.");
  }

  const resolvedSize =
    requestedSize ||
    (tier === "vip"
      ? process.env.GPT_IMAGE_VIP_SIZE || DEFAULT_VIP_SIZE
      : process.env.GPT_IMAGE_STANDARD_SIZE || DEFAULT_STANDARD_SIZE);
  validateSize(resolvedSize, tier);

  const resolvedQuality =
    tier === "vip"
      ? requestedQuality || process.env.GPT_IMAGE_VIP_QUALITY || DEFAULT_VIP_QUALITY
      : null;
  const resolvedModel = tier === "vip" ? VIP_MODEL : STANDARD_MODEL;
  const routeReasons =
    tier === "vip"
      ? vipReasons.length > 0
        ? vipReasons
        : [explicitModel ? "explicit-vip-model" : "explicit-vip-profile"]
      : [explicitModel ? "explicit-standard-model" : "cost-saving-default"];

  return {
    requestedProfile,
    tier,
    model: resolvedModel,
    size: resolvedSize,
    quality: resolvedQuality,
    n: parseInteger(n ?? process.env.GPT_IMAGE_N, 1, "n", 1),
    routeReasons,
  };
}

export function buildApiPayload(options, extra = {}) {
  const payload = {
    model: options.model,
    size: options.size,
    ...extra,
  };
  if (options.quality) payload.quality = options.quality;
  return payload;
}

export async function readPromptInput(prompt, promptFile) {
  if (Boolean(prompt) === Boolean(promptFile)) {
    throw new Error("Provide exactly one prompt source: --prompt or --promptfile.");
  }
  if (prompt) return prompt.trim();
  return (await readFile(path.resolve(promptFile), "utf8")).trim();
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
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    "-",
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0"),
  ].join("");
}

export function buildDefaultImagePath(operation, hint) {
  const folder = operation === "edit" ? "edited" : "generated";
  return path.join(
    DEFAULT_OUTPUT_ROOT,
    folder,
    `${slugify(hint, `${folder}-image`)}-${timestamp()}.png`,
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

export function imageMetadata(bytes) {
  if (
    bytes.length >= 24 &&
    bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
  ) {
    return {
      format: "png",
      width: bytes.readUInt32BE(16),
      height: bytes.readUInt32BE(20),
      bytes: bytes.length,
    };
  }

  if (bytes.length >= 4 && bytes[0] === 0xff && bytes[1] === 0xd8) {
    let offset = 2;
    while (offset + 9 < bytes.length) {
      if (bytes[offset] !== 0xff) {
        offset += 1;
        continue;
      }
      const marker = bytes[offset + 1];
      const length = bytes.readUInt16BE(offset + 2);
      if (marker >= 0xc0 && marker <= 0xc3) {
        return {
          format: "jpeg",
          width: bytes.readUInt16BE(offset + 7),
          height: bytes.readUInt16BE(offset + 5),
          bytes: bytes.length,
        };
      }
      if (length < 2) break;
      offset += 2 + length;
    }
  }

  return { format: "unknown", width: null, height: null, bytes: bytes.length };
}

export function summarizeSavedImages(images, paths, requestedSize) {
  const expected = /^(\d+)x(\d+)$/.exec(requestedSize || "");
  const expectedWidth = expected ? Number(expected[1]) : null;
  const expectedHeight = expected ? Number(expected[2]) : null;
  const actualImages = images.map((bytes, index) => ({
    path: paths[index],
    ...imageMetadata(bytes),
  }));
  const mismatches =
    expectedWidth === null
      ? []
      : actualImages.filter(
          (image) =>
            image.width !== null &&
            (image.width !== expectedWidth || image.height !== expectedHeight),
        );
  return {
    actualImages,
    requestedSizeMatched: expectedWidth === null ? null : mismatches.length === 0,
    warnings: mismatches.map(
      (image) =>
        `Gateway returned ${image.width}x${image.height} for requested ${requestedSize}: ${image.path}`,
    ),
  };
}

export function mimeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  if (ext !== ".png") {
    throw new Error(`Unsupported image type: ${ext || "(no extension)"}. Use PNG, JPEG, or WebP.`);
  }
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

export async function downloadReferenceImage(rawUrl) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error(`Reference URL is invalid: ${rawUrl}`);
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error(`Reference URL must use http or https: ${rawUrl}`);
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download reference image (${response.status}): ${rawUrl}`);
  }
  const contentType = (response.headers.get("content-type") || "").split(";")[0].trim();
  if (!["image/png", "image/jpeg", "image/webp"].includes(contentType)) {
    throw new Error(
      `Reference URL must return PNG, JPEG, or WebP, received ${contentType || "unknown"}: ${rawUrl}`,
    );
  }
  const extension =
    contentType === "image/png" ? ".png" : contentType === "image/webp" ? ".webp" : ".jpg";
  const basename = path.basename(url.pathname);
  const filename = basename && path.extname(basename) ? basename : `reference${extension}`;
  return {
    bytes: Buffer.from(await response.arrayBuffer()),
    contentType,
    filename,
  };
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

export function publicPlan(operation, options, extra = {}) {
  return {
    operation,
    endpoint: `${buildBaseUrl()}/images/${operation === "edit" ? "edits" : "generations"}`,
    requestedProfile: options.requestedProfile,
    selectedTier: options.tier,
    model: options.model,
    size: options.size,
    quality: options.quality,
    n: operation === "generate" ? options.n : undefined,
    routeReasons: options.routeReasons,
    ...extra,
  };
}

export function printJson(value) {
  console.log(JSON.stringify(value, null, 2));
}

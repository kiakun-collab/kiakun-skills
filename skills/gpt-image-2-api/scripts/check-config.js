#!/usr/bin/env node
import process from "node:process";
import {
  DEFAULT_ATLAS_QUALITY,
  DEFAULT_ATLAS_SIZE,
  DEFAULT_ATLAS_POLL_TIMEOUT_MS,
  DEFAULT_STANDARD_SIZE,
  DEFAULT_TIMEOUT_MS,
  DEFAULT_VIP_QUALITY,
  DEFAULT_VIP_SIZE,
  ATLAS_MODEL,
  STANDARD_MODEL,
  VIP_MODEL,
  buildAtlasBaseUrl,
  buildBaseUrl,
  loadAmbientEnv,
  printJson,
} from "./shared.js";

await loadAmbientEnv();

const result = {
  ready: Boolean(process.env.OPENAI_API_KEY || process.env.ATLASCLOUD_API_KEY),
  hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  hasAtlasApiKey: Boolean(process.env.ATLASCLOUD_API_KEY),
  baseUrl: buildBaseUrl(),
  atlasBaseUrl: buildAtlasBaseUrl(),
  defaultProfile: process.env.GPT_IMAGE_PROFILE || "auto",
  standard: {
    model: STANDARD_MODEL,
    size: process.env.GPT_IMAGE_STANDARD_SIZE || DEFAULT_STANDARD_SIZE,
    quality: null,
  },
  vip: {
    model: VIP_MODEL,
    size: process.env.GPT_IMAGE_VIP_SIZE || process.env.GPT_IMAGE_HD_SIZE || DEFAULT_VIP_SIZE,
    quality:
      process.env.GPT_IMAGE_VIP_QUALITY ||
      process.env.GPT_IMAGE_HD_QUALITY ||
      DEFAULT_VIP_QUALITY,
  },
  atlasFallback: {
    model: ATLAS_MODEL,
    enabled: (process.env.GPT_IMAGE_ATLAS_FALLBACK || "true").toLowerCase(),
    size:
      process.env.GPT_IMAGE_ATLAS_SIZE ||
      process.env.GPT_IMAGE_HD_SIZE ||
      DEFAULT_ATLAS_SIZE,
    quality:
      process.env.GPT_IMAGE_ATLAS_QUALITY ||
      process.env.GPT_IMAGE_HD_QUALITY ||
      DEFAULT_ATLAS_QUALITY,
  },
  timeoutMs: Number(process.env.OPENAI_IMAGE_TIMEOUT_MS ?? DEFAULT_TIMEOUT_MS),
  maxRetries: Number(process.env.OPENAI_IMAGE_MAX_RETRIES || 2),
  atlasPollIntervalMs: Number(process.env.ATLASCLOUD_POLL_INTERVAL_MS || 2000),
  atlasPollTimeoutMs: Number(
    process.env.ATLASCLOUD_POLL_TIMEOUT_MS || DEFAULT_ATLAS_POLL_TIMEOUT_MS,
  ),
};

if (process.argv.includes("--json")) printJson(result);
else {
  console.log(`ready          : ${result.ready}`);
  console.log(`hasApiKey      : ${result.hasApiKey}`);
  console.log(`hasAtlasApiKey : ${result.hasAtlasApiKey}`);
  console.log(`baseUrl        : ${result.baseUrl}`);
  console.log(`atlasBaseUrl   : ${result.atlasBaseUrl}`);
  console.log(`defaultProfile : ${result.defaultProfile}`);
  console.log(`standard       : ${result.standard.model} / ${result.standard.size}`);
  console.log(`vip            : ${result.vip.model} / ${result.vip.size} / ${result.vip.quality}`);
  console.log(
    `atlasFallback  : ${result.atlasFallback.model} / ${result.atlasFallback.size} / ${result.atlasFallback.quality} / ${result.atlasFallback.enabled}`,
  );
  console.log(`timeoutMs      : ${result.timeoutMs || "none"}`);
  console.log(`maxRetries     : ${result.maxRetries}`);
  console.log(`atlasPollMs    : ${result.atlasPollIntervalMs}`);
  console.log(`atlasTimeoutMs : ${result.atlasPollTimeoutMs}`);
}

if (!result.ready) process.exitCode = 1;

#!/usr/bin/env node
import process from "node:process";
import {
  DEFAULT_ATLAS_QUALITY,
  DEFAULT_ATLAS_SIZE,
  DEFAULT_ATLAS_POLL_TIMEOUT_MS,
  DEFAULT_STANDARD_SIZE,
  DEFAULT_TIMEOUT_MS,
  DEFAULT_XAPEX_MODEL,
  DEFAULT_XAPEX_POLL_INTERVAL_MS,
  DEFAULT_XAPEX_POLL_TIMEOUT_MS,
  DEFAULT_XAPEX_QUALITY,
  DEFAULT_XAPEX_SIZE,
  DEFAULT_VIP_GENERATION_SIZE,
  DEFAULT_VIP_QUALITY,
  DEFAULT_VIP_SIZE,
  ATLAS_MODEL,
  STANDARD_MODEL,
  VIP_MODEL,
  buildAtlasBaseUrl,
  buildBaseUrl,
  buildXapexBaseUrl,
  loadAmbientEnv,
  printJson,
} from "./shared.js";

await loadAmbientEnv();

const result = {
  ready: Boolean(
    process.env.OPENAI_API_KEY || process.env.ATLASCLOUD_API_KEY || process.env.XAPEX_API_KEY,
  ),
  hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  hasXapexApiKey: Boolean(process.env.XAPEX_API_KEY),
  hasAtlasApiKey: Boolean(process.env.ATLASCLOUD_API_KEY),
  baseUrl: buildBaseUrl(),
  xapexBaseUrl: buildXapexBaseUrl(),
  atlasBaseUrl: buildAtlasBaseUrl(),
  defaultProfile: process.env.GPT_IMAGE_PROFILE || "auto",
  generation: {
    size: process.env.GPT_IMAGE_GENERATION_SIZE ||
      process.env.GPT_IMAGE_STANDARD_SIZE ||
      DEFAULT_STANDARD_SIZE,
    quality: null,
    note: "standard generation uses documented 1K create sizes; max generation uses aifast VIP/max presets",
  },
  vipGeneration: {
    model: VIP_MODEL,
    size:
      process.env.GPT_IMAGE_VIP_GENERATION_SIZE ||
      process.env.GPT_IMAGE_VIP_SIZE ||
      process.env.GPT_IMAGE_HD_SIZE ||
      DEFAULT_VIP_GENERATION_SIZE,
    quality: null,
  },
  standard: {
    model: STANDARD_MODEL,
    size: process.env.GPT_IMAGE_STANDARD_SIZE || DEFAULT_STANDARD_SIZE,
    quality: null,
  },
  xapex: {
    model: process.env.GPT_IMAGE_XAPEX_MODEL || DEFAULT_XAPEX_MODEL,
    size: process.env.GPT_IMAGE_XAPEX_SIZE || DEFAULT_XAPEX_SIZE,
    quality: process.env.GPT_IMAGE_XAPEX_QUALITY || DEFAULT_XAPEX_QUALITY,
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
  xapexTimeoutMs: Number(process.env.XAPEX_IMAGE_TIMEOUT_MS ?? DEFAULT_TIMEOUT_MS),
  maxRetries: Number(process.env.OPENAI_IMAGE_MAX_RETRIES || 2),
  xapexMaxRetries: Number(process.env.XAPEX_IMAGE_MAX_RETRIES || 2),
  xapexPollIntervalMs: Number(
    process.env.XAPEX_POLL_INTERVAL_MS || DEFAULT_XAPEX_POLL_INTERVAL_MS,
  ),
  xapexPollTimeoutMs: Number(
    process.env.XAPEX_POLL_TIMEOUT_MS || DEFAULT_XAPEX_POLL_TIMEOUT_MS,
  ),
  atlasPollIntervalMs: Number(process.env.ATLASCLOUD_POLL_INTERVAL_MS || 2000),
  atlasPollTimeoutMs: Number(
    process.env.ATLASCLOUD_POLL_TIMEOUT_MS || DEFAULT_ATLAS_POLL_TIMEOUT_MS,
  ),
};

if (process.argv.includes("--json")) printJson(result);
else {
  console.log(`ready          : ${result.ready}`);
  console.log(`hasApiKey      : ${result.hasApiKey}`);
  console.log(`hasXapexApiKey: ${result.hasXapexApiKey}`);
  console.log(`hasAtlasApiKey : ${result.hasAtlasApiKey}`);
  console.log(`baseUrl        : ${result.baseUrl}`);
  console.log(`xapexBaseUrl   : ${result.xapexBaseUrl}`);
  console.log(`atlasBaseUrl   : ${result.atlasBaseUrl}`);
  console.log(`defaultProfile : ${result.defaultProfile}`);
  console.log(`generation     : ${result.generation.size} / quality omitted`);
  console.log(`vipGeneration  : ${result.vipGeneration.model} / ${result.vipGeneration.size} / quality omitted`);
  console.log(`standard       : ${result.standard.model} / ${result.standard.size}`);
  console.log(`xapex          : ${result.xapex.model} / ${result.xapex.size} / ${result.xapex.quality}`);
  console.log(`vip            : ${result.vip.model} / ${result.vip.size} / ${result.vip.quality}`);
  console.log(
    `atlasFallback  : ${result.atlasFallback.model} / ${result.atlasFallback.size} / ${result.atlasFallback.quality} / ${result.atlasFallback.enabled}`,
  );
  console.log(`timeoutMs      : ${result.timeoutMs || "none"}`);
  console.log(`xapexTimeoutMs : ${result.xapexTimeoutMs || "none"}`);
  console.log(`maxRetries     : ${result.maxRetries}`);
  console.log(`xapexRetries   : ${result.xapexMaxRetries}`);
  console.log(`xapexPollMs    : ${result.xapexPollIntervalMs}`);
  console.log(`xapexTaskMs    : ${result.xapexPollTimeoutMs}`);
  console.log(`atlasPollMs    : ${result.atlasPollIntervalMs}`);
  console.log(`atlasTimeoutMs : ${result.atlasPollTimeoutMs}`);
}

if (!result.ready) process.exitCode = 1;

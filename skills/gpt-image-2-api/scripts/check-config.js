#!/usr/bin/env node
import process from "node:process";
import {
  DEFAULT_STANDARD_SIZE,
  DEFAULT_VIP_QUALITY,
  DEFAULT_VIP_SIZE,
  STANDARD_MODEL,
  VIP_MODEL,
  buildBaseUrl,
  loadAmbientEnv,
  printJson,
} from "./shared.js";

await loadAmbientEnv();

const result = {
  ready: Boolean(process.env.OPENAI_API_KEY),
  hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  baseUrl: buildBaseUrl(),
  defaultProfile: process.env.GPT_IMAGE_PROFILE || "auto",
  standard: {
    model: STANDARD_MODEL,
    size: process.env.GPT_IMAGE_STANDARD_SIZE || DEFAULT_STANDARD_SIZE,
    quality: null,
  },
  vip: {
    model: VIP_MODEL,
    size: process.env.GPT_IMAGE_VIP_SIZE || DEFAULT_VIP_SIZE,
    quality: process.env.GPT_IMAGE_VIP_QUALITY || DEFAULT_VIP_QUALITY,
  },
  timeoutMs: Number(process.env.OPENAI_IMAGE_TIMEOUT_MS || 300000),
  maxRetries: Number(process.env.OPENAI_IMAGE_MAX_RETRIES || 2),
};

if (process.argv.includes("--json")) printJson(result);
else {
  console.log(`ready          : ${result.ready}`);
  console.log(`hasApiKey      : ${result.hasApiKey}`);
  console.log(`baseUrl        : ${result.baseUrl}`);
  console.log(`defaultProfile : ${result.defaultProfile}`);
  console.log(`standard       : ${result.standard.model} / ${result.standard.size}`);
  console.log(`vip            : ${result.vip.model} / ${result.vip.size} / ${result.vip.quality}`);
  console.log(`timeoutMs      : ${result.timeoutMs}`);
  console.log(`maxRetries     : ${result.maxRetries}`);
}

if (!result.ready) process.exitCode = 1;

#!/usr/bin/env node
import process from "node:process";
import {
  buildBaseUrl,
  loadAmbientEnv,
  printJson,
  resolveImageOptions,
} from "./shared.js";

await loadAmbientEnv();

const result = {
  ready: Boolean(process.env.OPENAI_API_KEY),
  hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  baseUrl: buildBaseUrl(),
  ...resolveImageOptions(),
  timeoutMs: Number(process.env.OPENAI_IMAGE_TIMEOUT_MS || 300000),
  maxRetries: Number(process.env.OPENAI_IMAGE_MAX_RETRIES || 2),
};

if (process.argv.includes("--json")) {
  printJson(result);
} else {
  for (const [key, value] of Object.entries(result)) {
    console.log(`${key.padEnd(12, " ")}: ${value}`);
  }
}

if (!result.ready) process.exitCode = 1;

#!/usr/bin/env node
import process from "node:process";
import path from "node:path";
import { readFile } from "node:fs/promises";
import { editImages } from "./edit.js";
import { generateImage } from "./generate.js";
import { loadAmbientEnv, printJson, slugify } from "./shared.js";

const SHARED_KEYS = ["profile", "model", "size", "quality", "n"];

function help() {
  console.log(`Run many generate/edit jobs in one command.

Usage:
  node scripts/batch.js --promptlist prompts.txt
  node scripts/batch.js --batch tasks.json

Input (choose one):
  --promptlist <path>   One prompt per line; blank lines and #comments ignored.
                        All lines share the routing/size params below.
  --batch <path>        JSON array or JSONL manifest; each task configured on its own.

Shared params (promptlist mode, and defaults for manifest tasks):
  --profile <name>      auto | standard | vip | atlas | xapex
  --model <name>        Explicit model override
  --size <preset>       Output preset
  --quality <level>     XApex/VIP/Atlas: auto | low | medium | high
  --n <count>           Images per generate task, XApex 1-9; others 1-10

Batch control:
  --concurrency <n>     Parallel tasks (default: 2)
  --output-dir <dir>    Base dir for auto-named outputs when a task has no --output
  --dry-run             Preview each task's route/cost; no API calls
  --json                Print a structured summary
  -h, --help            Show help

Manifest task fields:
  prompt | promptfile, profile, model, size, quality, n, output,
  images: [paths], urls: [urls]   (images/urls present => edit task)`);
}

function parseArgs(argv) {
  const config = { concurrency: 2, dryRun: false, json: false, help: false, shared: {} };
  const names = new Map([
    ["--promptlist", "promptList"],
    ["--batch", "batch"],
    ["--output-dir", "outputDir"],
    ["--concurrency", "concurrency"],
    ["--profile", "profile"],
    ["--model", "model"],
    ["--size", "size"],
    ["--quality", "quality"],
    ["--n", "n"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "-h" || arg === "--help") config.help = true;
    else if (arg === "--dry-run") config.dryRun = true;
    else if (arg === "--json") config.json = true;
    else if (names.has(arg)) {
      const value = argv[++index];
      if (!value) throw new Error(`Missing value for ${arg}`);
      const key = names.get(arg);
      if (SHARED_KEYS.includes(key)) config.shared[key] = value;
      else config[key] = value;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  return config;
}

function parseManifest(text) {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("[")) {
    const parsed = JSON.parse(trimmed);
    if (!Array.isArray(parsed)) throw new Error("Manifest JSON must be an array of tasks.");
    return parsed;
  }
  // JSONL: one JSON object per non-empty line.
  return trimmed
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch {
        throw new Error(`Manifest line ${index + 1} is not valid JSON: ${line}`);
      }
    });
}

async function loadTasks(config) {
  if (Boolean(config.promptList) === Boolean(config.batch)) {
    throw new Error("Provide exactly one input: --promptlist or --batch.");
  }
  if (config.promptList) {
    const text = await readFile(path.resolve(config.promptList), "utf8");
    const prompts = text
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#"));
    if (prompts.length === 0) throw new Error("Prompt list is empty.");
    return prompts.map((prompt) => ({ prompt }));
  }
  const tasks = parseManifest(await readFile(path.resolve(config.batch), "utf8"));
  if (tasks.length === 0) throw new Error("Manifest contains no tasks.");
  return tasks;
}

function toArray(value) {
  if (value === undefined || value === null) return [];
  return Array.isArray(value) ? value : [value];
}

function buildTaskConfig(task, index, config) {
  const merged = { ...config.shared, ...task };
  const images = toArray(task.images);
  const urls = toArray(task.urls);
  const isEdit = images.length > 0 || urls.length > 0;

  const promptFile = merged.promptFile ?? merged.promptfile;
  if (!merged.prompt && !promptFile) {
    throw new Error(`Task ${index + 1} needs a prompt or promptfile.`);
  }
  if (merged.prompt && promptFile) {
    throw new Error(`Task ${index + 1} has both prompt and promptfile.`);
  }
  if (images.length > 0 && urls.length > 0) {
    throw new Error(`Task ${index + 1} mixes images and urls.`);
  }

  const taskConfig = {};
  if (merged.prompt) taskConfig.prompt = String(merged.prompt);
  if (promptFile) taskConfig.promptFile = String(promptFile);
  for (const key of ["profile", "model", "size", "quality"]) {
    if (merged[key] !== undefined) taskConfig[key] = String(merged[key]);
  }
  if (!isEdit && merged.n !== undefined) taskConfig.n = String(merged.n);

  let output = merged.output;
  if (!output && config.outputDir) {
    const hint = slugify(
      String(merged.prompt || merged.promptfile || `task-${index + 1}`)
        .split(/\s+/)
        .slice(0, 6)
        .join(" "),
      `task-${index + 1}`,
    );
    output = path.join(config.outputDir, `${String(index + 1).padStart(3, "0")}-${hint}.png`);
  }
  if (output) taskConfig.output = String(output);
  if (isEdit) {
    taskConfig.images = images.map(String);
    taskConfig.urls = urls.map(String);
  }

  return { operation: isEdit ? "edit" : "generate", config: taskConfig };
}

async function runPool(items, limit, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  const size = Math.max(1, Math.min(limit, items.length));
  const runners = Array.from({ length: size }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      results[index] = await worker(items[index], index);
    }
  });
  await Promise.all(runners);
  return results;
}

async function run() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) return help();

  const concurrency = Number(config.concurrency);
  if (!Number.isInteger(concurrency) || concurrency < 1) {
    throw new Error("--concurrency must be an integer >= 1.");
  }

  await loadAmbientEnv();
  const tasks = await loadTasks(config);
  const built = tasks.map((task, index) => buildTaskConfig(task, index, config));

  const results = await runPool(built, concurrency, async (task, index) => {
    const base = { index: index + 1, operation: task.operation };
    try {
      const taskOptions = { ...task.config, dryRun: config.dryRun, json: true, skipEnvLoad: true };
      const data = task.operation === "edit"
        ? await editImages(taskOptions)
        : await generateImage(taskOptions);
      return { ...base, ok: true, result: data, savedImages: data?.savedImages ?? null };
    } catch (error) {
      return {
        ...base,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  });

  const succeeded = results.filter((r) => r.ok);
  const failed = results.filter((r) => !r.ok);

  if (config.json) {
    return printJson({
      mode: config.dryRun ? "dry-run" : "run",
      total: results.length,
      succeeded: succeeded.length,
      failed: failed.length,
      concurrency,
      results,
    });
  }

  for (const r of results) {
    if (r.ok) {
      const saved = r.savedImages ? r.savedImages.join(", ") : "(dry-run)";
      console.log(`[${r.index}] ${r.operation} OK  ${saved}`);
    } else {
      console.log(`[${r.index}] ${r.operation} FAIL  ${r.error}`);
    }
  }
  console.log(`\n${succeeded.length}/${results.length} succeeded, ${failed.length} failed.`);
  if (failed.length > 0 && !config.dryRun) process.exitCode = 1;
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

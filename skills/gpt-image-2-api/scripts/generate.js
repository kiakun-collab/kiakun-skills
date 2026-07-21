#!/usr/bin/env node
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import {
  DEFAULT_OUTPUT_ROOT,
  addOutputIndex,
  buildApiPayload,
  buildDefaultImagePath,
  extractGeneratedImages,
  loadAmbientEnv,
  postJson,
  postXapexJson,
  printJson,
  publicPlan,
  readPromptInput,
  resolveImageOptions,
  resolveOutput,
  responseSummary,
  saveImage,
  savePrompt,
  slugify,
  summarizeSavedImages,
  runXapexTask,
} from "./shared.js";

function help() {
  console.log(`Generate an image through POST /v1/images/generations.

Usage:
  node scripts/generate.js --prompt "A cozy reading corner"

Required input (choose one):
  --prompt <text>          Prompt text
  --promptfile <path>      Load prompt from a UTF-8 file

Routing and image parameters:
  --profile <name>         auto | standard | vip | xapex (hd is a vip compatibility alias)
  --model <name>           Explicit model override; XApex defaults to gpt-image-2
  --size <preset>          Standard 1K preset, VIP/max 1K/2K/4K preset, or ratio mapped to a preset
  --quality <level>        XApex API field; aifast auto uses it only as a VIP route hint
  --n <count>              Number of images, XApex 1-9; other profiles 1-10 (default: 1)
  --async                  XApex only: submit a task and poll until completed

Output:
  --output <path>          Image path (default: ${DEFAULT_OUTPUT_ROOT}/generated/...)
  --image <path>           Backward-compatible alias for --output
  --prompt-output <path>   Prompt archive path
  --dry-run                Print the selected model and request plan; do not call API
  --json                   Print structured result without image Base64
  -h, --help               Show help

Cost-aware examples:
  node scripts/generate.js --prompt "A cat by a window"
  node scripts/generate.js --model gpt-image-2-max --size 9:16 --promptfile poster.md`);
}

function parseArgs(argv) {
  const config = { json: false, dryRun: false, help: false };
  const names = new Map([
    ["--prompt", "prompt"],
    ["--promptfile", "promptFile"],
    ["--prompt-output", "promptOutput"],
    ["--output", "output"],
    ["--image", "output"],
    ["--profile", "profile"],
    ["--model", "model"],
    ["--size", "size"],
    ["--quality", "quality"],
    ["--n", "n"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "-h" || arg === "--help") config.help = true;
    else if (arg === "--json") config.json = true;
    else if (arg === "--dry-run") config.dryRun = true;
    else if (arg === "--async") config.async = true;
    else if (names.has(arg)) {
      const value = argv[++index];
      if (!value) throw new Error(`Missing value for ${arg}`);
      config[names.get(arg)] = value;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  return config;
}

export async function generateImage(config) {
  if (!config.skipEnvLoad) await loadAmbientEnv();
  const prompt = await readPromptInput(config.prompt, config.promptFile);
  const options = resolveImageOptions(config, { operation: "generate" });
  if (options.tier === "atlas") {
    throw new Error("AtlasCloud fallback uses an edit-only model and requires at least one reference image; use edit.js.");
  }
  if (config.async && options.tier !== "xapex") {
    throw new Error("--async is currently supported only with --profile xapex.");
  }
  const plan = publicPlan("generate", options, { async: Boolean(config.async) });
  if (config.dryRun) return plan;

  const hint = slugify(prompt.split(/\s+/).slice(0, 8).join(" "), "generated-image");
  const promptPath = await savePrompt(prompt, config.promptOutput, hint);
  const outputPath = resolveOutput(config.output, buildDefaultImagePath("generate", hint));
  const images = [];
  const responseSummaries = [];
  let taskId = null;
  const sendJson = options.tier === "xapex" ? postXapexJson : postJson;
  if (config.async) {
    const started = await sendJson(
      plan.endpoint,
      buildApiPayload(options, { prompt, n: options.n }),
    );
    const completed = await runXapexTask(started);
    taskId = completed.taskId;
    images.push(...(await extractGeneratedImages(completed.result)));
    responseSummaries.push(responseSummary(completed.result));
  } else while (images.length < options.n) {
    const remaining = options.n - images.length;
    const response = await sendJson(
      plan.endpoint,
      buildApiPayload(options, {
        prompt,
        n: remaining,
      }),
    );
    const batch = await extractGeneratedImages(response);
    images.push(...batch.slice(0, remaining));
    responseSummaries.push(responseSummary(response));
  }
  const savedImages = [];
  for (let index = 0; index < images.length; index += 1) {
    const imagePath = addOutputIndex(outputPath, index, images.length);
    await saveImage(imagePath, images[index]);
    savedImages.push(imagePath);
  }
  const imageSummary = summarizeSavedImages(images, savedImages, options.size);

  return {
    ...plan,
    taskId,
    savedImages,
    savedPrompt: promptPath,
    ...imageSummary,
    apiResponse: {
      requestCount: responseSummaries.length,
      imageCount: images.length,
      responses: responseSummaries,
    },
  };
}

async function run() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) return help();
  const result = await generateImage(config);
  if (config.json || config.dryRun) return printJson(result);
  console.log(result.savedImages.join("\n"));
}

function isCliEntry() {
  return process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
}

if (isCliEntry()) run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

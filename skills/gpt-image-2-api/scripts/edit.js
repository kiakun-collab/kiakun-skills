#!/usr/bin/env node
import process from "node:process";
import { readFile } from "node:fs/promises";
import {
  DEFAULT_OUTPUT_ROOT,
  addOutputIndex,
  appendFormValue,
  buildApiPayload,
  buildDefaultImagePath,
  downloadReferenceImage,
  ensureFilesExist,
  extractGeneratedImages,
  loadAmbientEnv,
  mimeFor,
  postMultipart,
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
} from "./shared.js";

function help() {
  console.log(`Edit images through POST /v1/images/edits.

Usage:
  node scripts/edit.js --image source.png --prompt "Replace the background"
  node scripts/edit.js --url https://example.com/source.jpg --prompt "Change the style"

Required source (choose one type):
  --image <path>           Local PNG/JPEG/WebP; repeatable
  --url <url>              Public reference URL; repeatable

Required prompt input (choose one):
  --prompt <text>          Edit instructions
  --promptfile <path>      Load instructions from a UTF-8 file

Routing and image parameters:
  --profile <name>         auto | standard | vip (default: auto)
  --model <name>           Explicit gpt-image-2 or gpt-image-2-vip override
  --size <preset>          Listed output preset or ratio; not an arbitrary exact resolution
  --quality <level>        VIP only: auto | low | medium | high

Output:
  --output <path>          Image path (default: ${DEFAULT_OUTPUT_ROOT}/edited/...)
  --prompt-output <path>   Prompt archive path
  --dry-run                Print the selected model and request plan; do not call API
  --json                   Print structured result without image Base64
  -h, --help               Show help

Routing rule:
  One reference defaults to gpt-image-2. Two or more references automatically use gpt-image-2-vip.`);
}

function parseArgs(argv) {
  const config = { images: [], urls: [], json: false, dryRun: false, help: false };
  const names = new Map([
    ["--prompt", "prompt"],
    ["--promptfile", "promptFile"],
    ["--prompt-output", "promptOutput"],
    ["--output", "output"],
    ["--profile", "profile"],
    ["--model", "model"],
    ["--size", "size"],
    ["--quality", "quality"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "-h" || arg === "--help") config.help = true;
    else if (arg === "--json") config.json = true;
    else if (arg === "--dry-run") config.dryRun = true;
    else if (arg === "--image" || arg === "--url") {
      const value = argv[++index];
      if (!value) throw new Error(`Missing value for ${arg}`);
      config[arg === "--image" ? "images" : "urls"].push(value);
    } else if (names.has(arg)) {
      const value = argv[++index];
      if (!value) throw new Error(`Missing value for ${arg}`);
      config[names.get(arg)] = value;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  return config;
}

async function requestEdit(config, prompt, options, endpoint) {
  const form = new FormData();
  if (config.images.length > 0) {
    await ensureFilesExist(config.images);
    for (const imagePath of config.images) {
      const bytes = await readFile(imagePath);
      form.append(
        "image",
        new Blob([bytes], { type: mimeFor(imagePath) }),
        imagePath.split(/[\\/]/).pop(),
      );
    }
  } else {
    for (const rawUrl of config.urls) {
      const reference = await downloadReferenceImage(rawUrl);
      form.append(
        "image",
        new Blob([reference.bytes], { type: reference.contentType }),
        reference.filename,
      );
    }
  }

  const payload = buildApiPayload(options, { prompt });
  for (const [key, value] of Object.entries(payload)) appendFormValue(form, key, value);
  return postMultipart(endpoint, form);
}

async function run() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) return help();
  if (config.images.length === 0 && config.urls.length === 0) {
    throw new Error("Provide at least one --image or --url.");
  }
  if (config.images.length > 0 && config.urls.length > 0) {
    throw new Error("Do not mix --image and --url in the same request.");
  }

  await loadAmbientEnv();
  const prompt = await readPromptInput(config.prompt, config.promptFile);
  const referenceCount = config.images.length + config.urls.length;
  const options = resolveImageOptions(config, { referenceCount });
  const plan = publicPlan("edit", options, {
    sourceType: config.images.length > 0 ? "files" : "urls",
    referenceCount,
  });
  if (config.dryRun) return printJson(plan);

  const hint = slugify(prompt.split(/\s+/).slice(0, 8).join(" "), "edited-image");
  const promptPath = await savePrompt(prompt, config.promptOutput, hint);
  const outputPath = resolveOutput(config.output, buildDefaultImagePath("edit", hint));
  const response = await requestEdit(config, prompt, options, plan.endpoint);
  const images = await extractGeneratedImages(response);
  const savedImages = [];
  for (let index = 0; index < images.length; index += 1) {
    const imagePath = addOutputIndex(outputPath, index, images.length);
    await saveImage(imagePath, images[index]);
    savedImages.push(imagePath);
  }
  const imageSummary = summarizeSavedImages(images, savedImages, options.size);

  if (config.json) {
    return printJson({
      ...plan,
      savedImages,
      savedPrompt: promptPath,
      ...imageSummary,
      apiResponse: responseSummary(response),
    });
  }
  console.log(savedImages.join("\n"));
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

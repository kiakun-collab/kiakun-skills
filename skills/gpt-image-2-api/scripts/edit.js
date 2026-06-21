#!/usr/bin/env node
import process from "node:process";
import { readFile } from "node:fs/promises";
import {
  DEFAULT_OUTPUT_ROOT,
  addOutputIndex,
  appendFormValue,
  buildAtlasEditPayload,
  buildApiPayload,
  buildDefaultImagePath,
  downloadReferenceImage,
  ensureFilesExist,
  extractGeneratedImages,
  extractAtlasImages,
  loadAmbientEnv,
  mimeFor,
  postMultipart,
  printJson,
  publicPlan,
  readPromptInput,
  resolveImageOptions,
  resolveOutput,
  responseSummary,
  runAtlasEdit,
  saveImage,
  savePrompt,
  shouldUseAtlasFallback,
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
  --profile <name>         auto | standard | vip | atlas (hd is a vip compatibility alias)
  --model <name>           Explicit gpt-image-2, gpt-image-2-vip, or openai/gpt-image-2/edit
  --size <preset>          Listed output preset
  --quality <level>        VIP/Atlas only: auto | low | medium | high

Output:
  --output <path>          Image path (default: ${DEFAULT_OUTPUT_ROOT}/edited/...)
  --prompt-output <path>   Prompt archive path
  --dry-run                Print the selected model and request plan; do not call API
  --json                   Print structured result without image Base64
  -h, --help               Show help

Routing rule:
  One reference defaults to gpt-image-2. Multiple references or quality control use gpt-image-2-vip.
  VIP failures fall back to AtlasCloud when ATLASCLOUD_API_KEY is configured.`);
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

async function atlasImages(config) {
  if (config.urls.length > 0) return config.urls;
  await ensureFilesExist(config.images);
  return Promise.all(
    config.images.map(async (imagePath) => {
      const bytes = await readFile(imagePath);
      return `data:${mimeFor(imagePath)};base64,${bytes.toString("base64")}`;
    }),
  );
}

async function requestAtlasEdit(config, prompt, options) {
  const format = String(config.output || "").toLowerCase().endsWith(".jpg") ||
    String(config.output || "").toLowerCase().endsWith(".jpeg")
    ? "jpeg"
    : "png";
  return runAtlasEdit(
    buildAtlasEditPayload(options, {
      prompt,
      images: await atlasImages(config),
      outputFormat: format,
    }),
  );
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
  let response;
  let images;
  let usedProvider = plan.provider;
  let fallbackFrom = null;
  if (options.tier === "atlas") {
    response = await requestAtlasEdit(config, prompt, options);
    images = await extractAtlasImages(response.outputs);
  } else {
    try {
      response = await requestEdit(config, prompt, options, plan.endpoint);
      images = await extractGeneratedImages(response);
    } catch (error) {
      if (options.tier !== "vip" || !shouldUseAtlasFallback(error)) throw error;
      fallbackFrom = error instanceof Error ? error.message : String(error);
      response = await requestAtlasEdit(config, prompt, options);
      images = await extractAtlasImages(response.outputs);
      usedProvider = "atlascloud";
    }
  }
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
      usedProvider,
      fallbackFrom,
      savedImages,
      savedPrompt: promptPath,
      ...imageSummary,
      apiResponse:
        usedProvider === "atlascloud"
          ? {
              predictionId: response.predictionId,
              imageCount: images.length,
              hasNsfwContents: response.hasNsfwContents,
            }
          : responseSummary(response),
    });
  }
  console.log(savedImages.join("\n"));
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

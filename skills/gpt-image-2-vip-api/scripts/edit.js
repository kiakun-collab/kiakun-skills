#!/usr/bin/env node
import process from "node:process";
import { readFile } from "node:fs/promises";
import {
  DEFAULT_IMAGE_DIR,
  DEFAULT_MODEL,
  DEFAULT_QUALITY,
  DEFAULT_SIZE,
  addOutputIndex,
  appendFormValue,
  buildBaseUrl,
  buildDefaultImagePath,
  ensureFilesExist,
  extractGeneratedImages,
  loadAmbientEnv,
  mimeFor,
  postJson,
  postMultipart,
  printJson,
  readPromptInput,
  resolveImageOptions,
  resolveOutput,
  responseSummary,
  saveImage,
  savePrompt,
  slugify,
} from "./shared.js";

function help() {
  console.log(`Usage:
  node scripts/edit.js --image source.png --prompt "Replace the background"
  node scripts/edit.js --url https://example.com/source.jpg --prompt "Change the style"

Options:
  --image <path>           Local reference image; repeatable
  --url <url>              Public reference URL; repeatable
  --prompt <text>          Edit prompt
  --promptfile <path>      Load prompt from a file
  --prompt-output <path>   Save prompt to a specific path
  --output <path>          Output image path (default: ${DEFAULT_IMAGE_DIR}/...)
  --model <name>           Model (default: ${DEFAULT_MODEL})
  --size <WxH>             Pixel dimensions (default: ${DEFAULT_SIZE})
  --quality <level>        auto | low | medium | high (default: ${DEFAULT_QUALITY})
  --json                   Print structured output without Base64
  -h, --help               Show help`);
}

function parseArgs(argv) {
  const config = { images: [], urls: [], json: false, help: false };
  const names = new Map([
    ["--prompt", "prompt"],
    ["--promptfile", "promptFile"],
    ["--prompt-output", "promptOutput"],
    ["--output", "output"],
    ["--model", "model"],
    ["--size", "size"],
    ["--quality", "quality"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "-h" || arg === "--help") {
      config.help = true;
    } else if (arg === "--json") {
      config.json = true;
    } else if (arg === "--image" || arg === "--url") {
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

async function requestEdit(config, prompt, options, requestUrl) {
  if (config.images.length > 0) {
    await ensureFilesExist(config.images);
    const form = new FormData();
    for (const imagePath of config.images) {
      const bytes = await readFile(imagePath);
      form.append(
        "image",
        new Blob([bytes], { type: mimeFor(imagePath) }),
        imagePath.split(/[\\/]/).pop(),
      );
    }
    form.append("model", options.model);
    form.append("prompt", prompt);
    appendFormValue(form, "size", options.size);
    appendFormValue(form, "quality", options.quality);
    return postMultipart(requestUrl, form);
  }

  return postJson(requestUrl, {
    model: options.model,
    size: options.size,
    quality: options.quality,
    prompt,
    urls: config.urls,
  });
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
  const hint = slugify(prompt.split(/\s+/).slice(0, 8).join(" "), "edited-image");
  const promptPath = await savePrompt(prompt, config.promptOutput, hint);
  const outputPath = resolveOutput(config.output, buildDefaultImagePath("edit", hint));
  const options = resolveImageOptions(config);
  const requestUrl = `${buildBaseUrl()}/images/edits`;
  const response = await requestEdit(config, prompt, options, requestUrl);
  const images = await extractGeneratedImages(response);
  const savedImages = [];
  for (let index = 0; index < images.length; index += 1) {
    const imagePath = addOutputIndex(outputPath, index, images.length);
    await saveImage(imagePath, images[index]);
    savedImages.push(imagePath);
  }

  if (config.json) {
    return printJson({
      savedImages,
      savedPrompt: promptPath,
      requestUrl,
      options,
      sourceType: config.images.length > 0 ? "files" : "urls",
      apiResponse: responseSummary(response),
    });
  }
  console.log(savedImages.join("\n"));
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

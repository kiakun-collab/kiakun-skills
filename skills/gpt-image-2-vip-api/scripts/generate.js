#!/usr/bin/env node
import process from "node:process";
import {
  DEFAULT_IMAGE_DIR,
  DEFAULT_MODEL,
  DEFAULT_QUALITY,
  DEFAULT_SIZE,
  addOutputIndex,
  buildBaseUrl,
  buildDefaultImagePath,
  extractGeneratedImages,
  loadAmbientEnv,
  postJson,
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
  node scripts/generate.js --prompt "A premium product photo"

Options:
  --prompt <text>          Prompt text
  --promptfile <path>      Load prompt from a file
  --prompt-output <path>   Save prompt to a specific path
  --image <path>           Output image path (default: ${DEFAULT_IMAGE_DIR}/...)
  --model <name>           Model (default: ${DEFAULT_MODEL})
  --size <WxH>             Pixel dimensions (default: ${DEFAULT_SIZE})
  --quality <level>        auto | low | medium | high (default: ${DEFAULT_QUALITY})
  --n <count>              Number of images (default: 1)
  --json                   Print structured output without Base64
  -h, --help               Show help`);
}

function parseArgs(argv) {
  const config = { json: false, help: false };
  const names = new Map([
    ["--prompt", "prompt"],
    ["--promptfile", "promptFile"],
    ["--prompt-output", "promptOutput"],
    ["--image", "image"],
    ["--model", "model"],
    ["--size", "size"],
    ["--quality", "quality"],
    ["--n", "n"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "-h" || arg === "--help") {
      config.help = true;
    } else if (arg === "--json") {
      config.json = true;
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

async function run() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) return help();

  await loadAmbientEnv();
  const prompt = await readPromptInput(config.prompt, config.promptFile);
  const hint = slugify(prompt.split(/\s+/).slice(0, 8).join(" "), "generated-image");
  const promptPath = await savePrompt(prompt, config.promptOutput, hint);
  const outputPath = resolveOutput(config.image, buildDefaultImagePath("generate", hint));
  const options = resolveImageOptions(config);
  const requestUrl = `${buildBaseUrl()}/images/generations`;
  const response = await postJson(requestUrl, {
    ...options,
    prompt,
    response_format: "b64_json",
  });
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
      apiResponse: responseSummary(response),
    });
  }
  console.log(savedImages.join("\n"));
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

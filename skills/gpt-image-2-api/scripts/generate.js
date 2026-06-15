#!/usr/bin/env node
import process from "node:process";
import {
  DEFAULT_OUTPUT_ROOT,
  addOutputIndex,
  buildApiPayload,
  buildDefaultImagePath,
  extractGeneratedImages,
  loadAmbientEnv,
  postJson,
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
  console.log(`Generate an image through POST /v1/images/generations.

Usage:
  node scripts/generate.js --prompt "A cozy reading corner"

Required input (choose one):
  --prompt <text>          Prompt text
  --promptfile <path>      Load prompt from a UTF-8 file

Routing and image parameters:
  --profile <name>         auto | standard (HD currently requires an edit reference)
  --model <name>           Explicit gpt-image-2 override
  --size <preset>          Listed output preset or ratio; not an arbitrary exact resolution
  --quality <level>        Reserved for HD editing
  --n <count>              Number of images, 1-10 (default: 1)

Output:
  --output <path>          Image path (default: ${DEFAULT_OUTPUT_ROOT}/generated/...)
  --image <path>           Backward-compatible alias for --output
  --prompt-output <path>   Prompt archive path
  --dry-run                Print the selected model and request plan; do not call API
  --json                   Print structured result without image Base64
  -h, --help               Show help

Cost-aware examples:
  node scripts/generate.js --prompt "A cat by a window"
  node scripts/generate.js --size 1536x1024 --promptfile poster.md`);
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

async function run() {
  const config = parseArgs(process.argv.slice(2));
  if (config.help) return help();

  await loadAmbientEnv();
  const prompt = await readPromptInput(config.prompt, config.promptFile);
  const options = resolveImageOptions(config);
  if (options.tier === "hd") {
    throw new Error("AtlasCloud HD currently requires at least one reference image; use edit.js.");
  }
  const plan = publicPlan("generate", options);
  if (config.dryRun) return printJson(plan);

  const hint = slugify(prompt.split(/\s+/).slice(0, 8).join(" "), "generated-image");
  const promptPath = await savePrompt(prompt, config.promptOutput, hint);
  const outputPath = resolveOutput(config.output, buildDefaultImagePath("generate", hint));
  const images = [];
  const responseSummaries = [];
  while (images.length < options.n) {
    const remaining = options.n - images.length;
    const response = await postJson(
      plan.endpoint,
      buildApiPayload(options, {
        prompt,
        n: remaining,
        response_format: "b64_json",
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

  if (config.json) {
    return printJson({
      ...plan,
      savedImages,
      savedPrompt: promptPath,
      ...imageSummary,
      apiResponse: {
        requestCount: responseSummaries.length,
        imageCount: images.length,
        responses: responseSummaries,
      },
    });
  }
  console.log(savedImages.join("\n"));
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});

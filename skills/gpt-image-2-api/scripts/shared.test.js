import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cp, mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  buildAtlasEditPayload,
  buildDefaultImagePath,
  imageMetadata,
  readPromptInput,
  resolveImageOptions,
} from "./shared.js";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

function runNode(script, args, cwd, env = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(SCRIPT_DIR, script), ...args], {
      cwd,
      env: { ...process.env, ...env },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.stderr.on("data", (chunk) => (stderr += chunk));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(`Process exited ${code}: ${stderr || stdout}`));
    });
  });
}

async function withGateway(handler, callback) {
  const server = createServer(handler);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    await callback(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
}

function testEnv(baseUrl) {
  return {
    OPENAI_API_KEY: "test-key",
    OPENAI_BASE_URL: baseUrl,
    ATLASCLOUD_API_KEY: "atlas-test-key",
    ATLASCLOUD_BASE_URL: `${baseUrl}/api/v1/model`,
    ATLASCLOUD_POLL_INTERVAL_MS: "100",
    ATLASCLOUD_POLL_TIMEOUT_MS: "5000",
    GPT_IMAGE_PROFILE: "auto",
    GPT_IMAGE_STANDARD_SIZE: "1024x1024",
    GPT_IMAGE_VIP_SIZE: "2048x2048",
    GPT_IMAGE_VIP_QUALITY: "high",
    GPT_IMAGE_ATLAS_SIZE: "2048x2048",
    GPT_IMAGE_ATLAS_QUALITY: "high",
    GPT_IMAGE_N: "1",
    OPENAI_IMAGE_MAX_RETRIES: "0",
    // Old global settings must not force this skill onto VIP.
    OPENAI_IMAGE_MODEL: "gpt-image-2-vip",
    OPENAI_IMAGE_SIZE: "2048x2048",
    OPENAI_IMAGE_QUALITY: "high",
  };
}

test("auto defaults daily generation to standard model", () => {
  assert.deepEqual(resolveImageOptions(), {
    requestedProfile: "auto",
    tier: "standard",
    model: "gpt-image-2",
    size: "1024x1024",
    quality: null,
    n: 1,
    routeReasons: ["cost-saving-default"],
  });
});

test("rejects image counts above the paid-request safety limit", () => {
  assert.throws(
    () => resolveImageOptions({ n: 11 }),
    /n must be an integer between 1 and 10/,
  );
});

test("auto selects VIP for a quality request", () => {
  const options = resolveImageOptions({ size: "3840x2160", quality: "high" });
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.tier, "vip");
  assert.deepEqual(options.routeReasons, [
    "quality-control-requested",
    "2k-or-4k-preset-requested",
  ]);
});

test("auto selects VIP for multiple reference images", () => {
  const options = resolveImageOptions({}, { referenceCount: 2 });
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.size, "2048x2048");
  assert.deepEqual(options.routeReasons, ["multiple-reference-images"]);
});

test("VIP accepts ratio size tokens for max model", () => {
  const options = resolveImageOptions({ model: "gpt-image-2-max", size: "9:16", quality: "high" });
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.tier, "vip");
  assert.equal(options.size, "9:16");
  assert.equal(options.quality, "high");
});

test("VIP generation maps ratio tokens to max 2K presets and omits quality", () => {
  const options = resolveImageOptions(
    { model: "gpt-image-2-max", size: "9:16", quality: "high" },
    { operation: "generate" },
  );
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.tier, "vip");
  assert.equal(options.size, "1440x2560");
  assert.equal(options.quality, null);
});

test("standard generation maps portrait ratios to documented 1K presets", () => {
  const options = resolveImageOptions({ size: "9:16" }, { operation: "generate" });
  assert.equal(options.model, "gpt-image-2");
  assert.equal(options.tier, "standard");
  assert.equal(options.size, "720x1280");
});

test("VIP generation maps standard create sizes to observed max 2K presets", () => {
  const options = resolveImageOptions(
    { model: "gpt-image-2-max", size: "1024x1536" },
    { operation: "generate" },
  );
  assert.equal(options.size, "1664x2496");
});

test("VIP generation accepts documented aifast max 4K pixel sizes", () => {
  const options = resolveImageOptions(
    { model: "gpt-image-2-max", size: "2160x3840" },
    { operation: "generate" },
  );
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.size, "2160x3840");
});

test("standard profile rejects VIP-only parameters", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "standard", quality: "high" }),
    /quality is only supported/,
  );
  assert.throws(
    () => resolveImageOptions({ profile: "standard", size: "2048x2048" }),
    /2K\/4K output presets require/,
  );
});

test("rejects arbitrary resolutions that are not documented presets", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "standard", size: "1600x900" }),
    /requires profile vip/,
  );
  assert.throws(
    () => resolveImageOptions({ profile: "vip", size: "4096x4096" }),
    /Unsupported VIP output preset/,
  );
});

test("accepts every AtlasCloud schema size", () => {
  for (const size of [
    "1024x1024",
    "1024x1536",
    "1536x1024",
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
  ]) {
    assert.equal(resolveImageOptions({ profile: "atlas", size }).size, size);
  }
});

test("AtlasCloud payload enforces one to ten reference images", () => {
  const options = resolveImageOptions({ profile: "atlas" }, { referenceCount: 1 });
  assert.throws(
    () => buildAtlasEditPayload(options, { prompt: "test", images: [] }),
    /between 1 and 10/,
  );
  assert.throws(
    () =>
      buildAtlasEditPayload(options, {
        prompt: "test",
        images: Array.from({ length: 11 }, (_, index) => `https://example.com/${index}.png`),
      }),
    /between 1 and 10/,
  );
});

test("conflicting explicit profile and model are rejected", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "vip", model: "gpt-image-2" }),
    /conflicts with explicit model/,
  );
});

test("retired gpt-image-2-vip model id maps to gpt-image-2-max", () => {
  const options = resolveImageOptions({ model: "gpt-image-2-vip" });
  assert.equal(options.model, "gpt-image-2-max");
  assert.equal(options.tier, "vip");
});

test("reads PNG metadata for saved output verification", () => {
  assert.deepEqual(imageMetadata(PNG), {
    format: "png",
    width: 1,
    height: 1,
    bytes: PNG.length,
  });
});

test("default image paths are unique within the same process", () => {
  const first = buildDefaultImagePath("generate", "same prompt");
  const second = buildDefaultImagePath("generate", "same prompt");
  assert.notEqual(first, second);
});

test("requires exactly one prompt source", async () => {
  await assert.rejects(() => readPromptInput(), /exactly one prompt source/);
  await assert.rejects(
    () => readPromptInput("inline prompt", "prompt.md"),
    /exactly one prompt source/,
  );
});

test("dry-run explains routing without an API key", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "image-dry-run-"));
  try {
    const { stdout } = await runNode(
      "generate.js",
      ["--prompt", "simple daily image", "--dry-run"],
      cwd,
      {
        OPENAI_API_KEY: "",
        OPENAI_BASE_URL: "https://aifast.site/v1",
        GPT_IMAGE_PROFILE: "auto",
        OPENAI_IMAGE_MODEL: "gpt-image-2-vip",
        HOME: cwd,
        USERPROFILE: cwd,
      },
    );
    const plan = JSON.parse(stdout);
    assert.equal(plan.endpoint, "https://aifast.site/v1/images/generations");
    assert.equal(plan.model, "gpt-image-2");
    assert.deepEqual(plan.routeReasons, ["cost-saving-default"]);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("check-config loads env from the skill root when run from another cwd", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "skill-root-env-cwd-"));
  const skillRoot = await mkdtemp(path.join(tmpdir(), "skill-root-env-skill-"));
  try {
    await mkdir(path.join(skillRoot, "scripts"), { recursive: true });
    await cp(SCRIPT_DIR, path.join(skillRoot, "scripts"), { recursive: true });
    await writeFile(
      path.join(skillRoot, ".env"),
      "OPENAI_API_KEY=skill-root-test-key\nOPENAI_BASE_URL=https://example.test/v1\n",
    );
    const { stdout } = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [path.join(skillRoot, "scripts", "check-config.js"), "--json"], {
        cwd,
        env: {
          ...process.env,
          OPENAI_API_KEY: "",
          OPENAI_BASE_URL: "",
          HOME: cwd,
          USERPROFILE: cwd,
        },
        stdio: ["ignore", "pipe", "pipe"],
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (chunk) => (stdout += chunk));
      child.stderr.on("data", (chunk) => (stderr += chunk));
      child.on("error", reject);
      child.on("close", (code) => {
        if (code === 0) resolve({ stdout, stderr });
        else reject(new Error(`Process exited ${code}: ${stderr || stdout}`));
      });
    });
    const config = JSON.parse(stdout);
    assert.equal(config.ready, true);
    assert.equal(config.hasApiKey, true);
    assert.equal(config.baseUrl, "https://example.test/v1");
  } finally {
    await rm(cwd, { recursive: true, force: true });
    await rm(skillRoot, { recursive: true, force: true });
  }
});

test("standard generation omits quality and saves every image", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "standard-generate-"));
  let body;
  try {
    await withGateway(
      async (request, response) => {
        assert.equal(request.url, "/v1/images/generations");
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        response.writeHead(200, { "content-type": "application/json" });
        response.end(
          JSON.stringify({
            data: [
              { b64_json: PNG.toString("base64") },
              { b64_json: PNG.toString("base64") },
            ],
          }),
        );
      },
      (baseUrl) =>
        runNode(
          "generate.js",
          [
            "--prompt",
            "test image",
            "--n",
            "2",
            "--output",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.equal(body.model, "gpt-image-2");
    assert.equal(body.size, "1024x1024");
    assert.equal("quality" in body, false);
    assert.equal("response_format" in body, false);
    assert.deepEqual(await readFile(path.join(cwd, "result-1.png")), PNG);
    assert.deepEqual(await readFile(path.join(cwd, "result-2.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("generation fills missing images when the gateway ignores n", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "generation-backfill-"));
  let requestCount = 0;
  try {
    await withGateway(
      async (request, response) => {
        requestCount += 1;
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        assert.equal(body.n, 3 - requestCount);
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "generate.js",
          [
            "--prompt",
            "three images",
            "--n",
            "2",
            "--output",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.equal(requestCount, 2);
    assert.deepEqual(await readFile(path.join(cwd, "result-1.png")), PNG);
    assert.deepEqual(await readFile(path.join(cwd, "result-2.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("generation retries 429 and then succeeds", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "generation-retry-"));
  let requestCount = 0;
  try {
    await withGateway(
      async (request, response) => {
        requestCount += 1;
        for await (const _chunk of request) {
          // Drain the request body before responding.
        }
        if (requestCount === 1) {
          response.writeHead(429, {
            "content-type": "application/json",
            "retry-after": "0",
          });
          response.end(JSON.stringify({ error: { message: "rate limited" } }));
          return;
        }
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "generate.js",
          [
            "--prompt",
            "retry image",
            "--output",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          { ...testEnv(baseUrl), OPENAI_IMAGE_MAX_RETRIES: "1" },
        ),
    );
    assert.equal(requestCount, 2);
    assert.deepEqual(await readFile(path.join(cwd, "result.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("generated image URL downloads retry 5xx and then save", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "generated-download-retry-"));
  let imageRequests = 0;
  try {
    await withGateway(
      async (request, response) => {
        if (request.method === "GET" && request.url === "/result.png") {
          imageRequests += 1;
          if (imageRequests === 1) {
            response.writeHead(500, { "content-type": "text/plain" });
            response.end("temporary image host failure");
            return;
          }
          response.writeHead(200, { "content-type": "image/png" });
          response.end(PNG);
          return;
        }
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        response.writeHead(200, { "content-type": "application/json" });
        response.end(
          JSON.stringify({
            data: [{ url: `http://127.0.0.1:${request.socket.localPort}/result.png` }],
          }),
        );
      },
      (baseUrl) =>
        runNode(
          "generate.js",
          [
            "--profile",
            "vip",
            "--prompt",
            "retry downloaded image",
            "--output",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          { ...testEnv(baseUrl), OPENAI_IMAGE_MAX_RETRIES: "1" },
        ),
    );
    assert.equal(imageRequests, 2);
    assert.deepEqual(await readFile(path.join(cwd, "result.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("generated image URL downloads do not retry 404", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "generated-download-no-retry-"));
  let imageRequests = 0;
  try {
    await assert.rejects(
      () =>
        withGateway(
          async (request, response) => {
            if (request.method === "GET" && request.url === "/missing.png") {
              imageRequests += 1;
              response.writeHead(404, { "content-type": "text/plain" });
              response.end("missing");
              return;
            }
            const chunks = [];
            for await (const chunk of request) chunks.push(chunk);
            response.writeHead(200, { "content-type": "application/json" });
            response.end(
              JSON.stringify({
                data: [{ url: `http://127.0.0.1:${request.socket.localPort}/missing.png` }],
              }),
            );
          },
          (baseUrl) =>
            runNode(
              "generate.js",
              [
                "--profile",
                "vip",
                "--prompt",
                "missing downloaded image",
                "--output",
                "result.png",
                "--prompt-output",
                "prompt.md",
              ],
              cwd,
              { ...testEnv(baseUrl), OPENAI_IMAGE_MAX_RETRIES: "2" },
            ),
        ),
      /Failed to download generated image \(404\)/,
    );
    assert.equal(imageRequests, 1);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("generation does not retry a 400 response", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "generation-no-retry-"));
  let requestCount = 0;
  try {
    await assert.rejects(
      () =>
        withGateway(
          async (request, response) => {
            requestCount += 1;
            for await (const _chunk of request) {
              // Drain the request body before responding.
            }
            response.writeHead(400, { "content-type": "application/json" });
            response.end(JSON.stringify({ error: { message: "invalid parameters" } }));
          },
          (baseUrl) =>
            runNode(
              "generate.js",
              [
                "--prompt",
                "invalid image",
                "--output",
                "result.png",
                "--prompt-output",
                "prompt.md",
              ],
              cwd,
              { ...testEnv(baseUrl), OPENAI_IMAGE_MAX_RETRIES: "2" },
            ),
        ),
      /Image API error \(400\): invalid parameters/,
    );
    assert.equal(requestCount, 1);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("VIP generation uses max model but omits unsupported quality", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-generate-"));
  let body;
  try {
    await withGateway(
      async (request, response) => {
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "generate.js",
          [
            "--profile",
            "vip",
            "--prompt",
            "complex infographic",
            "--size",
            "9:16",
            "--quality",
            "high",
            "--output",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.equal(body.model, "gpt-image-2-max");
    assert.equal(body.size, "1440x2560");
    assert.equal("quality" in body, false);
    assert.equal("response_format" in body, false);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("single-reference edit uses standard model", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "standard-edit-"));
  let multipart = "";
  try {
    await writeFile(path.join(cwd, "one.png"), PNG);
    await withGateway(
      async (request, response) => {
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        multipart = Buffer.concat(chunks).toString("latin1");
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "edit.js",
          [
            "--image",
            "one.png",
            "--prompt",
            "replace background",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.match(multipart, /name="model"\r\n\r\ngpt-image-2/);
    assert.doesNotMatch(multipart, /name="quality"/);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("URL-reference edit downloads the image and uploads multipart", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "url-edit-"));
  let multipart = "";
  try {
    await withGateway(
      async (request, response) => {
        if (request.method === "GET" && request.url === "/reference.png") {
          response.writeHead(200, { "content-type": "image/png" });
          response.end(PNG);
          return;
        }
        assert.equal(request.method, "POST");
        assert.equal(request.url, "/v1/images/edits");
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        multipart = Buffer.concat(chunks).toString("latin1");
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "edit.js",
          [
            "--url",
            `${baseUrl}/reference.png`,
            "--prompt",
            "change style",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.match(multipart, /name="image"; filename="reference.png"/);
    assert.match(multipart, /name="model"\r\n\r\ngpt-image-2/);
    assert.doesNotMatch(multipart, /name="urls"/);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("multi-URL reference edit downloads in parallel but preserves multipart order", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "multi-url-edit-order-"));
  let multipart = "";
  try {
    await withGateway(
      async (request, response) => {
        if (request.method === "GET" && request.url === "/first.png") {
          await new Promise((resolve) => setTimeout(resolve, 50));
          response.writeHead(200, { "content-type": "image/png" });
          response.end(PNG);
          return;
        }
        if (request.method === "GET" && request.url === "/second.png") {
          response.writeHead(200, { "content-type": "image/png" });
          response.end(PNG);
          return;
        }
        assert.equal(request.method, "POST");
        assert.equal(request.url, "/v1/images/edits");
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        multipart = Buffer.concat(chunks).toString("latin1");
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "edit.js",
          [
            "--url",
            `${baseUrl}/first.png`,
            "--url",
            `${baseUrl}/second.png`,
            "--prompt",
            "combine remote references",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.ok(
      multipart.indexOf('filename="first.png"') < multipart.indexOf('filename="second.png"'),
    );
    assert.match(multipart, /name="model"\r\n\r\ngpt-image-2-max/);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("multi-reference edit uses VIP first", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-edit-"));
  let multipart = "";
  try {
    await writeFile(path.join(cwd, "one.png"), PNG);
    await writeFile(path.join(cwd, "two.png"), PNG);
    await withGateway(
      async (request, response) => {
        assert.equal(request.url, "/v1/images/edits");
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        multipart = Buffer.concat(chunks).toString("latin1");
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      (baseUrl) =>
        runNode(
          "edit.js",
          [
            "--image",
            "one.png",
            "--image",
            "two.png",
            "--prompt",
            "combine references",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.equal((multipart.match(/name="image"/g) || []).length, 2);
    assert.match(multipart, /name="model"\r\n\r\ngpt-image-2-max/);
    assert.match(multipart, /name="quality"\r\n\r\nhigh/);
    assert.deepEqual(await readFile(path.join(cwd, "edited.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("VIP edit falls back to AtlasCloud after upstream failure", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-fallback-edit-"));
  let vipRequests = 0;
  let atlasSubmitted;
  try {
    await writeFile(path.join(cwd, "one.png"), PNG);
    await writeFile(path.join(cwd, "two.png"), PNG);
    await withGateway(
      async (request, response) => {
        if (request.method === "POST" && request.url === "/v1/images/edits") {
          vipRequests += 1;
          for await (const _chunk of request) {
            // Drain the multipart body before failing VIP.
          }
          response.writeHead(500, { "content-type": "application/json" });
          response.end(JSON.stringify({ error: { message: "vip unavailable" } }));
          return;
        }
        if (request.method === "POST" && request.url === "/api/v1/model/generateImage") {
          const chunks = [];
          for await (const chunk of request) chunks.push(chunk);
          atlasSubmitted = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          assert.equal(request.headers.authorization, "Bearer atlas-test-key");
          response.writeHead(200, { "content-type": "application/json" });
          response.end(JSON.stringify({ id: "prediction-1", status: "created", outputs: [] }));
          return;
        }
        if (request.method === "GET" && request.url === "/api/v1/model/result/prediction-1") {
          response.writeHead(200, { "content-type": "application/json" });
          response.end(
            JSON.stringify({
              id: "prediction-1",
              status: "completed",
              outputs: [`http://127.0.0.1:${request.socket.localPort}/result.png`],
              has_nsfw_contents: [false],
            }),
          );
          return;
        }
        if (request.method === "GET" && request.url === "/result.png") {
          response.writeHead(200, { "content-type": "image/png" });
          response.end(PNG);
          return;
        }
        response.writeHead(404).end();
      },
      (baseUrl) =>
        runNode(
          "edit.js",
          [
            "--image",
            "one.png",
            "--image",
            "two.png",
            "--prompt",
            "combine references",
            "--size",
            "2560x1440",
            "--quality",
            "high",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
            "--json",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.equal(vipRequests, 1);
    assert.equal(atlasSubmitted.model, "openai/gpt-image-2/edit");
    assert.equal(atlasSubmitted.size, "2048x1152");
    assert.equal(atlasSubmitted.quality, "high");
    assert.equal(atlasSubmitted.images.length, 2);
    assert.match(atlasSubmitted.images[0], /^data:image\/png;base64,/);
    assert.deepEqual(await readFile(path.join(cwd, "edited.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("batch promptlist dry-run routes every non-empty line", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "batch-promptlist-"));
  try {
    await writeFile(
      path.join(cwd, "prompts.txt"),
      "a red fox in snow\n# a comment line\n\na blue whale at dusk\n",
    );
    const { stdout } = await runNode(
      "batch.js",
      ["--promptlist", "prompts.txt", "--dry-run", "--json"],
      cwd,
      { OPENAI_API_KEY: "", GPT_IMAGE_PROFILE: "auto", HOME: cwd, USERPROFILE: cwd },
    );
    const summary = JSON.parse(stdout);
    assert.equal(summary.total, 2);
    assert.equal(summary.succeeded, 2);
    assert.equal(summary.results[0].operation, "generate");
    assert.equal(summary.results[0].result.model, "gpt-image-2");
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("batch manifest runs mixed generate and edit tasks", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "batch-manifest-"));
  const seen = [];
  try {
    await writeFile(path.join(cwd, "one.png"), PNG);
    await writeFile(
      path.join(cwd, "tasks.json"),
      JSON.stringify([
        { prompt: "text image", output: "gen.png" },
        { prompt: "edit it", images: ["one.png"], output: "edited.png" },
      ]),
    );
    await withGateway(
      async (request, response) => {
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        seen.push(request.url);
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      async (baseUrl) => {
        const { stdout } = await runNode(
          "batch.js",
          ["--batch", "tasks.json", "--concurrency", "1", "--json"],
          cwd,
          testEnv(baseUrl),
        );
        const summary = JSON.parse(stdout);
        assert.equal(summary.total, 2);
        assert.equal(summary.succeeded, 2);
        assert.equal(summary.failed, 0);
      },
    );
    assert.ok(seen.includes("/v1/images/generations"));
    assert.ok(seen.includes("/v1/images/edits"));
    assert.deepEqual(await readFile(path.join(cwd, "gen.png")), PNG);
    assert.deepEqual(await readFile(path.join(cwd, "edited.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("batch continues past a failed task and reports it", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "batch-continue-"));
  try {
    await writeFile(
      path.join(cwd, "tasks.json"),
      JSON.stringify([
        { prompt: "ok image", output: "ok.png" },
        { prompt: "broken edit", images: ["missing.png"], output: "bad.png" },
      ]),
    );
    await withGateway(
      async (request, response) => {
        const chunks = [];
        for await (const chunk of request) chunks.push(chunk);
        response.writeHead(200, { "content-type": "application/json" });
        response.end(JSON.stringify({ data: [{ b64_json: PNG.toString("base64") }] }));
      },
      async (baseUrl) => {
        const { stdout } = await runNode(
          "batch.js",
          ["--batch", "tasks.json", "--concurrency", "1", "--json"],
          cwd,
          testEnv(baseUrl),
        );
        const summary = JSON.parse(stdout);
        assert.equal(summary.total, 2);
        assert.equal(summary.succeeded, 1);
        assert.equal(summary.failed, 1);
        const failure = summary.results.find((r) => !r.ok);
        assert.match(failure.error, /not found/);
      },
    );
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("batch rejects providing both inputs", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "batch-both-"));
  try {
    await writeFile(path.join(cwd, "prompts.txt"), "one\n");
    await writeFile(path.join(cwd, "tasks.json"), "[]");
    await assert.rejects(
      () =>
        runNode(
          "batch.js",
          ["--promptlist", "prompts.txt", "--batch", "tasks.json"],
          cwd,
          { OPENAI_API_KEY: "", HOME: cwd, USERPROFILE: cwd },
        ),
      /exactly one input/,
    );
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { imageMetadata, readPromptInput, resolveImageOptions } from "./shared.js";

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
    GPT_IMAGE_PROFILE: "auto",
    GPT_IMAGE_STANDARD_SIZE: "1024x1024",
    GPT_IMAGE_VIP_SIZE: "2048x2048",
    GPT_IMAGE_VIP_QUALITY: "high",
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

test("auto selects VIP for a supported 2K preset and quality request", () => {
  const options = resolveImageOptions({ size: "2560x1440", quality: "high" });
  assert.equal(options.model, "gpt-image-2-vip");
  assert.equal(options.tier, "vip");
  assert.deepEqual(options.routeReasons, [
    "quality-control-requested",
    "2k-or-4k-preset-requested",
  ]);
});

test("auto selects VIP for multiple reference images", () => {
  const options = resolveImageOptions({}, { referenceCount: 2 });
  assert.equal(options.model, "gpt-image-2-vip");
  assert.equal(options.size, "2048x2048");
  assert.deepEqual(options.routeReasons, ["multiple-reference-images"]);
});

test("standard profile rejects VIP-only parameters", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "standard", quality: "high" }),
    /quality is only supported/,
  );
  assert.throws(
    () => resolveImageOptions({ profile: "standard", size: "3840x2160" }),
    /2K\/4K output presets require/,
  );
});

test("rejects arbitrary resolutions that are not documented presets", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "standard", size: "1600x900" }),
    /arbitrary resolutions are not supported/,
  );
  assert.throws(
    () => resolveImageOptions({ profile: "vip", size: "4096x4096" }),
    /arbitrary resolutions are not supported/,
  );
});

test("conflicting explicit profile and model are rejected", () => {
  assert.throws(
    () => resolveImageOptions({ profile: "vip", model: "gpt-image-2" }),
    /conflicts with explicit model/,
  );
});

test("reads PNG metadata for saved output verification", () => {
  assert.deepEqual(imageMetadata(PNG), {
    format: "png",
    width: 1,
    height: 1,
    bytes: PNG.length,
  });
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
    assert.equal(body.response_format, "b64_json");
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

test("VIP generation sends size and quality", async () => {
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
            "2560x1440",
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
    assert.equal(body.model, "gpt-image-2-vip");
    assert.equal(body.size, "2560x1440");
    assert.equal(body.quality, "high");
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

test("multi-reference edit automatically uses VIP", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-edit-"));
  let multipart = "";
  try {
    await writeFile(path.join(cwd, "one.png"), PNG);
    await writeFile(path.join(cwd, "two.png"), PNG);
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
    assert.match(multipart, /name="model"\r\n\r\ngpt-image-2-vip/);
    assert.match(multipart, /name="quality"\r\n\r\nhigh/);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

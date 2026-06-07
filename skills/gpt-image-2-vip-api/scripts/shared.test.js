import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { resolveImageOptions } from "./shared.js";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

function runNode(script, args, cwd, env) {
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
    OPENAI_IMAGE_MODEL: "gpt-image-2-vip",
    OPENAI_IMAGE_SIZE: "2048x2048",
    OPENAI_IMAGE_QUALITY: "high",
    OPENAI_IMAGE_N: "1",
    OPENAI_IMAGE_MAX_RETRIES: "0",
  };
}

test("uses VIP 2K high defaults", () => {
  const keys = [
    "OPENAI_IMAGE_MODEL",
    "OPENAI_IMAGE_SIZE",
    "OPENAI_IMAGE_QUALITY",
    "OPENAI_IMAGE_N",
  ];
  const original = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
  keys.forEach((key) => delete process.env[key]);
  try {
    assert.deepEqual(resolveImageOptions(), {
      model: "gpt-image-2-vip",
      size: "2048x2048",
      quality: "high",
      n: 1,
    });
  } finally {
    for (const key of keys) {
      if (original[key] === undefined) delete process.env[key];
      else process.env[key] = original[key];
    }
  }
});

test("generation sends documented fields and saves all images", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-generate-"));
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
            "--image",
            "result.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.deepEqual(Object.keys(body).sort(), [
      "model",
      "n",
      "prompt",
      "quality",
      "response_format",
      "size",
    ]);
    assert.equal(body.model, "gpt-image-2-vip");
    assert.equal(body.size, "2048x2048");
    assert.equal(body.quality, "high");
    assert.deepEqual(await readFile(path.join(cwd, "result-1.png")), PNG);
    assert.deepEqual(await readFile(path.join(cwd, "result-2.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("local edit uploads multiple image fields", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-edit-files-"));
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
            "combine",
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
    assert.deepEqual(await readFile(path.join(cwd, "edited.png")), PNG);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("URL edit sends the gateway urls extension", async () => {
  const cwd = await mkdtemp(path.join(tmpdir(), "vip-edit-urls-"));
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
          "edit.js",
          [
            "--url",
            "https://example.com/one.jpg",
            "--url",
            "https://example.com/two.jpg",
            "--prompt",
            "combine",
            "--output",
            "edited.png",
            "--prompt-output",
            "prompt.md",
          ],
          cwd,
          testEnv(baseUrl),
        ),
    );
    assert.deepEqual(body.urls, [
      "https://example.com/one.jpg",
      "https://example.com/two.jpg",
    ]);
    assert.equal(body.model, "gpt-image-2-vip");
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

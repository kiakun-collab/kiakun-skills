// Thin adapter to the installed Presentations finalizer. No alternative renderer.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {PresentationFile, FileBlob} from '@oai/artifact-tool';

export async function finalizeAndRender({workspaceDir, candidatePath, finalPath,
  renderDir, presentationSkillDir, pythonExecutable, expectedSlideSizeEmu,
  requirements = {}, fontPolicy, pages}) {
  for (const value of [workspaceDir, candidatePath, finalPath, renderDir,
    presentationSkillDir, pythonExecutable]) {
    if (typeof value !== 'string' || !path.isAbsolute(value))
      throw new Error('Runtime adapter requires absolute paths');
  }
  if (!process.env.RUNTIME_NODE_MODULES)
    throw new Error('RUNTIME_NODE_MODULES is required; use rebuild_workflow.py run');
  if (!expectedSlideSizeEmu) throw new Error('expectedSlideSizeEmu is required');
  const existingRenderFiles = await fs.readdir(renderDir).catch(error => {
    if (error.code === 'ENOENT') return [];
    throw error;
  });
  if (existingRenderFiles.length) throw new Error('Use a new empty renderDir for each revision; existing evidence is preserved');
  const tableOwners = requirements.requiredNativeTableOwnerSlides ?? [];
  const {finalizePresentation} = await import(pathToFileURL(path.join(
    presentationSkillDir, 'container_tools/artifact_tool_utils.mjs')).href);
  const receiptDir = path.join(workspaceDir, 'work', 'finalizer');
  await fs.mkdir(receiptDir, {recursive: true});
  await fs.mkdir(path.dirname(finalPath), {recursive: true});
  await fs.mkdir(renderDir, {recursive: true});
  const started = Date.now();
  await finalizePresentation({
    ...requirements, workspaceDir, candidatePath, finalPath,
    pythonExecutable,
    integrityValidatorPath: path.join(presentationSkillDir, 'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath: path.join(presentationSkillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs: ['--expected-slide-size-emu', expectedSlideSizeEmu,
      '--validate-bullet-geometry', '--validate-heading-fit',
      ...tableOwners.flatMap(n => ['--require-native-table-slide', String(n)])],
    requiredNativeTableOwnerSlides: tableOwners, fontPolicy,
    verifyArtifactToolImport: true,
    receiptPath: path.join(receiptDir, `${path.basename(finalPath)}.validation.json`),
  });
  const finalized = Date.now();
  const pptxHash = crypto.createHash('sha256').update(await fs.readFile(finalPath)).digest('hex');
  const deck = await PresentationFile.importPptx(await FileBlob.load(finalPath));
  const selected = pages ?? deck.slides.items.map((_, i) => i + 1);
  if (new Set(selected).size !== selected.length || selected.some(n => !Number.isInteger(n) || n < 1 || n > deck.slides.items.length))
    throw new Error('Invalid or duplicate render page');
  const renders = [];
  for (const number of selected) {
    const renderPath = path.join(renderDir, `slide-${number}.png`);
    const blob = await deck.export({slide: deck.slides.items[number - 1], format: 'png', scale: 1});
    const bytes = new Uint8Array(await blob.arrayBuffer());
    await fs.writeFile(renderPath, bytes);
    renders.push({page: number, renderPath,
      renderSha256: crypto.createHash('sha256').update(bytes).digest('hex')});
  }
  const result = {generatedBy: 'rebuild-runtime.mjs', outputPptx: finalPath,
    outputPptxSha256: pptxHash, slideCount: deck.slides.items.length,
    acceptanceRenderer: 'artifact-tool import final PPTX -> PNG', pages: renders,
    finalizeMs: finalized - started, renderMs: Date.now() - finalized,
    startedAt: new Date(started).toISOString(), renderStartedAt: new Date(finalized).toISOString(),
    completedAt: new Date().toISOString()};
  await fs.writeFile(path.join(renderDir, 'render-receipt.json'), JSON.stringify(result, null, 2));
  return result;
}

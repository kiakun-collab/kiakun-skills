// Shared Presentations adapter. Copy all three runtime .mjs files into the task build directory.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
import {resolveLayout} from './layout-data.mjs';
import {finalizeAndRender} from './rebuild-runtime.mjs';

const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const readJson = async p => JSON.parse((await fs.readFile(p, 'utf8')).replace(/^\uFEFF/, ''));
const position = o => ({left: o.x, top: o.y, width: o.w, height: o.h, ...(o.rotation !== undefined ? {rotation: o.rotation} : {})});
const line = o => ({fill: o.style?.stroke ?? 'none', width: o.style?.strokeWidthPx ?? 0, style: o.dash ?? 'solid'});

function textStyle(s = {}, font) {
  return {typeface: s.fontFamily ?? font, fontSize: (s.fontSizePt ?? 18) / 0.75,
    color: s.color ?? '#111111', bold: s.bold ?? (s.fontWeight >= 600), italic: s.italic ?? false,
    alignment: s.align ?? 'left', verticalAlignment: s.verticalAlign ?? 'top',
    autoFit: 'none', wrap: 'square', insets: s.insets ?? {left: 0, right: 0, top: 0, bottom: 0},
    ...(s.lineSpacingPercent !== undefined ? {lineSpacing: s.lineSpacingPercent / 100} : {})};
}

export async function createFromLayout(resolved, {helpers, assetRoot, handlers = {}}) {
  const presentation = Presentation.create({slideSize: resolved.coordinateSystem});
  const objectMap = [], fonts = new Set(), nativeTables = [], nativeCharts = [];
  const assetCache = new Map();
  for (const page of resolved.pages) {
    const slide = presentation.slides.add();
    slide.background.fill = page.background;
    const font = helpers.resolvePresentationFont({fontFamily: page.fontFamily});
    fonts.add(font);
    for (const o of page.objects) {
      let element, asset;
      for (const style of [o.style, o.headerStyle, ...(o.textRuns ?? []).map(r => r.style)]) if (style?.fontFamily) fonts.add(style.fontFamily);
      if (handlers[o.type]) {
        element = await handlers[o.type]({presentation, slide, object: o, page, helpers, assetRoot});
      } else if (o.type === 'text') {
        element = slide.shapes.add({name: o.name, geometry: 'textbox', position: position(o), fill: 'none', line: {fill: 'none', width: 0}});
        element.text.style = {...textStyle(o.style, font), ...(o.lineSpacing !== undefined ? {lineSpacing: o.lineSpacing} : {})};
        if (o.textRuns?.length) {
          element.text = [[...o.textRuns.map(r => ({run: r.text, textStyle: {
            ...(r.style?.fontSizePt !== undefined ? {fontSize: `${r.style.fontSizePt}pt`} : {}),
            ...(r.style?.fontFamily ? {typeface: r.style.fontFamily} : {}),
            ...(r.style?.color ? {color: r.style.color} : {}),
            ...(r.style?.bold !== undefined || r.style?.fontWeight !== undefined ? {bold: r.style.bold ?? r.style.fontWeight >= 600} : {}),
            ...(r.style?.italic !== undefined ? {italic: r.style.italic} : {})
          }}))]];
        } else element.text = o.text;
      } else if (o.type === 'shape') {
        element = slide.shapes.add({name: o.name, geometry: o.shape, position: position(o),
          fill: o.style?.fill === 'transparent' ? 'none' : o.style?.fill ?? 'none', line: line(o),
          ...(o.borderRadius !== undefined ? {borderRadius: o.borderRadius} : {})});
      } else if (o.type === 'path') {
        element = slide.shapes.add({name: o.name, geometry: 'custom', position: position(o), fill: 'none', line: line(o),
          customPaths: [{width: o.w, height: o.h, commands: o.points.map(([x, y], i) => ({[i ? 'lineTo' : 'moveTo']: {x, y}}))}]});
      } else if (o.type === 'image') {
        const source = path.resolve(assetRoot, o.source);
        if (!assetCache.has(source)) {
          const bytes = await fs.readFile(source);
          const mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}[path.extname(source).toLowerCase()];
          if (!mime && !o.contentType) throw new Error(`${o.name}: explicit contentType required for this image format`);
          assetCache.set(source, {bytes, source, sha256: sha(bytes), contentType: o.contentType ?? mime});
        }
        asset = assetCache.get(source);
        element = slide.images.add({blob: new Uint8Array(asset.bytes), contentType: asset.contentType, alt: o.name,
          position: position(o), fit: o.fit ?? 'contain', ...(o.crop ? {crop: o.crop} : {}),
          ...(o.geometry ? {geometry: o.geometry} : {}), ...(o.borderRadius !== undefined ? {borderRadius: o.borderRadius} : {})});
        if (o.rotation !== undefined) element.rotation = o.rotation;
      } else if (o.type === 'table') {
        const rows = o.values.length, columns = o.values[0].length;
        element = slide.tables.add({rows, columns, left: o.x, top: o.y, width: o.w, height: o.h, columnWidths: o.columnWidths, values: o.values});
        element.styleOptions = {headerRow: false, bandedRows: false, firstColumn: false, lastColumn: false};
        for (let r = 0; r < rows; r++) {
          if (o.rowHeights) element.rows[r].height = o.rowHeights[r];
          for (let c = 0; c < columns; c++) {
            const style = r === 0 ? {...o.style, ...o.headerStyle} : o.style;
            // Apply all four edges per cell, including interior gridlines.
            element.cells.block({row: r, column: c, rowCount: 1, columnCount: 1}).assign({
              fill: style?.fill ?? '#FFFFFF', borders: Object.fromEntries(['top', 'bottom', 'left', 'right'].map(side => [side, line(o)])),
              margins: {top: 2, right: 4, bottom: 2, left: 4}, anchor: 'center'});
            element.getCell(r, c).text.style = {...textStyle(style, font), alignment: style?.align ?? 'center', verticalAlignment: 'middle'};
          }
        }
        if (!nativeTables.includes(page.page)) nativeTables.push(page.page);
      } else if (o.type === 'chart') {
        element = slide.charts.add(o.chartType, {position: position(o), categories: o.categories, series: o.series,
          titlePlacement: 'none', hasLegend: o.hasLegend ?? false, barOptions: o.barOptions,
          xAxis: o.xAxis, yAxis: o.yAxis, dataLabels: o.dataLabels,
          chartFill: 'none', chartLine: {fill: 'none', width: 0}, plotAreaFill: 'none', plotAreaLine: {fill: 'none', width: 0}});
        helpers.applyPresentationChartFont(element, {fontFamily: font});
        if (!nativeCharts.includes(page.page)) nativeCharts.push(page.page);
      } else throw new Error(`Unsupported type ${o.type}; provide an explicit native adapter extension`);
      if (!element) throw new Error(`${o.name}: adapter returned no object`);
      objectMap.push({page: page.page, name: o.name, type: o.type, runtimeId: element.id,
        frame: position(o), sourceExtractionId: o.sourceExtractionId, template: page.template,
        ...(asset ? {source: asset.source, assetSha256: asset.sha256, fit: o.fit ?? 'contain', geometry: o.geometry ?? 'rect', crop: o.crop} : {})});
    }
    const notes = Array.isArray(page.notes) ? page.notes.join('\n') : page.notes ?? '';
    if (notes) slide.speakerNotes.textFrame.setText(notes);
  }
  return {presentation, objectMap, fonts: [...fonts], nativeTables, nativeCharts};
}

export async function buildLayoutFile(layoutPath, config) {
  for (const key of ['workspaceDir', 'buildDir', 'finalPath', 'presentationSkillDir', 'pythonExecutable'])
    if (!path.isAbsolute(config[key] ?? '')) throw new Error(`${key} must be an absolute path`);
  const started = performance.now();
  const resolved = resolveLayout(await readJson(layoutPath));
  const assetRoot = path.dirname(path.resolve(layoutPath));
  const existing = await fs.readdir(config.buildDir).catch(e => {if (e.code === 'ENOENT') return []; throw e;});
  if (existing.length) throw new Error('Use a new empty buildDir for each revision');
  const helpers = await import(pathToFileURL(path.join(config.presentationSkillDir, 'container_tools/artifact_tool_utils.mjs')).href);
  await fs.mkdir(config.buildDir, {recursive: true});
  const pageDir = path.join(config.buildDir, 'layout-pages');
  await fs.mkdir(pageDir);
  for (const page of resolved.pages) {
    // Derived files remain usable for QA outside the input directory.
    for (const key of ['sourceExtractionFile', 'coordinateCalibrationFile', 'typographyCalibrationFile'])
      if (page[key]) page[key] = path.resolve(assetRoot, page[key]);
    for (const o of page.objects) if (o.type === 'image') o.source = path.resolve(assetRoot, o.source);
    await fs.writeFile(path.join(pageDir, `page-${page.page}.json`), JSON.stringify(page, null, 2));
  }
  await fs.writeFile(path.join(config.buildDir, 'resolved-layout.json'), JSON.stringify(resolved, null, 2));
  const resolvedAt = performance.now();
  const built = await createFromLayout(resolved, {helpers, assetRoot});
  const constructedAt = performance.now();
  const candidatePath = path.join(config.buildDir, 'candidate.pptx');
  await (await PresentationFile.exportPptx(built.presentation)).save(candidatePath);
  const exportedAt = performance.now();
  const requirements = {...config.requirements};
  if (requirements.explicitTotalSlideCount !== undefined && requirements.explicitTotalSlideCount !== resolved.pages.length)
    throw new Error('Declared slide count differs from layout pages');
  requirements.explicitTotalSlideCount = resolved.pages.length;
  requirements.requiredNativeTableOwnerSlides = [...new Set([...(requirements.requiredNativeTableOwnerSlides ?? []), ...built.nativeTables])];
  requirements.requiredNativeChartOwnerSlides = [...new Set([...(requirements.requiredNativeChartOwnerSlides ?? []), ...built.nativeCharts])];
  const renderDir = path.join(config.buildDir, 'render');
  const receipt = await finalizeAndRender({...config, candidatePath, renderDir, requirements,
    expectedSlideSizeEmu: `${Math.round(resolved.coordinateSystem.width * 9525)},${Math.round(resolved.coordinateSystem.height * 9525)}`,
    fontPolicy: config.fontPolicy ?? {basis: 'design', families: built.fonts}});
  await fs.writeFile(path.join(config.buildDir, 'object-map.json'), JSON.stringify({
    note: 'runtimeId identifies authoring objects; image alt/name export depends on the installed runtime. Use source hash + page + frame for independent package verification.',
    objects: built.objectMap}, null, 2));
  const metrics = {layoutSha256: sha(await fs.readFile(layoutPath)),
    builderSha256: sha(await fs.readFile(fileURLToPath(import.meta.url))),
    resolverSha256: sha(await fs.readFile(new URL('./layout-data.mjs', import.meta.url))),
    slideCount: resolved.pages.length, objectCount: built.objectMap.length,
    resolveMs: Math.round(resolvedAt - started), constructMs: Math.round(constructedAt - resolvedAt),
    exportMs: Math.round(exportedAt - constructedAt), finalizeMs: receipt.finalizeMs, renderMs: receipt.renderMs,
    totalMs: Math.round(performance.now() - started), finalPath: config.finalPath, renderDir,
    visualStatus: 'NOT_REVIEWED', timingScope: 'execution only; excludes model analysis, asset preparation and visual review'};
  await fs.writeFile(path.join(config.buildDir, 'metrics.json'), JSON.stringify(metrics, null, 2));
  return metrics;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [layoutPath, configPath] = process.argv.slice(2);
    if (!layoutPath || !configPath) throw new Error('Usage: node build-from-layout.mjs layout-spec.json build-config.json');
    console.log(JSON.stringify(await buildLayoutFile(path.resolve(layoutPath), await readJson(configPath))));
  } catch (error) {console.error(error.stack ?? String(error)); process.exitCode = 1;}
}

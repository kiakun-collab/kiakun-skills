// Pure data resolution: no renderer, filesystem access, OCR, or inferred measurements.
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const plain = o => o !== null && typeof o === 'object' && !Array.isArray(o);
const clone = o => structuredClone(o);
const TYPES = ['text', 'shape', 'path', 'image', 'table', 'chart'];

function merge(base, patch) {
  const out = plain(base) ? clone(base) : {};
  for (const [key, value] of Object.entries(patch ?? {})) {
    if (['__proto__', 'constructor', 'prototype'].includes(key)) throw new Error(`Invalid key: ${key}`);
    out[key] = plain(value) ? merge(out[key], value) : clone(value);
  }
  return out;
}

function uniqueObjects(objects, context) {
  if (!Array.isArray(objects)) throw new Error(`${context}: objects must be an array`);
  const map = new Map();
  for (const o of objects) {
    if (!plain(o) || typeof o.name !== 'string' || !o.name || map.has(o.name))
      throw new Error(`${context}: duplicate/missing object name ${o?.name}`);
    map.set(o.name, clone(o));
  }
  return map;
}

function bindData(o, datasets) {
  function rows(key) {
    const value = datasets[key];
    if (!Array.isArray(value) || !value.length || value.some(r => !plain(r)))
      throw new Error(`${o.name}: missing/empty dataset ${key}`);
    return value;
  }
  function field(row, key, numeric = false) {
    if (!own(row, key) || row[key] === null || (numeric && !Number.isFinite(row[key])))
      throw new Error(`${o.name}: invalid dataset field ${key}`);
    return row[key];
  }
  if (o.dataRef) {
    const data = rows(o.dataRef);
    if (o.type === 'table') {
      if (!o.columns?.length) throw new Error(`${o.name}: table columns required`);
      o.values = [o.columns.map(c => c.label), ...data.map(r => o.columns.map(c => String(field(r, c.field))))];
    } else if (o.type === 'chart') {
      o.categories = data.map(r => String(field(r, o.categoryField)));
      if (!o.series?.length) throw new Error(`${o.name}: chart series required`);
      o.series = o.series.map(s => ({...s, values: data.map(r => field(r, s.valueField, true))}));
    } else throw new Error(`${o.name}: dataRef supports table/chart only`);
  }
  if (o.textFrom) {
    if (o.type !== 'text' || o.textFrom.aggregate !== 'sum') throw new Error(`${o.name}: only sum textFrom is supported`);
    o.text = String(rows(o.textFrom.dataset).reduce((sum, r) => sum + field(r, o.textFrom.field, true), 0));
    if (o.textRuns?.length) throw new Error(`${o.name}: textFrom cannot retain literal textRuns`);
  }
}

function validateObject(o, allowedTypes) {
  if (!allowedTypes.includes(o.type)) throw new Error(`${o.name}: unsupported object type ${o.type}; use an explicit adapter extension`);
  for (const k of ['x', 'y', 'w', 'h']) if (!Number.isFinite(o[k])) throw new Error(`${o.name}: invalid ${k}`);
  if (o.w < 0 || o.h < 0) throw new Error(`${o.name}: negative frame`);
  for (const k of ['z', 'rotation']) if (o[k] !== undefined && !Number.isFinite(o[k])) throw new Error(`${o.name}: invalid ${k}`);
  for (const style of [o.style, o.headerStyle, ...(o.textRuns ?? []).map(r => r.style)]) {
    if (style?.fontSizePt !== undefined && (!Number.isFinite(style.fontSizePt) || style.fontSizePt <= 0))
      throw new Error(`${o.name}: fontSizePt must be positive`);
  }
  if (o.type === 'text') {
    if (typeof o.text !== 'string') throw new Error(`${o.name}: text must be a string`);
    if (o.textRuns?.length && o.textRuns.map(r => r.text).join('') !== o.text) throw new Error(`${o.name}: textRuns differ from text`);
  }
  if (o.type === 'shape' && !o.shape) throw new Error(`${o.name}: shape geometry required`);
  if (o.type === 'path' && (!Array.isArray(o.points) || o.points.length < 2 || o.points.some(p => !Array.isArray(p) || p.length !== 2 || p.some(n => !Number.isFinite(n)))))
    throw new Error(`${o.name}: path points must be local pixel pairs`);
  if (o.type === 'image') {
    if (typeof o.source !== 'string' || !o.source) throw new Error(`${o.name}: image source required`);
    if (o.fit !== undefined && !['cover', 'contain'].includes(o.fit)) throw new Error(`${o.name}: invalid image fit`);
    if (o.crop) {
      const c = o.crop;
      if (['left', 'top', 'right', 'bottom'].some(k => !Number.isFinite(c[k]) || c[k] < 0 || c[k] >= 1) || c.left + c.right >= 1 || c.top + c.bottom >= 1)
        throw new Error(`${o.name}: crop must leave a nonempty source area`);
    }
  }
  if (o.type === 'table' && (!Array.isArray(o.values) || !o.values.length || !o.values[0]?.length || o.values.some(r => !Array.isArray(r) || r.length !== o.values[0].length)))
    throw new Error(`${o.name}: table must be a nonempty rectangular matrix`);
  if (o.type === 'chart' && (!o.chartType || !o.categories?.length || !o.series?.length || o.series.some(s => !Array.isArray(s.values) || s.values.length !== o.categories.length || s.values.some(v => !Number.isFinite(v)))))
    throw new Error(`${o.name}: chart categories and numeric series must align`);
}

export function resolveLayout(input, {allowedTypes = TYPES} = {}) {
  if (!plain(input)) throw new Error('Layout must be an object');
  if (input.schemaVersion && !['2.0', '3.0', 'prototype-1'].includes(input.schemaVersion)) throw new Error('Unsupported layout schemaVersion');
  const canvas = clone(input.coordinateSystem ?? {width: 1280, height: 720});
  if (![canvas.width, canvas.height].every(n => Number.isFinite(n) && n > 0)) throw new Error('Invalid coordinateSystem');
  const policy = clone(input.templatePolicy ?? {mode: 'faithful'});
  if (!['faithful', 'normalize'].includes(policy.mode)) throw new Error('Invalid templatePolicy.mode');
  if (policy.mode === 'normalize' && !policy.basis?.trim()) throw new Error('Template normalization requires the user-intent basis');
  const pages = input.pages ?? [input];
  if (!Array.isArray(pages) || !pages.length) throw new Error('At least one page is required');
  const resolved = pages.map((page, index) => {
    if (!plain(page)) throw new Error('Page must be an object');
    if (input.pages && page.page !== undefined && Number(page.page) !== index + 1) throw new Error('Page numbers must match their 1-based deck order');
    if (page.coordinateSystem && (page.coordinateSystem.width !== canvas.width || page.coordinateSystem.height !== canvas.height))
      throw new Error('A PPTX has one canvas size; split mixed-aspect decks instead of stretching pages');
    const template = page.template ? input.templates?.[page.template] : {};
    if (!plain(template)) throw new Error(`Unknown template: ${page.template}`);
    const objects = uniqueObjects(template.objects ?? [], `template ${page.template ?? '(none)'}`);
    const omitted = new Set();
    for (const name of page.omitObjects ?? []) {
      if (!objects.has(name) || omitted.has(name)) throw new Error(`Unknown/duplicate omitted template object: ${name}`);
      omitted.add(name);
      objects.delete(name);
    }
    for (const [name, patch] of uniqueObjects(page.objects ?? [], `page ${index + 1}`)) {
      if (omitted.has(name)) throw new Error(`Object is both omitted and overridden: ${name}`);
      const obj = merge(objects.get(name), patch);
      // New content cannot accidentally retain runs from the previous page's title.
      if (own(patch, 'text') && !own(patch, 'textRuns')) delete obj.textRuns;
      if (own(patch, 'text') && !own(patch, 'textFrom')) delete obj.textFrom;
      objects.set(name, obj);
    }
    const styles = merge(input.styles, page.styles);
    const datasets = merge(input.datasets, page.datasets);
    const out = merge(template, page);
    delete out.styles;
    delete out.templates;
    delete out.pages;
    delete out.omitObjects;
    out.schemaVersion = '3.0';
    out.page = index + 1;
    out.coordinateSystem = clone(canvas);
    out.background = page.background ?? template.background ?? input.background ?? '#FFFFFF';
    out.fontFamily = page.fontFamily ?? template.fontFamily ?? input.fontFamily;
    out.templatePolicy = clone(policy);
    out.objects = [...objects.values()].map(o => {
      if (o.styleRef && !own(styles, o.styleRef)) throw new Error(`${o.name}: unknown styleRef ${o.styleRef}`);
      o.style = merge(styles[o.styleRef], o.style);
      bindData(o, datasets);
      validateObject(o, allowedTypes);
      return o;
    }).sort((a, b) => (a.z ?? 0) - (b.z ?? 0));
    return out;
  });
  return {schemaVersion: '3.0', coordinateSystem: canvas, templatePolicy: policy, pages: resolved};
}

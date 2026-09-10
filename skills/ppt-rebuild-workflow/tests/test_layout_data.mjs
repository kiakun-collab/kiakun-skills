import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {resolveLayout} from '../assets/runtime/layout-data.mjs';

const readExample = () => JSON.parse(fs.readFileSync(new URL('../assets/templates/layout-spec-shared-template-example.json', import.meta.url), 'utf8'));
const text = (name, value = '正文') => ({name, type: 'text', text: value, x: 40, y: 200, w: 600, h: 100});

test('one template controls all pages; changing one page leaves peers and input untouched', () => {
  const input = readExample(), snapshot = structuredClone(input);
  const before = resolveLayout(input);
  input.pages[0].objects[0].text = '只改第一页';
  const after = resolveLayout(input);
  assert.equal(after.pages[0].objects.find(o => o.name === 'title-main').text, '只改第一页');
  assert.deepEqual(after.pages[1], before.pages[1]);
  assert.deepEqual(input.templates, snapshot.templates);
  input.templates['blue-white'].objects[0].h = 192;
  const changedTemplate = resolveLayout(input);
  for (const p of changedTemplate.pages) assert.equal(p.objects.find(o => o.name === 'background-header').h, 192);
  assert.equal(before.pages[0].objects[0].h, 180);
});

test('local style overrides preserve shared values and title updates cannot retain stale runs', () => {
  const input = readExample();
  const title = input.templates['blue-white'].objects[1];
  title.text = '旧标题'; title.textRuns = [{text: '旧标题', style: {color: '#00FF00'}}];
  input.pages[0].objects[0].style = {fontSizePt: 30};
  const out = resolveLayout(input).pages[0].objects.find(o => o.name === 'title-main');
  assert.equal(out.style.fontSizePt, 30);
  assert.equal(out.style.color, '#FFFFFF');
  assert.equal(out.style.bold, true);
  assert.equal(out.textRuns, undefined);
});

test('explicit omission and per-page objects do not remove or add objects on peer pages', () => {
  const input = readExample();
  input.pages[0].objects = [input.pages[0].objects[0], text('body-text-extra')];
  input.pages[0].omitObjects = ['body-text-main'];
  const pages = resolveLayout(input).pages;
  assert.equal(pages[0].objects.some(o => o.name === 'body-text-main'), false);
  assert.equal(pages[1].objects.some(o => o.name === 'body-text-main'), true);
  assert.equal(pages[1].objects.some(o => o.name === 'body-text-extra'), false);
});

test('one dataset updates table, native chart data and sum text without mutating peers', () => {
  const input = {datasets: {cities: [{city: '青岛', participants: 120}, {city: '厦门', participants: 180}]}, templates: {data: {objects: [
    {...text('body-text-total'), textFrom: {dataset: 'cities', aggregate: 'sum', field: 'participants'}},
    {name: 'table-cities', type: 'table', x: 40, y: 320, w: 500, h: 200, dataRef: 'cities', columns: [{field: 'city', label: '城市'}, {field: 'participants', label: '人数'}]},
    {name: 'chart-cities', type: 'chart', x: 600, y: 320, w: 500, h: 200, chartType: 'bar', dataRef: 'cities', categoryField: 'city', series: [{name: '人数', valueField: 'participants'}]}
  ]}}, pages: [{template: 'data'}, {template: 'data', datasets: {cities: [{city: '青岛', participants: 126}, {city: '厦门', participants: 180}]}}]};
  const snapshot = structuredClone(input), out = resolveLayout(input);
  assert.deepEqual(input, snapshot);
  assert.equal(out.pages[0].objects[0].text, '300');
  assert.equal(out.pages[1].objects[0].text, '306');
  assert.equal(out.pages[1].objects[1].values[1][1], '126');
  assert.deepEqual(out.pages[1].objects[2].series[0].values, [126, 180]);
  input.datasets.cities[0].participants = 130;
  assert.equal(resolveLayout(input).pages[0].objects[0].text, '310');
  assert.equal(resolveLayout(input).pages[1].objects[0].text, '306');
  input.datasets.cities[0].participants = 'unknown';
  assert.throws(() => resolveLayout(input), /invalid dataset field/);
});

test('faithful is default; normalization requires stated user intent without altering source observations', () => {
  const input = {objects: [{...text('title-main'), sourceExtractionId: 'observed-title', measurementEvidence: 'reference bbox'}]};
  assert.equal(resolveLayout(input).templatePolicy.mode, 'faithful');
  input.templatePolicy = {mode: 'normalize'};
  assert.throws(() => resolveLayout(input), /user-intent basis/);
  input.templatePolicy.basis = '用户要求统一模板';
  const obj = resolveLayout(input).pages[0].objects[0];
  assert.equal(obj.sourceExtractionId, 'observed-title');
  assert.equal(obj.measurementEvidence, 'reference bbox');
});

test('explicit page copy overrides inherited calculations while an explicit binding can be retained', () => {
  const input = {datasets: {cities: [{n: 120}]}, templates: {totals: {objects: [
    {...text('body-text-total'), textFrom: {dataset: 'cities', aggregate: 'sum', field: 'n'}}
  ]}}, pages: [{template: 'totals', objects: [{name: 'body-text-total', text: '以用户定稿为准'}]},
    {template: 'totals', objects: [{name: 'body-text-total', text: '', textFrom: {dataset: 'cities', aggregate: 'sum', field: 'n'}}]}]};
  const out = resolveLayout(input);
  assert.equal(out.pages[0].objects[0].text, '以用户定稿为准');
  assert.equal(out.pages[1].objects[0].text, '120');
});

test('single-page 2.0 data and 4:3 dimensions remain supported', () => {
  const out = resolveLayout({schemaVersion: '2.0', page: '03', coordinateSystem: {width: 1280, height: 960}, objects: [text('title-main')]});
  assert.deepEqual(out.coordinateSystem, {width: 1280, height: 960});
  assert.equal(out.pages.length, 1);
  assert.equal(out.pages[0].objects[0].text, '正文');
});

test('duplicate IDs, unknown template/style and unsupported types are actionable input errors', () => {
  assert.throws(() => resolveLayout({objects: [text('same'), text('same')]}), /duplicate/);
  assert.throws(() => resolveLayout({pages: [{template: 'missing'}]}), /Unknown template/);
  assert.throws(() => resolveLayout({objects: [{...text('a'), styleRef: 'missing'}]}), /unknown styleRef/);
  assert.throws(() => resolveLayout({objects: [{...text('a'), type: 'video'}]}), /unsupported object type/);
  assert.throws(() => resolveLayout({pages: [{page: 2, objects: []}]}), /deck order/);
});

test('ellipse masks and explicit source cropping survive resolution, invalid crops fail', () => {
  const o = {name: 'content-image-icon', type: 'image', source: 'icon.png', x: 900, y: 240, w: 100, h: 100, fit: 'cover', geometry: 'ellipse', crop: {left: 0.1, top: 0, right: 0.1, bottom: 0}};
  assert.deepEqual(resolveLayout({objects: [o]}).pages[0].objects[0], {...o, style: {}});
  o.crop.left = 0.95;
  assert.throws(() => resolveLayout({objects: [o]}), /crop/);
});

test('invalid geometry, mixed aspect and conflicting omissions cannot silently distort output', () => {
  assert.throws(() => resolveLayout({objects: [{...text('a'), w: -1}]}), /negative frame/);
  assert.throws(() => resolveLayout({objects: [{...text('a'), x: '80%'}]}), /invalid x/);
  assert.throws(() => resolveLayout({pages: [{coordinateSystem: {width: 1280, height: 960}}]}), /one canvas/);
  const input = readExample(); input.pages[0].omitObjects = ['title-main'];
  assert.throws(() => resolveLayout(input), /both omitted and overridden/);
});

test('custom native adapter types require an explicit opt-in; rich text must match content', () => {
  const input = {objects: [{...text('connector-a'), type: 'connector'}]};
  assert.equal(resolveLayout(input, {allowedTypes: ['connector']}).pages[0].objects[0].type, 'connector');
  assert.throws(() => resolveLayout({objects: [{...text('a', 'new'), textRuns: [{text: 'old'}]}]}), /textRuns differ/);
});

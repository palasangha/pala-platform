const test = require('node:test');
const assert = require('node:assert/strict');
const { buildSnippet, splitContextLines, cleanContextLine } = require('../lib/snippetUtils.js');

test('cleanContextLine removes trailing timestamp and file metadata', () => {
  assert.equal(
    cleanContextLine('And now you will work very carefully 2026-05-13T10:29:01.098112+00:00 DAY_5_91.docx ocr'),
    'And now you will work very carefully'
  );
});

test('buildSnippet returns one contiguous six-line window from a single source', () => {
  const shortAnchor = 'But even to expect some name or some fame or some position, some power, some status—oh no, then one has not understood Dhamma.';
  const fullSource = [
    'Intro line one that should not be selected.',
    'Intro line two that should not be selected.',
    'Line three before the hit.',
    'But even to expect some name or some fame or some position, some power, some status—oh no, then one has not understood Dhamma.',
    'Line five after the hit.',
    'Line six after the hit.',
    'Line seven after the hit.',
    'Line eight after the hit.',
  ].join('\n');

  const snippet = buildSnippet([shortAnchor, fullSource], 'What are the two qualities necessary for understanding Dhamma?', shortAnchor, 6);
  const lines = splitContextLines(snippet);

  assert.equal(lines.length, 6);
  assert.ok(lines.includes('But even to expect some name or some fame or some position, some power, some status—oh no, then one has not understood Dhamma.'));
  assert.ok(lines.every((line) => line.startsWith('Intro line') || line.includes('Dhamma.') || line.includes('Line')));
  assert.deepEqual(lines, [
    'Intro line two that should not be selected.',
    'Line three before the hit.',
    'But even to expect some name or some fame or some position, some power, some status—oh no, then one has not understood Dhamma.',
    'Line five after the hit.',
    'Line six after the hit.',
    'Line seven after the hit.',
  ]);
});

test('buildSnippet does not stitch lines from multiple candidates', () => {
  const sourceA = [
    'Source A line 1.',
    'Source A line 2.',
    'Source A line 3.',
    'Source A line 4.',
    'Source A line 5.',
    'Source A line 6.',
  ].join('\n');

  const sourceB = [
    'Source B line 1.',
    'Source B line 2.',
    'Source B line 3.',
    'Source B line 4.',
    'Source B line 5.',
    'Source B line 6.',
  ].join('\n');

  const snippet = buildSnippet([sourceA, sourceB], 'Source B', 'Source B line 3.', 6);
  const lines = splitContextLines(snippet);

  assert.equal(lines.length, 6);
  assert.ok(lines.every((line) => line.startsWith('Source B line')));
});

test('buildSnippet returns 6 lines from full content even when anchor is short', () => {
  const shortAnchor = 'But this was the contribution of Buddha, the discovery of Buddha: that you cannot come out of your misery.';
  const fullContent = [
    'Some introduction text that is not relevant.',
    'More intro lines here.',
    'Buddha spoke about suffering and its cessation.',
    'But this was the contribution of Buddha, the discovery of Buddha: that you cannot come out of your misery.',
    'Unless you understand the nature of misery deeply.',
    'The path to liberation requires wisdom and compassion.',
    'All sentient beings seek to escape suffering.',
    'The Buddha taught the four noble truths.',
  ].join('\n');
  const summary = 'A brief summary of the document';

  const snippet = buildSnippet([shortAnchor, fullContent, summary], 'Buddha teachings causes of misery', shortAnchor, 6);
  const lines = splitContextLines(snippet);

  assert.equal(lines.length, 6, `Expected 6 lines but got ${lines.length}: ${lines.join(' | ')}`);
  assert.ok(lines.some((line) => line.includes('contribution of Buddha')), 'Should include the anchor');
  assert.ok(lines.length >= 6, 'Should return minimum 6 lines, not just the short anchor');
});

test('buildSnippet with short anchor and empty full content returns best available', () => {
  const shortAnchor = 'But this was the contribution of Buddha, the discovery of Buddha: that you cannot come out of your misery.';
  const fullContent = ''; // Empty!
  const summary = 'A summary about Buddha teachings and the path to enlightenment. Many lines could follow here to provide context.';

  const snippet = buildSnippet([shortAnchor, fullContent, summary], 'Buddha teachings', shortAnchor, 6);
  const lines = splitContextLines(snippet);

  // When fullContent is empty, we might not get 6 lines, but we should get something reasonable
  assert.ok(lines.length > 0, 'Should return at least one line');
  assert.ok(snippet.length > 0, 'Snippet should not be empty');
});


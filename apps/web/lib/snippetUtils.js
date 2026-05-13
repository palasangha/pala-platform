const SEARCH_STOPWORDS = new Set([
  'a',
  'an',
  'and',
  'any',
  'are',
  'as',
  'at',
  'be',
  'but',
  'by',
  'for',
  'from',
  'has',
  'have',
  'how',
  'in',
  'is',
  'it',
  'of',
  'on',
  'or',
  'reference',
  'show',
  'that',
  'the',
  'there',
  'this',
  'to',
  'was',
  'were',
  'what',
  'when',
  'where',
  'who',
  'with',
]);

function toText(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value.trim();
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return '';
}

function normalizeQuestionText(text) {
  return toText(text).toLowerCase().replace(/\s+/g, ' ').trim();
}

function extractMeaningfulTerms(text) {
  return Array.from(
    new Set(
      toText(text)
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .map((term) => term.trim())
        .filter((term) => term.length > 2 && !SEARCH_STOPWORDS.has(term))
    )
  );
}

function cleanContextLine(text) {
  const normalized = toText(text).replace(/\s+/g, ' ').trim();
  if (!normalized) return '';

  const noisyPatterns = [
    /^\d{4}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2})?$/i,
    /^\d{4}-\d{2}-\d{2}$/,
    /^[\w.-]+\.(?:docx|pdf|txt|json|md|jpg|jpeg|png|gif|webp)$/i,
  ];

  if (noisyPatterns.some((pattern) => pattern.test(normalized))) {
    return '';
  }

  let cleaned = normalized;

  cleaned = cleaned.replace(/\s+\d{4}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2})?/gi, '');
  cleaned = cleaned.replace(/\s+[\w.-]+\.(?:docx|pdf|txt|json|md|jpg|jpeg|png|gif|webp)\b/gi, '');
  cleaned = cleaned.replace(/\s+(?:ocr|metadata|extracted|generated)\b/gi, '');
  cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();

  if (!cleaned) return '';
  if (cleaned.length < 3) return '';
  return cleaned;
}

function splitContextLines(text) {
  const normalized = toText(text).replace(/\r\n/g, '\n').replace(/\u00a0/g, ' ').trim();
  if (!normalized) return [];

  const newlineParts = normalized
    .split(/\n+/)
    .map((part) => part.trim())
    .filter(Boolean);

  const lines = [];
  for (const part of newlineParts) {
    const sentenceParts = part
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter(Boolean);

    const units = sentenceParts.length > 0 ? sentenceParts : [part];
    for (const unit of units) {
      const cleanedUnit = cleanContextLine(unit);
      if (!cleanedUnit) {
        continue;
      }

      if (cleanedUnit.length <= 160) {
        lines.push(cleanedUnit);
        continue;
      }

      let start = 0;
      while (start < cleanedUnit.length) {
        const chunk = cleanedUnit.slice(start, start + 160).trim();
        if (chunk) lines.push(chunk);
        start += 160;
      }
    }
  }

  return lines;
}

function uniqueNonEmptyText(values) {
  const seen = new Set();
  const out = [];
  for (const value of values || []) {
    const text = toText(value).trim();
    if (!text) continue;
    const key = normalizeQuestionText(text);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(text);
  }
  return out;
}

function pickBestLineIndex(lines, terms) {
  if (lines.length === 0 || terms.length === 0) return -1;

  let bestIndex = -1;
  let bestScore = 0;
  for (let index = 0; index < lines.length; index += 1) {
    const lower = lines[index].toLowerCase();
    const score = terms.reduce((total, term) => (lower.includes(term) ? total + 1 : total), 0);
    if (score > bestScore) {
      bestScore = score;
      bestIndex = index;
    }
  }

  return bestScore > 0 ? bestIndex : -1;
}

function lineWindow(text, query, minimumLines = 6, anchorText = '') {
  const lines = splitContextLines(text);
  if (lines.length === 0) return '';

  const normalizedQuery = normalizeQuestionText(query);
  const normalizedAnchor = normalizeQuestionText(anchorText);
  const terms = extractMeaningfulTerms(query);
  const anchorTerms = extractMeaningfulTerms(anchorText);

  let hitIndex = -1;
  if (normalizedAnchor) {
    hitIndex = lines.findIndex((line) => normalizeQuestionText(line).includes(normalizedAnchor));
  }

  if (hitIndex === -1 && anchorTerms.length > 0) {
    hitIndex = pickBestLineIndex(lines, anchorTerms);
  }

  if (hitIndex === -1 && terms.length > 0) {
    hitIndex = pickBestLineIndex(lines, terms);
  }

  if (hitIndex === -1 && normalizedQuery) {
    hitIndex = lines.findIndex((line) => normalizeQuestionText(line).includes(normalizedQuery));
  }

  let start = 0;
  if (hitIndex !== -1) {
    start = Math.max(0, hitIndex - 2);
  }

  let end = Math.min(lines.length, start + minimumLines);
  if (end - start < minimumLines) {
    start = Math.max(0, end - minimumLines);
  }

  return lines.slice(start, end).join('\n');
}

function countLineMatches(snippet, anchorText, query) {
  const lines = splitContextLines(snippet);
  if (lines.length === 0) return 0;

  const anchorTerms = extractMeaningfulTerms(anchorText);
  const queryTerms = extractMeaningfulTerms(query);
  const anchorExact = normalizeQuestionText(anchorText);
  const queryExact = normalizeQuestionText(query);

  let score = 0;
  for (const line of lines) {
    const lower = line.toLowerCase();
    const normalizedLine = normalizeQuestionText(line);

    if (anchorExact && normalizedLine.includes(anchorExact)) score += 8;
    if (queryExact && normalizedLine.includes(queryExact)) score += 4;
    score += anchorTerms.reduce((total, term) => (lower.includes(term) ? total + 2 : total), 0);
    score += queryTerms.reduce((total, term) => (lower.includes(term) ? total + 1 : total), 0);
  }

  return score;
}

function buildSnippet(candidates, query, anchorText, minimumLines = 6) {
  const uniqueCandidates = uniqueNonEmptyText(candidates);
  if (uniqueCandidates.length === 0) return '';

  const scored = uniqueCandidates
    .map((candidate) => {
      const snippet = lineWindow(candidate, query, minimumLines, anchorText);
      const lineCount = splitContextLines(snippet).length;
      const score = countLineMatches(snippet, anchorText, query);
      return { candidate, snippet, lineCount, score };
    })
    .sort((a, b) => (b.score - a.score) || (b.lineCount - a.lineCount) || (b.candidate.length - a.candidate.length));

  const richCandidates = scored.filter((entry) => entry.lineCount >= minimumLines);
  const best = richCandidates[0] || scored[0];
  return best ? best.snippet : '';
}

module.exports = {
  buildSnippet,
  cleanContextLine,
  countLineMatches,
  extractMeaningfulTerms,
  lineWindow,
  normalizeQuestionText,
  pickBestLineIndex,
  splitContextLines,
  uniqueNonEmptyText,
};

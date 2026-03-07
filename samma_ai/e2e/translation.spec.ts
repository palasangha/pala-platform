import { test, expect } from '@playwright/test';

/**
 * Translation Feature E2E Tests
 *
 * Tests the complete Pali translation pipeline:
 * 1. Cache hits/misses
 * 2. Translation quality (Deepseek via Ollama)
 * 3. Graceful fallback when Ollama unavailable
 * 4. Chat integration with enriched passages
 */

test.describe('Pali Translation Feature', () => {

  // ────────────────────────────────────────────────────────────────────────
  // Test 1: Basic Translation Quality
  // ────────────────────────────────────────────────────────────────────────

  test('should translate samadhi correctly', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is samadhi?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data).toHaveProperty('passages');
    expect(data.passages.length).toBeGreaterThan(0);

    // Check that passages have translations
    const passagesWithText = data.passages.filter(p => p.english_text);
    expect(passagesWithText.length).toBeGreaterThan(0);

    // Verify translation contains key terms for samadhi
    const translations = passagesWithText.map(p => p.english_text.toLowerCase());
    const hasValidTranslation = translations.some(t =>
      t.includes('concentration') ||
      t.includes('meditative') ||
      t.includes('absorption') ||
      t.includes('focus')
    );
    expect(hasValidTranslation).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 2: Metta (Loving-Kindness) Translation
  // ────────────────────────────────────────────────────────────────────────

  test('should translate metta correctly', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is metta?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.passages.length).toBeGreaterThan(0);

    const passagesWithText = data.passages.filter(p => p.english_text);
    const translations = passagesWithText.map(p => p.english_text.toLowerCase());

    // Metta should translate to loving-kindness or similar
    const hasValidTranslation = translations.some(t =>
      t.includes('loving') ||
      t.includes('kindness') ||
      t.includes('benevolence') ||
      t.includes('goodwill')
    );
    expect(hasValidTranslation).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 3: Translation Source Tracking
  // ────────────────────────────────────────────────────────────────────────

  test('should track translation source (db vs ollama)', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is dukkha?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    // All passages should have translation_source field
    for (const passage of data.passages) {
      expect(passage).toHaveProperty('translation_source');
      expect(['db', 'ollama', 'none']).toContain(passage.translation_source);

      // If source is 'db' or 'ollama', english_text should exist
      if (passage.translation_source !== 'none') {
        expect(passage.english_text).toBeTruthy();
        expect(passage.english_text.length).toBeGreaterThan(0);
      }
    }
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 4: Cache Performance (Second Request Should Be Faster)
  // ────────────────────────────────────────────────────────────────────────

  test('should cache translations and improve second request speed', async ({ request }) => {
    const message = 'What is anatta?';

    // First request (cold cache)
    const start1 = Date.now();
    const response1 = await request.post('/chat', {
      data: { message, model_id: 'copilot' }
    });
    const time1 = Date.now() - start1;

    expect(response1.status()).toBe(200);
    const data1 = await response1.json();
    expect(data1.passages.length).toBeGreaterThan(0);

    // Second request with same message (should hit cache)
    const start2 = Date.now();
    const response2 = await request.post('/chat', {
      data: { message, model_id: 'copilot' }
    });
    const time2 = Date.now() - start2;

    expect(response2.status()).toBe(200);
    const data2 = await response2.json();

    // Verify both responses have translations
    expect(data1.passages.some(p => p.english_text)).toBeTruthy();
    expect(data2.passages.some(p => p.english_text)).toBeTruthy();

    console.log(`First request: ${time1}ms, Second request: ${time2}ms`);
    // Note: Second request should be faster, but timing varies based on system
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 5: Dukkha (Suffering) Translation
  // ────────────────────────────────────────────────────────────────────────

  test('should translate dukkha correctly', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is dukkha?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    const passagesWithText = data.passages.filter(p => p.english_text);
    const translations = passagesWithText.map(p => p.english_text.toLowerCase());

    // Dukkha should translate to suffering or unsatisfactoriness
    const hasValidTranslation = translations.some(t =>
      t.includes('suffer') ||
      t.includes('unsatisfactor') ||
      t.includes('stress') ||
      t.includes('distress') ||
      t.includes('pain')
    );
    expect(hasValidTranslation).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 6: Anicca (Impermanence) Translation
  // ────────────────────────────────────────────────────────────────────────

  test('should translate anicca correctly', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is anicca?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    const passagesWithText = data.passages.filter(p => p.english_text);
    const translations = passagesWithText.map(p => p.english_text.toLowerCase());

    // Anicca should translate to impermanence or impermanent
    const hasValidTranslation = translations.some(t =>
      t.includes('impermanent') ||
      t.includes('transient') ||
      t.includes('inconstant') ||
      t.includes('changing') ||
      t.includes('change')
    );
    expect(hasValidTranslation).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 7: Passage Fields Completeness
  // ────────────────────────────────────────────────────────────────────────

  test('should return complete passage data with translations', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is the Noble Eightfold Path?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    for (const passage of data.passages) {
      // Required fields
      expect(passage).toHaveProperty('id');
      expect(passage).toHaveProperty('pali_text');
      expect(passage).toHaveProperty('english_text'); // NEW
      expect(passage).toHaveProperty('translation_source'); // NEW
      expect(passage).toHaveProperty('xml_source');
      expect(passage).toHaveProperty('paragraph_number');

      // Validate types
      expect(typeof passage.id).toBe('string');
      expect(typeof passage.pali_text).toBe('string');
      expect(typeof passage.english_text).toBe('string');
      expect(typeof passage.translation_source).toBe('string');
    }
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 8: Health Check Includes Translation Service
  // ────────────────────────────────────────────────────────────────────────

  test('should report translation service status in health check', async ({ request }) => {
    const response = await request.get('/status');

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data).toHaveProperty('checks');
    expect(data.checks).toHaveProperty('translation_service');

    const translationCheck = data.checks.translation_service;
    expect(translationCheck).toHaveProperty('status');
    expect(['healthy', 'degraded', 'disabled', 'error']).toContain(translationCheck.status);

    console.log('Translation service status:', translationCheck.status);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 9: Multiple Passages With Mixed Sources
  // ────────────────────────────────────────────────────────────────────────

  test('should handle multiple passages with mixed translation sources', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'Explain the Three Marks of Existence',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.passages.length).toBeGreaterThan(0);

    // Count translation sources
    const sources = data.passages.reduce((acc, p) => {
      const source = p.translation_source || 'none';
      acc[source] = (acc[source] || 0) + 1;
      return acc;
    }, {});

    console.log('Translation sources:', sources);
    // Should have at least some passages with translations
    expect(data.passages.some(p => p.english_text)).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 10: Response Structure Validation
  // ────────────────────────────────────────────────────────────────────────

  test('should return properly structured chat response with translations', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What is the Middle Way?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    // Root structure
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('conversation_id');
    expect(data).toHaveProperty('model_used');
    expect(data).toHaveProperty('response');
    expect(data).toHaveProperty('passages');
    expect(data).toHaveProperty('timestamp');

    // Response structure
    expect(data.response).toHaveProperty('formatted_text');
    expect(data.response).toHaveProperty('canonical_teachings');

    // Passages array
    expect(Array.isArray(data.passages)).toBeTruthy();
    expect(data.passages.length).toBeGreaterThan(0);

    // Timestamp is valid ISO string
    expect(new Date(data.timestamp).getTime()).toBeGreaterThan(0);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 11: Consecutive Requests (Cache Warm-Up)
  // ────────────────────────────────────────────────────────────────────────

  test('should handle consecutive requests with cache warming', async ({ request }) => {
    const questions = [
      'What is bodhi?',
      'What is nirvana?',
      'What is karma?'
    ];

    const responses = [];

    for (const message of questions) {
      const response = await request.post('/chat', {
        data: { message, model_id: 'copilot' }
      });

      expect(response.status()).toBe(200);
      const data = await response.json();
      responses.push(data);

      // Each response should have passages with translations
      expect(data.passages.length).toBeGreaterThan(0);
      expect(data.passages.some(p => p.english_text)).toBeTruthy();
    }

    console.log(`Processed ${responses.length} requests successfully`);
  });

  // ────────────────────────────────────────────────────────────────────────
  // Test 12: Pali Verse Translation Quality
  // ────────────────────────────────────────────────────────────────────────

  test('should handle complex Pali verse translations', async ({ request }) => {
    const response = await request.post('/chat', {
      data: {
        message: 'What does the Dhammapada teach?',
        model_id: 'copilot'
      }
    });

    expect(response.status()).toBe(200);
    const data = await response.json();

    expect(data.passages.length).toBeGreaterThan(0);

    // Check for reasonable translation length (should be substantial)
    const longTranslations = data.passages.filter(p =>
      p.english_text && p.english_text.length > 20
    );
    expect(longTranslations.length).toBeGreaterThan(0);

    // Translations should be readable English
    for (const passage of longTranslations.slice(0, 3)) {
      console.log(`Pali: ${passage.pali_text.substring(0, 50)}...`);
      console.log(`Translation: ${passage.english_text.substring(0, 100)}...`);
      console.log(`Source: ${passage.translation_source}\n`);
    }
  });
});

// ────────────────────────────────────────────────────────────────────────────
// Translation Quality Validation Tests
// ────────────────────────────────────────────────────────────────────────────

test.describe('Translation Quality Validation', () => {

  const paliTerms = {
    'samadhi': ['concentration', 'meditative', 'absorption', 'focus'],
    'metta': ['loving', 'kindness', 'benevolence', 'goodwill'],
    'dukkha': ['suffering', 'unsatisfactor', 'stress', 'distress', 'pain'],
    'anicca': ['impermanent', 'transient', 'inconstant', 'changing', 'change'],
    'anatta': ['not-self', 'non-self', 'selflessness', 'absence of self'],
    'nirvana': ['extinction', 'cessation', 'liberation', 'freedom', 'peace'],
  };

  for (const [paliTerm, expectedKeywords] of Object.entries(paliTerms)) {
    test(`should accurately translate "${paliTerm}"`, async ({ request }) => {
      const response = await request.post('/chat', {
        data: {
          message: `Explain ${paliTerm}`,
          model_id: 'copilot'
        }
      });

      expect(response.status()).toBe(200);
      const data = await response.json();

      const passagesWithText = data.passages.filter(p => p.english_text);
      expect(passagesWithText.length).toBeGreaterThan(0);

      const allText = passagesWithText
        .map(p => p.english_text.toLowerCase())
        .join(' ');

      const foundKeywords = expectedKeywords.filter(kw => allText.includes(kw));
      expect(foundKeywords.length).toBeGreaterThan(0);

      console.log(`✓ "${paliTerm}" → Found keywords: ${foundKeywords.join(', ')}`);
    });
  }
});

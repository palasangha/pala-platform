-- Migration 003: Add Pali translation cache table
-- Stores Pali → English translations with TTL

CREATE TABLE IF NOT EXISTS pali_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pali_text TEXT NOT NULL UNIQUE,
    english_translation TEXT NOT NULL,
    reference TEXT,
    model_used TEXT DEFAULT 'deepseek-r1:32b',
    source TEXT DEFAULT 'ollama',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_pali_text ON pali_translations(pali_text);
CREATE INDEX IF NOT EXISTS idx_created_at ON pali_translations(created_at);
CREATE INDEX IF NOT EXISTS idx_expires_at ON pali_translations(expires_at);

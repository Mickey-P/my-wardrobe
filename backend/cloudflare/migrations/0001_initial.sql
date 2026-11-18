PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS wardrobe_items (
    id TEXT PRIMARY KEY CHECK (id GLOB 'W[0-9][0-9][0-9]'),
    catalog_fields TEXT NOT NULL DEFAULT '{}',
    user_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visual_descriptions (
    item_id TEXT PRIMARY KEY REFERENCES wardrobe_items(id) ON DELETE CASCADE,
    source_fields TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS outfits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    season TEXT NOT NULL DEFAULT '',
    occasion TEXT NOT NULL DEFAULT '',
    item_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_manifest (
    id TEXT PRIMARY KEY REFERENCES wardrobe_items(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL DEFAULT '',
    object_key TEXT,
    status TEXT NOT NULL DEFAULT 'missing_url',
    source_type TEXT NOT NULL DEFAULT 'catalog_original',
    mime_type TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_outfits_updated_at ON outfits(updated_at DESC);

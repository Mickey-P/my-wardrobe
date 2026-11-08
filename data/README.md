# My Wardrobe data

- `catalog.csv` — the current project catalog. Original source: `wardrobe_catalog_W001-W139_v8.csv`.
- `visual_descriptions.csv` — the current visual reference. Original source: `wardrobe_visual_descriptions_W001-W139_v3.csv`.
- `image_manifest.json` — local photo statuses, source URLs, and checksums.
- `images/` — original photos named by each item's permanent ID.

The versioned source CSV files in the project root remain unchanged. Catalog and visual-reference imports should update their fields separately by `id`, preserve user notes when incoming values are blank, and leave photos in place during routine catalog updates.

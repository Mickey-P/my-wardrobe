# Recovering photos from the Brave cache

This procedure is for manually recovering original images only. Chromium's cache may not contain the original URLs or filenames, so an image-to-ID match cannot be reliably recovered from the cache alone. Do not assign recovered images to items automatically.

## 1. Find the Brave profile

1. Open Brave and visit `brave://version`.
2. Find **Profile Path** and note its location. The profile directory usually ends in `Default` or `Profile 1`.
3. The image cache is usually under `Cache/Cache_Data` inside the profile. Chromium's layout can change between versions. You can also inspect `Code Cache` and `Service Worker/CacheStorage`, but those locations may not contain cached photo responses.

## 2. Make a copy of the cache

1. Close Brave completely, including background processes. Confirm in Task Manager that all Brave processes have exited.
2. Copy the cache folder to a separate working directory and work only on that copy. Do not move or rename files in the original profile.
3. Clearing the cache, updating the browser, or continuing to browse may remove useful entries.

## 3. Why cached files have unfamiliar names

Chromium stores cache entries using internal keys and indexes. Files may have internal names without extensions, contain multiple entries, or have metadata stored alongside the response body. A filename usually does not reveal the URL or wardrobe item ID.

## 4. Detect and verify formats from file contents

Do not guess extensions. Install Pillow in a separate Python environment and inspect candidate files:

```python
from pathlib import Path
from PIL import Image

for path in Path("cache-copy").rglob("*"):
    if not path.is_file():
        continue
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            print(path, image.format, image.size)
    except Exception:
        pass
```

This example finds files Pillow can open as images. It does not parse every Chromium cache format and does not prove that a file is an original photo from the catalog.

## 5. Match images manually

1. Create a contact sheet or gallery of the candidates and inspect each photo.
2. Compare each one with `wardrobe_photo_catalog.html`, the item description, and other confirmed references. Do not rely only on a similar color or category.
3. Select an ID from W001–W139 and ask the user to confirm the match.
4. After confirmation, copy the original bytes to `data/images/` using the item ID and the extension matching the detected format, such as `W001.webp`. Do not modify the image.
5. Update that ID's entry in `data/image_manifest.json` with source `manual_brave_cache`, path, MIME type, file size, and SHA-256. Record the confirmation or a note if your workflow supports it.
6. If a valid photo already exists for the ID, do not replace it without separate user confirmation. Never overwrite a file with an unconfirmed candidate.

If you cannot confidently confirm a match, leave the file unmatched and the item without a photo. That is safer than assigning the wrong image.

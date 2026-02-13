# Vercel Migration (Frontend + Python PPT Engine)

## What was added
- `ppt_engine.py`: UI-independent PPT generation engine.
- `api/generate.py`: FastAPI endpoint for PPT generation.
- `vercel.json`: Vercel Python function/rewrite config.

## API
`POST /api/generate`

Multipart form fields:
- `season_item` (string)
- `season_color` (hex string, optional, default `#000000`)
- `name` (string, required)
- `code` (string, required)
- `logo` (string, optional, logo filename in `assets/logos`)
- `artworks` (comma-separated artwork filenames in `assets/artworks`)
- `color_names` (comma-separated names, order-matched with `color_images`)
- `main_image` (file, required)
- `color_images` (file[], optional)

Response:
- `.pptx` binary download

## Notes
- Keep fonts installed on runtime/authoring environment for visual consistency.
- Artwork type metadata is loaded from `assets/artworks/_meta.json`.

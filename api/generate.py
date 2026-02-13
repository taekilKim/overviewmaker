from __future__ import annotations

import io
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ppt_engine import generate_pptx

app = FastAPI(title="OverviewMaker API")

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = str(ROOT / "template.pptx")
LOGO_DIR = str(ROOT / "assets" / "logos")
ARTWORK_DIR = str(ROOT / "assets" / "artworks")
ASSETS_DIR = ROOT / "assets"
ARTWORK_META_FILE = Path(ARTWORK_DIR) / "_meta.json"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _asset_dir(kind: str) -> Path:
    k = (kind or "").strip().lower()
    if k in ("logo", "logos"):
        return Path(LOGO_DIR)
    if k in ("artwork", "artworks"):
        return Path(ARTWORK_DIR)
    raise HTTPException(status_code=400, detail="invalid kind")


def _list_files(folder: Path) -> List[str]:
    if not folder.exists():
        return []
    allowed = {".png", ".jpg", ".jpeg", ".svg"}
    return sorted(
        [p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in allowed],
        key=str.casefold,
    )


def _load_artwork_meta() -> dict:
    if not ARTWORK_META_FILE.exists():
        return {}
    try:
        return json.loads(ARTWORK_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_artwork_meta(meta: dict) -> None:
    ARTWORK_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_bytes_file(upload: UploadFile):
    data = upload.file.read()
    buff = io.BytesIO(data)
    buff.seek(0)
    return buff


@app.get("/")
def root():
    html_path = ROOT / "web" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse({"ok": True, "service": "overviewmaker-api"})


@app.get("/health")
def health():
    return JSONResponse({"ok": True, "service": "overviewmaker-api"})


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/api/assets")
def list_assets(kind: str):
    folder = _asset_dir(kind)
    folder.mkdir(parents=True, exist_ok=True)
    files = _list_files(folder)
    sub = "logos" if folder == Path(LOGO_DIR) else "artworks"
    payload = [{"name": f, "url": f"/assets/{sub}/{f}"} for f in files]
    data = {"kind": kind, "files": payload}
    if folder == Path(ARTWORK_DIR):
        meta = _load_artwork_meta()
        for f in files:
            meta.setdefault(f, "default")
        stale = [k for k in list(meta.keys()) if k not in files]
        for k in stale:
            meta.pop(k, None)
        _save_artwork_meta(meta)
        data["meta"] = meta
    return JSONResponse(data)


@app.post("/api/assets/upload")
def upload_assets(kind: str = Form(...), files: List[UploadFile] = File(default=[])):
    folder = _asset_dir(kind)
    folder.mkdir(parents=True, exist_ok=True)
    if not files:
        raise HTTPException(status_code=400, detail="no files")
    saved = []
    for f in files:
        name = Path(f.filename or "").name
        if not name:
            continue
        target = folder / name
        target.write_bytes(f.file.read())
        saved.append(name)
    if folder == Path(ARTWORK_DIR):
        meta = _load_artwork_meta()
        for name in saved:
            meta.setdefault(name, "default")
        _save_artwork_meta(meta)
    return JSONResponse({"ok": True, "saved": saved})


@app.delete("/api/assets")
def delete_asset(kind: str, name: str):
    folder = _asset_dir(kind)
    target = folder / Path(name).name
    if target.exists():
        target.unlink()
    if folder == Path(ARTWORK_DIR):
        meta = _load_artwork_meta()
        meta.pop(Path(name).name, None)
        _save_artwork_meta(meta)
    return JSONResponse({"ok": True})


@app.post("/api/assets/artwork-mode")
def set_artwork_mode(name: str = Form(...), mode: str = Form(...)):
    allowed = {"default", "horizontal", "small"}
    if mode not in allowed:
        raise HTTPException(status_code=400, detail="invalid mode")
    meta = _load_artwork_meta()
    meta[Path(name).name] = mode
    _save_artwork_meta(meta)
    return JSONResponse({"ok": True})


@app.post("/api/generate")
def generate(
    season_item: str = Form(""),
    season_color: str = Form("#000000"),
    name: str = Form(...),
    code: str = Form(...),
    logo: str = Form("선택 없음"),
    artworks: str = Form(""),  # comma-separated artwork filenames
    color_names: str = Form(""),  # comma-separated
    main_image: UploadFile = File(...),
    color_images: List[UploadFile] = File(default=[]),
):
    if not code.strip():
        raise HTTPException(status_code=400, detail="code is required")

    artwork_list = [a.strip() for a in artworks.split(",") if a.strip()]
    color_name_list = [n.strip() for n in color_names.split(",") if n.strip()]

    colors = []
    for i, img in enumerate(color_images):
        color_name = color_name_list[i] if i < len(color_name_list) else ""
        colors.append({"img": _to_bytes_file(img), "name": color_name})

    product = {
        "season_item": season_item,
        "season_color": season_color,
        "name": name,
        "code": code,
        "rrp": "",
        "main_image": _to_bytes_file(main_image),
        "logo": logo,
        "artworks": artwork_list,
        "colors": colors,
    }

    ppt = generate_pptx(
        products=[product],
        template_file=TEMPLATE_FILE,
        logo_dir=LOGO_DIR,
        artwork_dir=ARTWORK_DIR,
    )

    return StreamingResponse(
        ppt,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="BOSS_Golf_SpecSheet.pptx"'},
    )

from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
from pathlib import Path
from typing import List, Optional
from urllib import error, parse, request

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
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


def _to_bytes_file(upload: UploadFile):
    data = upload.file.read()
    buff = io.BytesIO(data)
    buff.seek(0)
    return buff


def _asset_dir(kind: str) -> Path:
    k = (kind or "").strip().lower()
    if k in ("logo", "logos"):
        return Path(LOGO_DIR)
    if k in ("artwork", "artworks"):
        return Path(ARTWORK_DIR)
    raise HTTPException(status_code=400, detail="invalid kind")


def _asset_subdir(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k in ("logo", "logos"):
        return "logos"
    if k in ("artwork", "artworks"):
        return "artworks"
    raise HTTPException(status_code=400, detail="invalid kind")


def _list_files_local(folder: Path) -> List[str]:
    if not folder.exists():
        return []
    allowed = {".png", ".jpg", ".jpeg", ".svg"}
    return sorted(
        [p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in allowed],
        key=str.casefold,
    )


def _load_artwork_meta_local() -> dict:
    if not ARTWORK_META_FILE.exists():
        return {}
    try:
        return json.loads(ARTWORK_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_artwork_meta_local(meta: dict) -> None:
    ARTWORK_META_FILE.parent.mkdir(parents=True, exist_ok=True)
    ARTWORK_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _gh_cfg() -> Optional[dict]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPO", "").strip()
    branch = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
    if not token or not repo:
        return None
    return {"token": token, "repo": repo, "branch": branch}


def _gh_request(method: str, path: str, payload: Optional[dict] = None):
    cfg = _gh_cfg()
    if not cfg:
        raise HTTPException(status_code=500, detail="github config missing")

    url = f"https://api.github.com/repos/{cfg['repo']}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "overviewmaker-api",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        if e.code == 404:
            raise FileNotFoundError(path)
        raise HTTPException(status_code=502, detail=f"github api error: {e.code} {body[:200]}")


def _gh_get_content(path_in_repo: str) -> Optional[dict]:
    try:
        data = _gh_request("GET", f"/contents/{parse.quote(path_in_repo)}")
    except FileNotFoundError:
        return None
    content = (data.get("content") or "").replace("\n", "")
    decoded = base64.b64decode(content) if content else b""
    return {"sha": data.get("sha"), "bytes": decoded}


def _gh_put_content(path_in_repo: str, content_bytes: bytes, message: str):
    cfg = _gh_cfg()
    if not cfg:
        raise HTTPException(status_code=500, detail="github config missing")
    existing = _gh_get_content(path_in_repo)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": cfg["branch"],
    }
    if existing and existing.get("sha"):
        payload["sha"] = existing["sha"]
    _gh_request("PUT", f"/contents/{parse.quote(path_in_repo)}", payload)


def _gh_delete_content(path_in_repo: str, message: str):
    cfg = _gh_cfg()
    if not cfg:
        raise HTTPException(status_code=500, detail="github config missing")
    existing = _gh_get_content(path_in_repo)
    if not existing or not existing.get("sha"):
        return
    payload = {
        "message": message,
        "sha": existing["sha"],
        "branch": cfg["branch"],
    }
    _gh_request("DELETE", f"/contents/{parse.quote(path_in_repo)}", payload)


def _gh_list_assets(subdir: str) -> List[str]:
    data = _gh_request("GET", f"/contents/{parse.quote(f'assets/{subdir}')}")
    if not isinstance(data, list):
        return []
    allowed = {".png", ".jpg", ".jpeg", ".svg"}
    files = []
    for item in data:
        name = item.get("name", "")
        if Path(name).suffix.lower() in allowed:
            files.append(name)
    return sorted(files, key=str.casefold)


def _load_artwork_meta() -> dict:
    cfg = _gh_cfg()
    if not cfg:
        return _load_artwork_meta_local()
    doc = _gh_get_content("assets/artworks/_meta.json")
    if not doc:
        return {}
    try:
        return json.loads(doc["bytes"].decode("utf-8"))
    except Exception:
        return {}


def _save_artwork_meta(meta: dict):
    _save_artwork_meta_local(meta)
    if _gh_cfg():
        _gh_put_content(
            "assets/artworks/_meta.json",
            json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
            "Update artwork meta",
        )


def _sync_asset_from_github(kind: str, name: str):
    cfg = _gh_cfg()
    if not cfg:
        return
    safe_name = Path(name).name
    local_dir = _asset_dir(kind)
    local_dir.mkdir(parents=True, exist_ok=True)
    target = local_dir / safe_name
    if target.exists():
        return
    subdir = _asset_subdir(kind)
    doc = _gh_get_content(f"assets/{subdir}/{safe_name}")
    if doc and doc.get("bytes") is not None:
        target.write_bytes(doc["bytes"])


def _asset_bytes(kind: str, name: str) -> bytes:
    safe_name = Path(name).name
    folder = _asset_dir(kind)
    folder.mkdir(parents=True, exist_ok=True)
    local_file = folder / safe_name
    if local_file.exists():
        return local_file.read_bytes()

    cfg = _gh_cfg()
    if cfg:
        subdir = _asset_subdir(kind)
        doc = _gh_get_content(f"assets/{subdir}/{safe_name}")
        if doc and doc.get("bytes") is not None:
            local_file.write_bytes(doc["bytes"])
            return doc["bytes"]

    raise HTTPException(status_code=404, detail="asset not found")


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
    sub = _asset_subdir(kind)
    if _gh_cfg():
        try:
            files = _gh_list_assets(sub)
        except FileNotFoundError:
            files = []
    else:
        folder = _asset_dir(kind)
        folder.mkdir(parents=True, exist_ok=True)
        files = _list_files_local(folder)

    payload = [{"name": f, "url": f"/api/assets/file?kind={kind}&name={parse.quote(f)}"} for f in files]
    data = {"kind": kind, "files": payload}

    if sub == "artworks":
        meta = _load_artwork_meta()
        for f in files:
            meta.setdefault(f, "default")
        stale = [k for k in list(meta.keys()) if k not in files]
        for k in stale:
            meta.pop(k, None)
        _save_artwork_meta(meta)
        data["meta"] = meta

    return JSONResponse(data)


@app.get("/api/assets/file")
def asset_file(kind: str = Query(...), name: str = Query(...)):
    content = _asset_bytes(kind, name)
    mime = mimetypes.guess_type(Path(name).name)[0] or "application/octet-stream"
    return Response(content=content, media_type=mime)


@app.post("/api/assets/upload")
def upload_assets(kind: str = Form(...), files: List[UploadFile] = File(default=[])):
    folder = _asset_dir(kind)
    folder.mkdir(parents=True, exist_ok=True)
    if not files:
        raise HTTPException(status_code=400, detail="no files")

    sub = _asset_subdir(kind)
    saved = []
    for f in files:
        name = Path(f.filename or "").name
        if not name:
            continue
        data = f.file.read()
        (folder / name).write_bytes(data)
        if _gh_cfg():
            _gh_put_content(f"assets/{sub}/{name}", data, f"Upload {name}")
        saved.append(name)

    if sub == "artworks":
        meta = _load_artwork_meta()
        for name in saved:
            meta.setdefault(name, "default")
        _save_artwork_meta(meta)

    return JSONResponse({"ok": True, "saved": saved})


@app.delete("/api/assets")
def delete_asset(kind: str, name: str):
    safe = Path(name).name
    folder = _asset_dir(kind)
    target = folder / safe
    if target.exists():
        target.unlink()

    sub = _asset_subdir(kind)
    if _gh_cfg():
        _gh_delete_content(f"assets/{sub}/{safe}", f"Delete {safe}")

    if sub == "artworks":
        meta = _load_artwork_meta()
        meta.pop(safe, None)
        _save_artwork_meta(meta)

    return JSONResponse({"ok": True})


@app.post("/api/assets/artwork-mode")
def set_artwork_mode(name: str = Form(...), mode: str = Form(...)):
    allowed = {"default", "horizontal", "small"}
    if mode not in allowed:
        raise HTTPException(status_code=400, detail="invalid mode")
    safe = Path(name).name
    meta = _load_artwork_meta()
    meta[safe] = mode
    _save_artwork_meta(meta)
    return JSONResponse({"ok": True})


@app.post("/api/generate")
def generate(
    season_item: str = Form(""),
    season_color: str = Form("#000000"),
    name: str = Form(...),
    code: str = Form(...),
    logo: str = Form("선택 없음"),
    artworks: str = Form(""),
    color_names: str = Form(""),
    main_image: UploadFile = File(...),
    color_images: List[UploadFile] = File(default=[]),
):
    if not code.strip():
        raise HTTPException(status_code=400, detail="code is required")

    artwork_list = [a.strip() for a in artworks.split(",") if a.strip()]
    color_name_list = [n.strip() for n in color_names.split(",") if n.strip()]

    if logo and logo != "선택 없음":
        _sync_asset_from_github("logo", logo)
    for art in artwork_list:
        _sync_asset_from_github("artwork", art)

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

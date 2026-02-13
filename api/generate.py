from __future__ import annotations

import io
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from ppt_engine import generate_pptx

app = FastAPI(title="OverviewMaker API")

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = str(ROOT / "template.pptx")
LOGO_DIR = str(ROOT / "assets" / "logos")
ARTWORK_DIR = str(ROOT / "assets" / "artworks")


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

from fastapi import FastAPI

from .generate import app as generate_app

app = FastAPI(title="OverviewMaker API Entrypoint")
app.mount("/", generate_app)

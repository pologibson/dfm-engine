from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="DFM Auto Generator MVP",
    version="0.1.0",
    description="Mock-based DFM report generator powered by FastAPI and python-pptx.",
)

app.include_router(router)

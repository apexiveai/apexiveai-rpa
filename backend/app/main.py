from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db import Base, engine
from app.models import rpa  # noqa: F401
from app.api.rpa import router as rpa_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rpa_router, prefix=settings.api_prefix)

@app.get("/")
def root():
    return {"product": settings.app_name, "status": "online"}

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.api.face import router as face_router
from app.service.config_service import ConfigService
from app.service.face_engine import FaceEngine
from app.service.gallery_service import GalleryService
from app.service.index_service import IndexService
from app.service.liveness_service import LivenessService
from app.service.liveness_test_service import LivenessTestService

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GALLERY_DIR = BASE_DIR / "data" / "gallery"
INDEX_DIR = BASE_DIR / "data" / "index"
LIVENESS_DATA_DIR = BASE_DIR / "data" / "liveness"
MODEL_DIR = BASE_DIR / "models"
CONFIG_FILE = BASE_DIR / "config" / "settings.yaml"


def create_app() -> FastAPI:
    app = FastAPI(title="Python Face Demo", version="0.1.0")

    config_service = ConfigService(CONFIG_FILE)
    settings = config_service.get_settings()
    face_engine = FaceEngine(
        MODEL_DIR,
        detection_score_threshold=settings["detection_score_threshold"],
    )
    liveness_service = LivenessService(
        base_dir=BASE_DIR,
        face_engine=face_engine,
        model_relative_path=settings["liveness_model_path"],
        threshold=settings["liveness_threshold"],
        enabled=settings["liveness_enabled"],
    )
    liveness_test_service = LivenessTestService(
        data_dir=LIVENESS_DATA_DIR,
        liveness_service=liveness_service,
    )
    index_service = IndexService(INDEX_DIR)
    gallery_service = GalleryService(
        gallery_dir=GALLERY_DIR,
        face_engine=face_engine,
        index_service=index_service,
    )

    app.state.config_service = config_service
    app.state.face_engine = face_engine
    app.state.liveness_service = liveness_service
    app.state.liveness_test_service = liveness_test_service
    app.state.index_service = index_service
    app.state.gallery_service = gallery_service

    @app.on_event("startup")
    def load_index() -> None:
        try:
            index_service.load()
        except Exception:
            app.state.index_service.index = None
            app.state.index_service.metadata = []
            app.state.index_service.dimension = None

    app.include_router(face_router)
    return app


app = create_app()

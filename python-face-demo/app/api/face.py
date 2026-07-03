from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile

from app.model.schemas import (
    GalleryPrecheckResponse,
    GalleryRebuildResponse,
    HealthResponse,
    LivenessBatchTestResponse,
    LivenessCheckResponse,
    RecognizeResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    index_service = request.app.state.index_service
    return HealthResponse(
        service="python-face-demo",
        index_ready=index_service.ready,
        face_count=index_service.face_count,
        employee_count=index_service.employee_count,
    )


@router.post("/api/gallery/rebuild", response_model=GalleryRebuildResponse)
def rebuild_gallery(request: Request) -> GalleryRebuildResponse:
    gallery_service = request.app.state.gallery_service
    try:
        result = gallery_service.rebuild_gallery()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GalleryRebuildResponse(**result)


@router.post("/api/gallery/precheck", response_model=GalleryPrecheckResponse)
def precheck_gallery(request: Request) -> GalleryPrecheckResponse:
    gallery_service = request.app.state.gallery_service
    try:
        result = gallery_service.precheck_gallery()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GalleryPrecheckResponse(**result)


@router.get("/api/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    config_service = request.app.state.config_service
    settings = config_service.get_settings()
    return SettingsResponse(
        detectionScoreThreshold=settings["detection_score_threshold"],
        recognitionThreshold=settings["recognition_threshold"],
        livenessEnabled=settings["liveness_enabled"],
        livenessThreshold=settings["liveness_threshold"],
        livenessModelPath=settings["liveness_model_path"],
    )


@router.post("/api/settings", response_model=SettingsResponse)
def update_settings(
    request: Request,
    payload: SettingsUpdateRequest = Body(...),
) -> SettingsResponse:
    config_service = request.app.state.config_service
    face_engine = request.app.state.face_engine
    liveness_service = request.app.state.liveness_service
    try:
        settings = config_service.update_settings(
            detection_score_threshold=payload.detection_score_threshold,
            recognition_threshold=payload.recognition_threshold,
            liveness_enabled=payload.liveness_enabled,
            liveness_threshold=payload.liveness_threshold,
            liveness_model_path=payload.liveness_model_path,
        )
        face_engine.set_detection_threshold(settings["detection_score_threshold"])
        liveness_service.refresh_settings(
            enabled=settings["liveness_enabled"],
            threshold=settings["liveness_threshold"],
            model_relative_path=settings["liveness_model_path"],
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SettingsResponse(
        detectionScoreThreshold=settings["detection_score_threshold"],
        recognitionThreshold=settings["recognition_threshold"],
        livenessEnabled=settings["liveness_enabled"],
        livenessThreshold=settings["liveness_threshold"],
        livenessModelPath=settings["liveness_model_path"],
    )


@router.post("/api/face/liveness-check", response_model=LivenessCheckResponse)
async def liveness_check(
    request: Request,
    file: UploadFile = File(...),
) -> LivenessCheckResponse:
    liveness_service = request.app.state.liveness_service

    started_at = perf_counter()
    try:
        file_bytes = await file.read()
        result = liveness_service.check_from_bytes(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    return LivenessCheckResponse(
        livenessResult=result["livenessResult"],
        livenessScore=result["livenessScore"],
        threshold=result["threshold"],
        elapsedMs=elapsed_ms,
        message=result["message"],
    )


@router.post("/api/face/liveness-batch-test", response_model=LivenessBatchTestResponse)
def liveness_batch_test(request: Request) -> LivenessBatchTestResponse:
    liveness_test_service = request.app.state.liveness_test_service
    try:
        result = liveness_test_service.run_batch_test()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LivenessBatchTestResponse(**result)


@router.post("/api/face/recognize", response_model=RecognizeResponse)
async def recognize_face(
    request: Request,
    file: UploadFile = File(...),
    threshold: float | None = Query(default=None, ge=0.0, le=1.0),
    top_k: int = Query(default=1, ge=1, le=5),
) -> RecognizeResponse:
    face_engine = request.app.state.face_engine
    index_service = request.app.state.index_service
    config_service = request.app.state.config_service
    liveness_service = request.app.state.liveness_service

    if not index_service.ready:
        raise HTTPException(status_code=400, detail="Index is not ready. Please rebuild gallery first.")

    effective_threshold = (
        threshold
        if threshold is not None
        else float(config_service.get_settings()["recognition_threshold"])
    )

    started_at = perf_counter()
    try:
        file_bytes = await file.read()
        liveness_result = liveness_service.check_from_bytes(file_bytes)
        if liveness_result["livenessResult"] == "REJECT":
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            return RecognizeResponse(
                matched=False,
                employeeNo=None,
                employeeName=None,
                livenessResult=liveness_result["livenessResult"],
                livenessScore=liveness_result["livenessScore"],
                livenessThreshold=liveness_result["threshold"],
                similarity=0.0,
                threshold=effective_threshold,
                elapsedMs=elapsed_ms,
                message="Liveness rejected.",
            )
        embedding = face_engine.extract_embedding_from_bytes(file_bytes)
        results = index_service.search(embedding=embedding, top_k=top_k)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    elapsed_ms = int((perf_counter() - started_at) * 1000)
    if not results:
        return RecognizeResponse(
            matched=False,
            employeeNo=None,
            employeeName=None,
            livenessResult=liveness_result["livenessResult"],
            livenessScore=liveness_result["livenessScore"],
            livenessThreshold=liveness_result["threshold"],
            similarity=0.0,
            threshold=effective_threshold,
            elapsedMs=elapsed_ms,
            message="No candidate found.",
        )

    best_match = results[0]
    similarity = float(best_match["similarity"])
    matched = similarity >= effective_threshold
    return RecognizeResponse(
        matched=matched,
        employeeNo=best_match.get("employeeNo") if matched else None,
        employeeName=best_match.get("employeeName") if matched else None,
        livenessResult=liveness_result["livenessResult"],
        livenessScore=liveness_result["livenessScore"],
        livenessThreshold=liveness_result["threshold"],
        similarity=similarity,
        threshold=effective_threshold,
        elapsedMs=elapsed_ms,
        message="Matched." if matched else "Similarity below threshold.",
    )

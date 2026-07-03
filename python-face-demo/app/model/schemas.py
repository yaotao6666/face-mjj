from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    success: bool = True
    service: str
    index_ready: bool
    face_count: int
    employee_count: int


class GalleryFailedItem(BaseModel):
    employee_no: str = Field(alias="employeeNo")
    employee_name: str = Field(alias="employeeName")
    image_path: str = Field(alias="imagePath")
    reason: str

    class Config:
        populate_by_name = True


class GalleryRebuildResponse(BaseModel):
    success: bool = True
    message: str
    employee_count: int
    image_count: int
    indexed_count: int
    failed_count: int
    index_path: str
    metadata_path: str
    failed_files: list[GalleryFailedItem] = Field(default_factory=list, alias="failedFiles")

    class Config:
        populate_by_name = True


class GalleryPrecheckResponse(BaseModel):
    success: bool = True
    message: str
    employee_count: int
    image_count: int
    passed_count: int
    failed_count: int
    failed_files: list[GalleryFailedItem] = Field(default_factory=list, alias="failedFiles")

    class Config:
        populate_by_name = True


class SettingsResponse(BaseModel):
    success: bool = True
    detection_score_threshold: float = Field(alias="detectionScoreThreshold")
    recognition_threshold: float = Field(alias="recognitionThreshold")
    liveness_enabled: bool = Field(alias="livenessEnabled")
    liveness_threshold: float = Field(alias="livenessThreshold")
    liveness_model_path: str = Field(alias="livenessModelPath")

    class Config:
        populate_by_name = True


class SettingsUpdateRequest(BaseModel):
    detection_score_threshold: float | None = Field(default=None, alias="detectionScoreThreshold")
    recognition_threshold: float | None = Field(default=None, alias="recognitionThreshold")
    liveness_enabled: bool | None = Field(default=None, alias="livenessEnabled")
    liveness_threshold: float | None = Field(default=None, alias="livenessThreshold")
    liveness_model_path: str | None = Field(default=None, alias="livenessModelPath")

    class Config:
        populate_by_name = True


class LivenessCheckResponse(BaseModel):
    success: bool = True
    liveness_result: str = Field(alias="livenessResult")
    liveness_score: float = Field(alias="livenessScore")
    threshold: float
    elapsed_ms: int = Field(alias="elapsedMs")
    message: str

    class Config:
        populate_by_name = True


class LivenessSampleResult(BaseModel):
    sample_path: str = Field(alias="samplePath")
    sample_type: str = Field(alias="sampleType")
    liveness_result: str = Field(alias="livenessResult")
    liveness_score: float | None = Field(default=None, alias="livenessScore")
    expected_result: str = Field(alias="expectedResult")
    is_correct: bool = Field(alias="isCorrect")
    message: str

    class Config:
        populate_by_name = True


class LivenessBatchTestResponse(BaseModel):
    success: bool = True
    message: str
    total_count: int = Field(alias="totalCount")
    real_count: int = Field(alias="realCount")
    photo_spoof_count: int = Field(alias="photoSpoofCount")
    screen_spoof_count: int = Field(alias="screenSpoofCount")
    accuracy: float
    real_pass_rate: float = Field(alias="realPassRate")
    photo_reject_rate: float = Field(alias="photoRejectRate")
    screen_reject_rate: float = Field(alias="screenRejectRate")
    sample_results: list[LivenessSampleResult] = Field(default_factory=list, alias="sampleResults")

    class Config:
        populate_by_name = True


class RecognizeResponse(BaseModel):
    success: bool = True
    matched: bool
    employee_no: str | None = Field(default=None, alias="employeeNo")
    employee_name: str | None = Field(default=None, alias="employeeName")
    liveness_result: str = Field(alias="livenessResult")
    liveness_score: float = Field(alias="livenessScore")
    liveness_threshold: float = Field(alias="livenessThreshold")
    similarity: float
    threshold: float
    elapsed_ms: int = Field(alias="elapsedMs")
    message: str

    class Config:
        populate_by_name = True

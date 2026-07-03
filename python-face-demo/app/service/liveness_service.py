from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

import cv2
import numpy as np
import onnxruntime as ort


class LivenessService:
    MODEL_URL = (
        "https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/models/"
        "best_model_quantized.onnx"
    )
    MIN_MODEL_SIZE_BYTES = 500_000

    def __init__(
        self,
        base_dir: str | Path,
        face_engine,
        model_relative_path: str,
        threshold: float = 0.5,
        enabled: bool = True,
        model_img_size: int = 128,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.face_engine = face_engine
        self.model_relative_path = model_relative_path
        self.threshold = float(threshold)
        self.enabled = bool(enabled)
        self.model_img_size = model_img_size
        self._session = None
        self._input_name = None

    @property
    def model_path(self) -> Path:
        return self.base_dir / self.model_relative_path

    def refresh_settings(
        self,
        *,
        enabled: bool,
        threshold: float,
        model_relative_path: str,
    ) -> None:
        self.enabled = bool(enabled)
        self.threshold = float(threshold)
        if self.model_relative_path != model_relative_path:
            self.model_relative_path = model_relative_path
            self._session = None
            self._input_name = None

    def _ensure_model(self) -> None:
        if self._session is not None and self._input_name is not None:
            return

        model_path = self.model_path
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if not model_path.exists():
            self._download_model(model_path)

        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        available_providers = ort.get_available_providers()
        providers = [provider for provider in ("CUDAExecutionProvider", "CPUExecutionProvider") if provider in available_providers]
        if not providers:
            providers = available_providers

        try:
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=session_options,
                providers=providers,
            )
            self._input_name = self._session.get_inputs()[0].name
        except Exception:
            if model_path.exists():
                model_path.unlink()
            self._download_model(model_path)
            self._session = ort.InferenceSession(
                str(model_path),
                sess_options=session_options,
                providers=providers,
            )
            self._input_name = self._session.get_inputs()[0].name

    @staticmethod
    def _download_model(model_path: Path) -> None:
        last_error = None
        for _ in range(3):
            temp_path = model_path.with_suffix(model_path.suffix + ".part")
            if temp_path.exists():
                temp_path.unlink()
            try:
                with urlopen(LivenessService.MODEL_URL) as response, temp_path.open("wb") as file:
                    file.write(response.read())
                if temp_path.stat().st_size < LivenessService.MIN_MODEL_SIZE_BYTES:
                    raise ValueError("Downloaded liveness model is incomplete.")
                temp_path.replace(model_path)
                return
            except Exception as exc:
                last_error = exc
                if temp_path.exists():
                    temp_path.unlink()
        raise RuntimeError(f"Failed to download liveness model: {last_error}")

    @staticmethod
    def _threshold_to_logit(threshold: float) -> float:
        probability = max(1e-6, min(1.0 - 1e-6, float(threshold)))
        return float(np.log(probability / (1.0 - probability)))

    def _preprocess_face_crop(self, face_crop_bgr: np.ndarray) -> np.ndarray:
        image_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
        old_height, old_width = image_rgb.shape[:2]
        ratio = float(self.model_img_size) / max(old_height, old_width)
        scaled_shape = (
            max(1, int(round(old_height * ratio))),
            max(1, int(round(old_width * ratio))),
        )
        interpolation = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
        resized = cv2.resize(
            image_rgb,
            (scaled_shape[1], scaled_shape[0]),
            interpolation=interpolation,
        )

        delta_w = self.model_img_size - scaled_shape[1]
        delta_h = self.model_img_size - scaled_shape[0]
        top = delta_h // 2
        bottom = delta_h - top
        left = delta_w // 2
        right = delta_w - left
        padded = cv2.copyMakeBorder(
            resized,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_REFLECT_101,
        )
        chw = padded.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.expand_dims(chw, axis=0)

    def _infer_face_crop(self, face_crop_bgr: np.ndarray) -> dict:
        if not self.enabled:
            return {
                "livenessResult": "SKIPPED",
                "livenessScore": 1.0,
                "threshold": self.threshold,
                "message": "Liveness check is disabled.",
            }

        self._ensure_model()
        batch_input = self._preprocess_face_crop(face_crop_bgr)
        logits = self._session.run([], {self._input_name: batch_input})[0]
        if logits.shape != (1, 2):
            raise ValueError("Invalid liveness model output shape.")

        real_logit = float(logits[0][0])
        spoof_logit = float(logits[0][1])
        logit_diff = real_logit - spoof_logit
        is_real = logit_diff >= self._threshold_to_logit(self.threshold)
        return {
            "livenessResult": "PASS" if is_real else "REJECT",
            "livenessScore": logit_diff,
            "threshold": self.threshold,
            "message": "Liveness passed." if is_real else "Liveness rejected.",
        }

    def check_from_bytes(self, file_bytes: bytes) -> dict:
        face_crop_bgr = self.face_engine.extract_face_crop_from_bytes(file_bytes)
        return self._infer_face_crop(face_crop_bgr)

    def check_from_path(self, image_path: str | Path) -> dict:
        face_crop_bgr = self.face_engine.extract_face_crop_from_path(image_path)
        return self._infer_face_crop(face_crop_bgr)

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.request import urlretrieve

import cv2
import numpy as np
from PIL import Image

class FaceEngine:
    DETECTOR_URL = (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    )
    RECOGNIZER_URL = (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    )

    def __init__(self, model_dir: str | Path, detection_score_threshold: float = 0.85) -> None:
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.detector_path = self.model_dir / "face_detection_yunet_2023mar.onnx"
        self.recognizer_path = self.model_dir / "face_recognition_sface_2021dec.onnx"
        self.detection_score_threshold = float(detection_score_threshold)
        self._detector = None
        self._recognizer = None

    def _ensure_models(self) -> None:
        if not self.detector_path.exists():
            urlretrieve(self.DETECTOR_URL, self.detector_path)
        if not self.recognizer_path.exists():
            urlretrieve(self.RECOGNIZER_URL, self.recognizer_path)

    def _ensure_app(self) -> None:
        if self._detector is not None and self._recognizer is not None:
            return
        self._ensure_models()
        self._detector = cv2.FaceDetectorYN.create(
            str(self.detector_path),
            "",
            (640, 640),
            score_threshold=self.detection_score_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(
            str(self.recognizer_path), ""
        )

    def set_detection_threshold(self, detection_score_threshold: float) -> None:
        new_threshold = float(detection_score_threshold)
        if self.detection_score_threshold == new_threshold:
            return
        self.detection_score_threshold = new_threshold
        self._detector = None

    @staticmethod
    def _image_to_bgr(image: Image.Image) -> np.ndarray:
        rgb = image.convert("RGB")
        return np.asarray(rgb)[:, :, ::-1]

    @staticmethod
    def _crop_square_face(image_bgr: np.ndarray, face: np.ndarray, expansion_factor: float = 1.5) -> np.ndarray:
        image_height, image_width = image_bgr.shape[:2]
        x, y, w, h = [float(value) for value in face[:4]]
        if w <= 0 or h <= 0:
            raise ValueError("Invalid face bounding box.")

        max_dim = max(w, h)
        center_x = x + w / 2.0
        center_y = y + h / 2.0
        crop_size = max(1, int(round(max_dim * expansion_factor)))
        crop_x = int(round(center_x - crop_size / 2.0))
        crop_y = int(round(center_y - crop_size / 2.0))

        crop_x1 = max(0, crop_x)
        crop_y1 = max(0, crop_y)
        crop_x2 = min(image_width, crop_x + crop_size)
        crop_y2 = min(image_height, crop_y + crop_size)

        top_pad = max(0, -crop_y)
        left_pad = max(0, -crop_x)
        bottom_pad = max(0, (crop_y + crop_size) - image_height)
        right_pad = max(0, (crop_x + crop_size) - image_width)

        cropped = image_bgr[crop_y1:crop_y2, crop_x1:crop_x2, :]
        if cropped.size == 0:
            raise ValueError("Failed to crop face region.")

        result = cv2.copyMakeBorder(
            cropped,
            top_pad,
            bottom_pad,
            left_pad,
            right_pad,
            cv2.BORDER_REFLECT_101,
        )
        return result

    def detect_primary_face(self, image_bgr: np.ndarray) -> np.ndarray:
        self._ensure_app()
        height, width = image_bgr.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(image_bgr)
        if faces is None or len(faces) == 0:
            raise ValueError("No face detected in image.")
        return max(faces, key=lambda item: float(item[2] * item[3]))

    def _extract_from_bgr(self, image_bgr: np.ndarray) -> np.ndarray:
        self._ensure_app()
        face = self.detect_primary_face(image_bgr)
        aligned = self._recognizer.alignCrop(image_bgr, face)
        embedding = np.asarray(self._recognizer.feature(aligned), dtype=np.float32).flatten()
        if embedding.ndim != 1:
            raise ValueError("Invalid embedding returned by model.")
        return embedding

    def extract_embedding_from_bytes(self, file_bytes: bytes) -> np.ndarray:
        with Image.open(BytesIO(file_bytes)) as image:
            image_bgr = self._image_to_bgr(image)
        return self._extract_from_bgr(image_bgr)

    def extract_embedding_from_path(self, image_path: str | Path) -> np.ndarray:
        with Image.open(image_path) as image:
            image_bgr = self._image_to_bgr(image)
        return self._extract_from_bgr(image_bgr)

    def extract_face_crop_from_bytes(self, file_bytes: bytes, expansion_factor: float = 1.5) -> np.ndarray:
        with Image.open(BytesIO(file_bytes)) as image:
            image_bgr = self._image_to_bgr(image)
        face = self.detect_primary_face(image_bgr)
        return self._crop_square_face(image_bgr, face, expansion_factor=expansion_factor)

    def extract_face_crop_from_path(self, image_path: str | Path, expansion_factor: float = 1.5) -> np.ndarray:
        with Image.open(image_path) as image:
            image_bgr = self._image_to_bgr(image)
        face = self.detect_primary_face(image_bgr)
        return self._crop_square_face(image_bgr, face, expansion_factor=expansion_factor)

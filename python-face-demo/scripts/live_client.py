from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import requests


@dataclass
class FaceDemoClient:
    server_url: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        self.server_url = self.server_url.rstrip("/")

    def recognize_frame(
        self,
        frame_bgr: Any,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            return {
                "requestOk": False,
                "message": "Camera frame is empty.",
            }

        ok, encoded = cv2.imencode(".jpg", frame_bgr)
        if not ok:
            return {
                "requestOk": False,
                "message": "Failed to encode camera frame as JPEG.",
            }

        endpoint = f"{self.server_url}/api/face/recognize"
        params: dict[str, Any] = {}
        if threshold is not None:
            params["threshold"] = threshold

        files = {
            "file": ("frame.jpg", encoded.tobytes(), "image/jpeg"),
        }

        try:
            response = requests.post(
                endpoint,
                params=params,
                files=files,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            return {
                "requestOk": False,
                "message": f"Request failed: {exc}",
            }

        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            return {
                "requestOk": False,
                "statusCode": response.status_code,
                "message": text or "Server returned a non-JSON response.",
            }

        if response.ok:
            payload["requestOk"] = True
            return payload

        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            message = detail.strip()
        else:
            message = str(payload)

        return {
            "requestOk": False,
            "statusCode": response.status_code,
            "message": message,
            "errorBody": payload,
        }

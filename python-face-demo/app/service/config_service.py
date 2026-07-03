from __future__ import annotations

from pathlib import Path

import yaml


class ConfigService:
    DEFAULT_SETTINGS = {
        "detection_score_threshold": 0.85,
        "recognition_threshold": 0.8,
        "liveness_enabled": True,
        "liveness_threshold": 0.5,
        "liveness_model_path": "models/best_model_quantized.onnx",
    }

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load_or_create()

    def _load_or_create(self) -> dict:
        if not self.config_path.exists():
            self._write(self.DEFAULT_SETTINGS)
            return dict(self.DEFAULT_SETTINGS)

        with self.config_path.open("r", encoding="utf-8") as file:
            content = yaml.safe_load(file) or {}

        settings = dict(self.DEFAULT_SETTINGS)
        settings.update(content)
        self._validate(settings)
        if settings != content:
            self._write(settings)
        return settings

    def _write(self, settings: dict) -> None:
        with self.config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(settings, file, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _validate(settings: dict) -> None:
        for key in ("detection_score_threshold", "recognition_threshold", "liveness_threshold"):
            value = settings.get(key)
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid config for {key}: must be a number.")
            if value < 0.0 or value > 1.0:
                raise ValueError(f"Invalid config for {key}: must be between 0.0 and 1.0.")

        if not isinstance(settings.get("liveness_enabled"), bool):
            raise ValueError("Invalid config for liveness_enabled: must be a boolean.")

        model_path = settings.get("liveness_model_path")
        if not isinstance(model_path, str) or not model_path.strip():
            raise ValueError("Invalid config for liveness_model_path: must be a non-empty string.")

    def get_settings(self) -> dict:
        return dict(self._settings)

    def update_settings(
        self,
        detection_score_threshold: float | None = None,
        recognition_threshold: float | None = None,
        liveness_enabled: bool | None = None,
        liveness_threshold: float | None = None,
        liveness_model_path: str | None = None,
    ) -> dict:
        updated = dict(self._settings)
        if detection_score_threshold is not None:
            updated["detection_score_threshold"] = float(detection_score_threshold)
        if recognition_threshold is not None:
            updated["recognition_threshold"] = float(recognition_threshold)
        if liveness_enabled is not None:
            updated["liveness_enabled"] = bool(liveness_enabled)
        if liveness_threshold is not None:
            updated["liveness_threshold"] = float(liveness_threshold)
        if liveness_model_path is not None:
            updated["liveness_model_path"] = str(liveness_model_path).strip()
        self._validate(updated)
        self._write(updated)
        self._settings = updated
        return self.get_settings()

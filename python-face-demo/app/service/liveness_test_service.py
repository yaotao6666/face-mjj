from __future__ import annotations

from pathlib import Path


class LivenessTestService:
    SAMPLE_TYPES = {
        "real": "PASS",
        "photo_spoof": "REJECT",
        "screen_spoof": "REJECT",
    }
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(self, data_dir: str | Path, liveness_service) -> None:
        self.data_dir = Path(data_dir)
        self.liveness_service = liveness_service

    def _list_samples(self, sample_type: str) -> list[Path]:
        sample_dir = self.data_dir / sample_type
        if not sample_dir.exists():
            return []
        return sorted(
            file_path
            for file_path in sample_dir.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

    def run_batch_test(self) -> dict:
        sample_results = []
        total_count = 0
        correct_count = 0
        stats = {
            "real": {"total": 0, "pass": 0, "reject": 0},
            "photo_spoof": {"total": 0, "pass": 0, "reject": 0},
            "screen_spoof": {"total": 0, "pass": 0, "reject": 0},
        }

        for sample_type, expected_result in self.SAMPLE_TYPES.items():
            for sample_path in self._list_samples(sample_type):
                total_count += 1
                stats[sample_type]["total"] += 1
                try:
                    result = self.liveness_service.check_from_path(sample_path)
                    liveness_result = result["livenessResult"]
                    liveness_score = float(result["livenessScore"])
                    is_correct = liveness_result == expected_result
                    if liveness_result == "PASS":
                        stats[sample_type]["pass"] += 1
                    elif liveness_result == "REJECT":
                        stats[sample_type]["reject"] += 1
                    message = result["message"]
                except Exception as exc:
                    liveness_result = "ERROR"
                    liveness_score = None
                    is_correct = False
                    message = str(exc)

                if is_correct:
                    correct_count += 1

                sample_results.append(
                    {
                        "samplePath": str(sample_path),
                        "sampleType": sample_type,
                        "livenessResult": liveness_result,
                        "livenessScore": liveness_score,
                        "expectedResult": expected_result,
                        "isCorrect": is_correct,
                        "message": message,
                    }
                )

        if total_count == 0:
            return {
                "success": False,
                "message": "No liveness samples found.",
                "totalCount": 0,
                "realCount": 0,
                "photoSpoofCount": 0,
                "screenSpoofCount": 0,
                "accuracy": 0.0,
                "realPassRate": 0.0,
                "photoRejectRate": 0.0,
                "screenRejectRate": 0.0,
                "sampleResults": [],
            }

        def safe_rate(numerator: int, denominator: int) -> float:
            return float(numerator / denominator) if denominator else 0.0

        return {
            "success": True,
            "message": "Liveness batch test completed.",
            "totalCount": total_count,
            "realCount": stats["real"]["total"],
            "photoSpoofCount": stats["photo_spoof"]["total"],
            "screenSpoofCount": stats["screen_spoof"]["total"],
            "accuracy": safe_rate(correct_count, total_count),
            "realPassRate": safe_rate(stats["real"]["pass"], stats["real"]["total"]),
            "photoRejectRate": safe_rate(stats["photo_spoof"]["reject"], stats["photo_spoof"]["total"]),
            "screenRejectRate": safe_rate(stats["screen_spoof"]["reject"], stats["screen_spoof"]["total"]),
            "sampleResults": sample_results,
        }

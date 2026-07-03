from __future__ import annotations

from pathlib import Path

from app.service.face_engine import FaceEngine
from app.service.index_service import IndexService


class GalleryService:
    IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(self, gallery_dir: str | Path, face_engine: FaceEngine, index_service: IndexService) -> None:
        self.gallery_dir = Path(gallery_dir)
        self.face_engine = face_engine
        self.index_service = index_service

    @staticmethod
    def _parse_employee_dir_name(dir_name: str) -> tuple[str, str]:
        if "_" not in dir_name:
            return dir_name, dir_name
        employee_no, employee_name = dir_name.split("_", 1)
        return employee_no.strip(), employee_name.strip()

    def _scan_gallery(self) -> dict:
        if not self.gallery_dir.exists():
            raise ValueError(f"Gallery directory does not exist: {self.gallery_dir}")

        embeddings = []
        metadata = []
        failed_files = []
        employee_dirs = [item for item in self.gallery_dir.iterdir() if item.is_dir()]

        employee_count = 0
        image_count = 0
        failed_count = 0

        for employee_dir in sorted(employee_dirs):
            employee_no, employee_name = self._parse_employee_dir_name(employee_dir.name)
            image_files = [
                item for item in sorted(employee_dir.iterdir())
                if item.is_file() and item.suffix.lower() in self.IMAGE_SUFFIXES
            ]
            if not image_files:
                continue
            employee_count += 1
            for image_file in image_files:
                image_count += 1
                try:
                    embedding = self.face_engine.extract_embedding_from_path(image_file)
                except Exception as exc:
                    failed_count += 1
                    failed_files.append(
                        {
                            "employeeNo": employee_no,
                            "employeeName": employee_name,
                            "imagePath": str(image_file),
                            "reason": str(exc),
                        }
                    )
                    continue
                embeddings.append(embedding)
                metadata.append(
                    {
                        "employeeNo": employee_no,
                        "employeeName": employee_name,
                        "imagePath": str(image_file),
                    }
                )

        return {
            "employee_count": employee_count,
            "image_count": image_count,
            "passed_count": len(metadata),
            "failed_count": failed_count,
            "failedFiles": failed_files,
            "embeddings": embeddings,
            "metadata": metadata,
        }

    def precheck_gallery(self) -> dict:
        result = self._scan_gallery()
        success = result["passed_count"] > 0
        return {
            "success": success,
            "message": (
                "Gallery precheck passed."
                if success
                else "No valid face embeddings were generated from gallery."
            ),
            "employee_count": result["employee_count"],
            "image_count": result["image_count"],
            "passed_count": result["passed_count"],
            "failed_count": result["failed_count"],
            "failedFiles": result["failedFiles"],
        }

    def rebuild_gallery(self) -> dict:
        result = self._scan_gallery()
        embeddings = result["embeddings"]
        metadata = result["metadata"]

        if not embeddings:
            return {
                "success": False,
                "message": "No valid face embeddings were generated from gallery.",
                "employee_count": result["employee_count"],
                "image_count": result["image_count"],
                "indexed_count": 0,
                "failed_count": result["failed_count"],
                "index_path": str(self.index_service.index_path),
                "metadata_path": str(self.index_service.metadata_path),
                "failedFiles": result["failedFiles"],
            }

        self.index_service.rebuild(embeddings=embeddings, metadata=metadata)
        return {
            "success": True,
            "message": "Gallery rebuilt successfully.",
            "employee_count": result["employee_count"],
            "image_count": result["image_count"],
            "indexed_count": len(metadata),
            "failed_count": result["failed_count"],
            "index_path": str(self.index_service.index_path),
            "metadata_path": str(self.index_service.metadata_path),
            "failedFiles": result["failedFiles"],
        }

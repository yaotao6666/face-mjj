from __future__ import annotations

import json
from pathlib import Path

import numpy as np

try:
    import faiss
except Exception:  # pragma: no cover
    faiss = None


class IndexService:
    def __init__(self, index_dir: str | Path) -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "faiss.index"
        self.metadata_path = self.index_dir / "metadata.json"
        self.embeddings_path = self.index_dir / "embeddings.npy"
        self.dimension: int | None = None
        self.index = None
        self.embedding_matrix: np.ndarray | None = None
        self.metadata: list[dict] = []

    @property
    def ready(self) -> bool:
        return self.index is not None and bool(self.metadata)

    @property
    def face_count(self) -> int:
        return len(self.metadata)

    @property
    def employee_count(self) -> int:
        employee_numbers = {
            item["employeeNo"] for item in self.metadata if item.get("employeeNo")
        }
        return len(employee_numbers)

    def load(self) -> bool:
        if not self.metadata_path.exists():
            self.index = None
            self.embedding_matrix = None
            self.metadata = []
            self.dimension = None
            return False
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if faiss is not None and self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.embedding_matrix = None
            self.dimension = self.index.d
            return True
        if self.embeddings_path.exists():
            self.embedding_matrix = np.load(self.embeddings_path).astype(np.float32)
            self.index = None
            self.dimension = int(self.embedding_matrix.shape[1])
            return True
        self.metadata = []
        self.dimension = None
        return True

    def rebuild(self, embeddings: list[np.ndarray], metadata: list[dict]) -> None:
        if not embeddings:
            raise ValueError("No valid face embeddings were generated from gallery.")
        matrix = np.vstack(embeddings).astype(np.float32)
        matrix = self._normalize(matrix)
        self.dimension = int(matrix.shape[1])
        if faiss is not None:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(matrix)
            faiss.write_index(self.index, str(self.index_path))
            self.embedding_matrix = None
            if self.embeddings_path.exists():
                self.embeddings_path.unlink()
        else:
            self.index = None
            self.embedding_matrix = matrix
            np.save(self.embeddings_path, matrix)
        self.metadata = metadata
        self.metadata_path.write_text(
            json.dumps(self.metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def search(self, embedding: np.ndarray, top_k: int = 1) -> list[dict]:
        if not self.ready:
            raise ValueError("Index is not ready. Please rebuild gallery first.")
        query = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != self.dimension:
            raise ValueError("Embedding dimension does not match current index.")
        query = self._normalize(query)
        if self.index is not None and faiss is not None:
            scores, indexes = self.index.search(query, top_k)
        else:
            scores, indexes = self._search_numpy(query, top_k)
        results: list[dict] = []
        for score, index in zip(scores[0], indexes[0], strict=False):
            if index < 0:
                continue
            item = dict(self.metadata[index])
            item["similarity"] = float(score)
            results.append(item)
        return results

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _search_numpy(self, query: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        if self.embedding_matrix is None:
            raise ValueError("Embedding matrix is not ready. Please rebuild gallery first.")
        scores = np.matmul(query, self.embedding_matrix.T)
        order = np.argsort(-scores, axis=1)[:, :top_k]
        top_scores = np.take_along_axis(scores, order, axis=1)
        return top_scores.astype(np.float32), order.astype(np.int64)

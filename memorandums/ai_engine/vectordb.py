# memorandums/ai_engine/vectordb.py
# Adapted from banker-ai/vectordb.py
# Uses dict-based metadata for safe serialization; backward-compatible with old list format.

import faiss
import numpy as np
import os
import pickle


class VectorStore:
    def __init__(self, dim: int, index_path: str, meta_path: str):
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.index = faiss.IndexFlatL2(dim)
        self._metadata: dict = {}

        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.load()

    def add(self, vectors: list, texts: list):
        np_vectors = np.array(vectors).astype("float32")
        start_idx = self.index.ntotal
        self.index.add(np_vectors)
        for i, text in enumerate(texts):
            self._metadata[start_idx + i] = text
        self.save()

    def search(self, query_vector: list, top_k: int = 8) -> list:
        if self.index.ntotal == 0:
            return []
        query = np.array([query_vector]).astype("float32")
        _, indices = self.index.search(query, min(top_k, self.index.ntotal))
        return [self._metadata[i] for i in indices[0] if i in self._metadata]

    def batch_search(self, query_vectors: list, top_k: int = 8) -> list:
        """Search multiple query vectors at once — used for speed in extract_all()."""
        if self.index.ntotal == 0:
            return [[] for _ in query_vectors]
        queries = np.array(query_vectors).astype("float32")
        k = min(top_k, self.index.ntotal)
        _, indices = self.index.search(queries, k)
        results = []
        for query_indices in indices:
            results.append([self._metadata[i] for i in query_indices if i in self._metadata])
        return results

    def clear(self):
        self.index = faiss.IndexFlatL2(self.dim)
        self._metadata = {}
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self._metadata, f)

    def load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "rb") as f:
            data = pickle.load(f)
            # Handle old list format from memorandums_old
            if isinstance(data, list):
                self._metadata = {i: text for i, text in enumerate(data)}
            else:
                self._metadata = data

    def cleanup(self):
        """Remove temporary vector store files from disk."""
        for path in (self.index_path, self.meta_path):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

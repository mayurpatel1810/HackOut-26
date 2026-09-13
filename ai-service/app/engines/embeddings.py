"""Embedding backends.

Production uses sentence-transformers (all-MiniLM-L6-v2, 384 dimensions, which
is what the pgvector column is sized for). Where that model cannot be installed
- an air-gapped build, a CI box, this repository's own test run - EcoForge falls
back to a deterministic TF-IDF + truncated SVD projection into the SAME 384
dimensions, so the retrieval pipeline, the vector store and every downstream
test behave identically. The active backend is reported in /ai/health and shown
in the Evidence panel, because a degraded embedding model is something the user
is entitled to know about.
"""
from __future__ import annotations

import hashlib
from typing import List, Optional, Protocol, Sequence

import numpy as np

DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    name: str
    dim: int
    degraded: bool

    def fit(self, corpus: Sequence[str]) -> "Embedder": ...
    def encode(self, texts: Sequence[str]) -> np.ndarray: ...


def _l2(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class SentenceTransformerEmbedder:
    name = MODEL_NAME
    dim = DIM
    degraded = False

    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer   # noqa: F401
        self._model = SentenceTransformer(model_name)
        self.name = model_name

    def fit(self, corpus: Sequence[str]):
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vecs = self._model.encode(list(texts), normalize_embeddings=True,
                                  show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


class TfidfSvdEmbedder:
    """Deterministic fallback. Same dimensionality, same cosine semantics."""
    name = "tfidf-svd-384 (fallback)"
    dim = DIM
    degraded = True

    def __init__(self, dim: int = DIM):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.dim = dim
        self._vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                                    sublinear_tf=True, min_df=1,
                                    stop_words="english")
        self._svd: Optional[TruncatedSVD] = None
        self._TruncatedSVD = TruncatedSVD
        self._fitted = False

    def fit(self, corpus: Sequence[str]):
        corpus = list(corpus) or ["empty"]
        X = self._vec.fit_transform(corpus)
        k = max(2, min(self.dim, X.shape[0] - 1, X.shape[1] - 1))
        self._svd = self._TruncatedSVD(n_components=k, random_state=0)
        self._svd.fit(X)
        self._fitted = True
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfSvdEmbedder.fit() must be called with the corpus "
                               "before encoding.")
        X = self._vec.transform(list(texts))
        Z = self._svd.transform(X).astype(np.float32)
        if Z.shape[1] < self.dim:                     # pad so the vector column fits
            Z = np.hstack([Z, np.zeros((Z.shape[0], self.dim - Z.shape[1]),
                                       dtype=np.float32)])
        return _l2(Z)


def build_embedder(prefer_transformer: bool = True) -> Embedder:
    if prefer_transformer:
        try:
            return SentenceTransformerEmbedder()
        except Exception:                              # noqa: BLE001 - optional dep
            pass
    return TfidfSvdEmbedder()


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]

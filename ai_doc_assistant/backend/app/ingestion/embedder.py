import hashlib
import logging
from typing import List, Dict, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

logger = logging.getLogger("cachemind.embedder")

class EmbeddingEngine:
    """
    Local embedding generator using sentence-transformers with an in-memory
    Layer-3 Embedding Cache to avoid redundant vector calculations.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEngine, cls).__new__(cls)
            cls._instance._model = None
            cls._instance._cache: Dict[str, np.ndarray] = {}
            cls._instance._hit_count = 0
            cls._instance._miss_count = 0
        return cls._instance

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading SentenceTransformer: {settings.EMBEDDING_MODEL_NAME}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        return self._model

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string with cache lookup."""
        thash = self._hash_text(text)
        if thash in self._cache:
            self._hit_count += 1
            return self._cache[thash]
            
        self._miss_count += 1
        model = self._get_model()
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        vec = vec.astype("float32")
        
        # Cache management (cap at 50,000 entries)
        if len(self._cache) > 50000:
            # Simple eviction of 5000 oldest keys
            keys_to_del = list(self._cache.keys())[:5000]
            for k in keys_to_del:
                del self._cache[k]
                
        self._cache[thash] = vec
        return vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed a batch of texts leveraging existing cached embeddings where possible."""
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, t in enumerate(texts):
            thash = self._hash_text(t)
            if thash in self._cache:
                self._hit_count += 1
                results[i] = self._cache[thash]
            else:
                self._miss_count += 1
                uncached_indices.append(i)
                uncached_texts.append(t)
                
        if uncached_texts:
            model = self._get_model()
            batch_vecs = model.encode(uncached_texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
            batch_vecs = batch_vecs.astype("float32")
            
            for orig_idx, vec, txt in zip(uncached_indices, batch_vecs, uncached_texts):
                thash = self._hash_text(txt)
                self._cache[thash] = vec
                results[orig_idx] = vec
                
        return np.vstack(results)

    def get_stats(self) -> Dict[str, Union[int, float]]:
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total) * 100.0 if total > 0 else 0.0
        return {
            "cached_vectors_count": len(self._cache),
            "cache_hits": self._hit_count,
            "cache_misses": self._miss_count,
            "cache_hit_rate_pct": round(hit_rate, 2)
        }

embedding_engine = EmbeddingEngine()

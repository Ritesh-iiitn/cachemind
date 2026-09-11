import hashlib
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("cachemind.prefix_cache")

class PrefixCacheEntry:
    def __init__(self, prefix_hash: str, prefix_text: str, token_count: int, model: str):
        self.prefix_hash = prefix_hash
        self.prefix_text = prefix_text
        self.token_count = token_count
        self.model = model
        self.reuse_count = 0
        self.first_seen = time.time()
        self.last_reused = time.time()

    def touch(self) -> None:
        self.reuse_count += 1
        self.last_reused = time.time()

class PrefixPromptCache:
    """
    Tier 5 Prefix Prompt Cache that identifies common prompt prefixes
    (e.g., system instructions, schemas, static reference docs) and tracks
    KV prefill compute savings when reusing identical prompt prefixes.
    """
    def __init__(self, min_prefix_tokens: int = 64):
        self.min_prefix_tokens = min_prefix_tokens
        self._store: Dict[str, PrefixCacheEntry] = {}
        self.total_prefill_tokens_saved = 0
        self.hits = 0
        self.misses = 0

    def compute_prefix_hash(self, prefix_text: str, model: str) -> str:
        payload = f"{model}::{prefix_text.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def register_or_check_prefix(self, prefix_text: str, model: str) -> Dict[str, Any]:
        """
        Check if a prompt prefix was seen before; if so, register a reuse event
        and record token prefill computation savings.
        """
        approx_tokens = max(1, len(prefix_text.split()) * 4 // 3)
        if approx_tokens < self.min_prefix_tokens:
            return {"hit": False, "reason": "prefix_too_short", "tokens": approx_tokens}

        p_hash = self.compute_prefix_hash(prefix_text, model)
        entry = self._store.get(p_hash)
        
        if entry is not None:
            entry.touch()
            self.hits += 1
            self.total_prefill_tokens_saved += approx_tokens
            logger.info(f"[PrefixCache HIT] Prefix {p_hash[:8]} reused {entry.reuse_count} times ({approx_tokens} tokens saved).")
            return {
                "hit": True,
                "prefix_hash": p_hash,
                "reuse_count": entry.reuse_count,
                "tokens_saved": approx_tokens
            }
        else:
            self.misses += 1
            self._store[p_hash] = PrefixCacheEntry(
                prefix_hash=p_hash,
                prefix_text=prefix_text,
                token_count=approx_tokens,
                model=model
            )
            logger.info(f"[PrefixCache NEW] Registered prefix {p_hash[:8]} ({approx_tokens} tokens).")
            return {
                "hit": False,
                "prefix_hash": p_hash,
                "tokens": approx_tokens
            }

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        return {
            "tier": "Prefix Prompt Cache (L5)",
            "tracked_prefixes": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 4),
            "total_prefill_tokens_saved": self.total_prefill_tokens_saved
        }

prefix_cache = PrefixPromptCache()

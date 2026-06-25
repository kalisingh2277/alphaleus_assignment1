"""Text embeddings via fastembed (ONNX, CPU-bound).

We use fastembed rather than sentence-transformers: it is ONNX-backed, has no
torch dependency, and is far lighter on RAM — which matters because everything
must fit inside a free-tier memory envelope. Model: BAAI/bge-small-en-v1.5
(384-dim), loaded lazily as a process-wide singleton so the load cost is paid once.
"""

from __future__ import annotations

import asyncio
import math
import os
from functools import lru_cache

from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
# bge-small handles ~512 tokens; cap input so a huge page cannot blow up memory.
# The leading slice carries the page's gist, which is what we compare on.
MAX_CHARS = 8000

# Persist the ONNX model outside the OS temp dir so it survives reboots/cleanups
# and is downloaded exactly once. Overridable via env for CI/Docker layer caching.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
_CACHE_DIR = os.environ.get("FASTEMBED_CACHE_DIR") or os.path.join(
    os.path.expanduser("~"), ".cache", "fastembed"
)


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=_CACHE_DIR)


def embed(text: str) -> list[float]:
    """Embed a single document into a 384-dim vector (sync, CPU-bound)."""
    snippet = (text or "").strip()[:MAX_CHARS]
    if not snippet:
        return [0.0] * EMBEDDING_DIM
    vector = next(iter(_model().embed([snippet])))  # fastembed yields numpy arrays
    return [float(x) for x in vector]


async def embed_async(text: str) -> list[float]:
    """Async wrapper: runs the blocking embed off the event loop."""
    return await asyncio.to_thread(embed, text)


def cosine_similarity(a, b) -> float:
    """Cosine similarity in [-1, 1]. Returns 0.0 if either vector is empty/zero.

    Accepts lists or numpy arrays (pgvector deserialises stored vectors to numpy),
    so guards use length/``is None`` rather than truthiness — a numpy array has no
    unambiguous bool.
    """
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))

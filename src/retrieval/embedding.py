# src/retrieval/embedding.py
"""
BGE Query Embedding Generator for Phase 2.3.
Applies the mandatory BGE instruction prefix and generates L2-normalized 768-dim query vectors.
"""

import time
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-base-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def format_bge_query(query: str) -> str:
    """
    Applies the exact BGE query instruction prefix.
    MUST be the single authoritative source of prefix handling across codebase.
    """
    return f"{BGE_QUERY_PREFIX}{query}"


class QueryEmbedder:
    """
    Singleton-style manager for sentence-transformers model lifetime.
    Loads BAAI/bge-base-en-v1.5 once and executes single-query embeddings.
    """
    def __init__(self, use_gpu: bool = True):
        self.device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
        print(f"Loading QueryEmbedder model '{MODEL_NAME}' on device '{self.device}'...")
        start_t = time.time()
        self.model = SentenceTransformer(MODEL_NAME, device=self.device)
        print(f"QueryEmbedder model loaded in {time.time() - start_t:.2f}s.")

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embeds a single query string with BGE instruction prefix.
        Returns L2-normalized 768-dim numpy float32 array.
        """
        prefixed_text = format_bge_query(query)
        
        if self.device == "cuda":
            with torch.amp.autocast("cuda"):
                vec = self.model.encode(
                    prefixed_text,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True
                )
        else:
            vec = self.model.encode(
                prefixed_text,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            
        vec = vec.astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

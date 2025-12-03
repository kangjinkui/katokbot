import logging
from typing import List, Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Thin wrapper around SentenceTransformer for encoding text to vectors.
    """

    def __init__(self, model_name: str = "jhgan/ko-sbert-sts", cache_dir: Optional[str] = None):
        self.model_name = model_name
        self.cache_dir = cache_dir

        logger.info(f"[Embedding] Loading model: {model_name}")
        self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
        logger.info("[Embedding] Model loaded")

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of texts into embeddings."""
        if not texts:
            return []
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def encode_single(self, text: str) -> List[float]:
        """Encode a single text into an embedding."""
        return self.encode([text])[0]

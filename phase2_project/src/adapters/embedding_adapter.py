import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingAdapter:
    def __init__(self, config: dict):
        """
        初始化 Embedding 轉接器。

        config 範例:
        {
            "embedding": {
                "provider": "sentence_transformers",
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "normalize_embeddings": true,
                "batch_size": 32
            }
        }
        """
        self.emb_config = config.get("embedding", {})
        self.provider = self.emb_config.get("provider", "sentence_transformers")
        self.model_name = self.emb_config.get(
            "model_name",
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.normalize = self.emb_config.get("normalize_embeddings", True)
        self.batch_size = self.emb_config.get("batch_size", 32)

        # 延遲載入
        self.model = None

    def encode(self, texts: list) -> tuple:
        """
        將文本列表編碼為向量。

        前置條件：
            texts 為 feature_texts（已完成清洗與語意建構）

        Returns:
            (embeddings, embedding_summary)
        """

        if not isinstance(texts, list):
            raise ValueError("texts 必須為 list")

        # 空輸入處理
        if len(texts) == 0:
            return np.empty((0, 0)), {
                "provider": self.provider,
                "model_name": self.model_name,
                "embedding_dimension": 0,
                "normalized": self.normalize
            }

        # lazy load（只初始化一次）
        if self.model is None:
            if self.provider == "sentence_transformers":
                self.model = SentenceTransformer(self.model_name)
            else:
                raise ValueError(f"未支援的 provider: {self.provider}")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=False
        )

        # invariant
        if embeddings.shape[0] != len(texts):
            raise RuntimeError("Invariant violated: embedding size mismatch")

        summary = {
            "provider": self.provider,
            "model_name": self.model_name,
            "embedding_dimension": embeddings.shape[1],
            "normalized": self.normalize
        }

        return embeddings, summary

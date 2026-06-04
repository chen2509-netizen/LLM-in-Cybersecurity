import numpy as np
from sklearn.cluster import DBSCAN

class ClusteringAdapter:
    def __init__(self, config: dict):
        self.clu_config = config.get("clustering", {})

        self.algorithm = self.clu_config.get("algorithm", "DBSCAN")
        self.metric = self.clu_config.get("metric", "cosine")
        self.eps = self.clu_config.get("eps", 0.25)
        self.min_samples = self.clu_config.get("min_samples", 3)

        self.model = None

    def fit_predict(self, embeddings: np.ndarray) -> np.ndarray:
        """
        前置條件：
            embeddings shape = (n_samples, embedding_dim)
        """

        if not isinstance(embeddings, np.ndarray):
            raise ValueError("embeddings 必須為 numpy.ndarray")

        # 空出入處理
        if embeddings.shape[0] == 0:
            return np.array([], dtype=int)

        if self.model is None:
            if self.algorithm == "DBSCAN":
                self.model = DBSCAN(
                    metric=self.metric,
                    eps=self.eps,
                    min_samples=self.min_samples
                )
            else:
                raise ValueError(f"未支援的分群演算法: {self.algorithm}")

        labels = self.model.fit_predict(embeddings)

        # Invariant Check
        if len(labels) != embeddings.shape[0]:
            raise RuntimeError("Invariant violated: clustering result size mismatch")

        return labels
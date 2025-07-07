from enum import Enum


class VectorDistance(Enum):
    r"""Distance metrics used in a vector database."""

    DOT = "dot"
    r"""Dot product. https://en.wikipedia.org/wiki/Dot_product"""

    COSINE = "cosine"
    r"""Cosine similarity. https://en.wikipedia.org/wiki/Cosine_similarity"""

    EUCLIDEAN = "euclidean"
    r"""Euclidean distance. https://en.wikipedia.org/wiki/Euclidean_distance"""


class EmbeddingModelType(Enum):
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"

    @property
    def is_openai(self) -> bool:
        r"""Returns whether this type of models is an OpenAI-released model."""
        return self in {
            EmbeddingModelType.TEXT_EMBEDDING_3_SMALL,
        }

    @property
    def output_dim(self) -> int:
        if self is EmbeddingModelType.TEXT_EMBEDDING_3_SMALL:
            return 1536
        else:
            raise ValueError(f"Unknown model type {self}.")


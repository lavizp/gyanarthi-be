from app.schemas.enum import VectorDistance
from app.schemas.uploaded_article import UploadedArticle
from loguru import logger
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

if TYPE_CHECKING:
    from qdrant_client import QdrantClient


from app.storages.vectordb_storage_base import (
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
)
# from src.schemas.document import Document
# USE MY SCHEMA INSTEAD OF DUCUMENT

_qdrant_local_client_map: Dict[str, Tuple[Any, int]] = {}


class QdrantStorage:
    r"""An implementation of the Qdrant, a vector search engine."""

    def __init__(
        self,
        vector_dim: int =1536,
        collection_name: Optional[str] = None,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        path: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        delete_collection_on_del: bool = False,
        **kwargs: Any,
    ) -> None:
        from qdrant_client import QdrantClient

        self._client: QdrantClient
        self._local_path: Optional[str] = None
        self._create_client(url_and_api_key, path, **kwargs)

        self.vector_dim = vector_dim
        self.distance = distance
        self.collection_name = collection_name or self._generate_collection_name()

        self._check_and_create_collection()

        self.delete_collection_on_del = delete_collection_on_del

    def __del__(self):
        r"""Deletes the collection if :obj:`del_collection` is set to
        :obj:`True`.
        """
        # If the client is a local client, decrease count by 1
        if self._local_path is not None:
            # if count decrease to 0, remove it from the map
            _client, _count = _qdrant_local_client_map.pop(self._local_path)
            if _count > 1:
                _qdrant_local_client_map[self._local_path] = (
                    _client,
                    _count - 1,
                )

        if hasattr(self, "delete_collection_on_del") and self.delete_collection_on_del:
            try:
                self._delete_collection(self.collection_name)
            except RuntimeError as e:
                logger.error(
                    f"Failed to delete collection '{self.collection_name}': {e}"
                )

    def _create_client(
        self,
        url_and_api_key: Optional[Tuple[str, str]],
        path: Optional[str],
        **kwargs: Any,
    ) -> None:
        from qdrant_client import QdrantClient

        if url_and_api_key is not None:
            self._client = QdrantClient(
                url=url_and_api_key[0],
                api_key=url_and_api_key[1],
                **kwargs,
            )
        elif path is not None:
            # Avoid creating a local client multiple times,
            # which is prohibited by Qdrant
            self._local_path = path
            if path in _qdrant_local_client_map:
                # Store client instance in the map and maintain counts
                self._client, count = _qdrant_local_client_map[path]
                _qdrant_local_client_map[path] = (self._client, count + 1)
            else:
                self._client = QdrantClient(path=path, **kwargs)
                _qdrant_local_client_map[path] = (self._client, 1)
        else:
            self._client = QdrantClient(":memory:", **kwargs)

    def _check_and_create_collection(self) -> None:
        if self._collection_exists(self.collection_name):
            in_dim = self._get_collection_info(self.collection_name)["vector_dim"]
            if in_dim != self.vector_dim:
                # The name of collection has to be confirmed by the user
                raise ValueError(
                    "Vector dimension of the existing collection "
                    f'"{self.collection_name}" ({in_dim}) is different from '
                    f"the given embedding dim ({self.vector_dim})."
                )
        else:
            self._create_collection(
                collection_name=self.collection_name,
                size=self.vector_dim,
                distance=self.distance,
            )

    def _create_collection(
        self,
        collection_name: str,
        size: int,
        distance: VectorDistance = VectorDistance.COSINE,
        **kwargs: Any,
    ) -> None:
        r"""Creates a new collection in the database.

        Args:
            collection_name (str): Name of the collection to be created.
            size (int): Dimensionality of vectors to be stored in this
                collection.
            distance (VectorDistance, optional): The distance metric to be used
                for vector similarity. (default: :obj:`VectorDistance.COSINE`)
            **kwargs (Any): Additional keyword arguments.
        """
        from qdrant_client.http.models import Distance, VectorParams

        distance_map = {
            VectorDistance.DOT: Distance.DOT,
            VectorDistance.COSINE: Distance.COSINE,
            VectorDistance.EUCLIDEAN: Distance.EUCLID,
        }
        # Since `recreate_collection` method will be removed in the future
        # by Qdrant, `create_collection` is recommended instead.
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=size,
                distance=distance_map[distance],
            ),
            **kwargs,
        )

    def _delete_collection(
        self,
        collection_name: str,
        **kwargs: Any,
    ) -> None:
        r"""Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
            **kwargs (Any): Additional keyword arguments.
        """
        self._client.delete_collection(collection_name=collection_name, **kwargs)

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Returns whether the collection exists in the database"""
        for c in self._client.get_collections().collections:
            if collection_name == c.name:
                return True
        return False

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name if user doesn't provide"""
        return datetime.now().isoformat()

    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        r"""Retrieves details of an existing collection.

        Args:
            collection_name (str): Name of the collection to be checked.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                collection.
        """
        from qdrant_client.http.models import VectorParams

        # TODO: check more information
        collection_info = self._client.get_collection(collection_name=collection_name)
        vector_config = collection_info.config.params.vectors
        return {
            "vector_dim": vector_config.size
            if isinstance(vector_config, VectorParams)
            else None,
            "vector_count": collection_info.points_count,
            "status": collection_info.status,
            "vectors_count": collection_info.vectors_count,
            "config": collection_info.config,
        }

    def close_client(self, **kwargs):
        r"""Closes the client connection to the Qdrant storage."""
        self._client.close(**kwargs)

    def add(self, records: List[UploadedArticle], **kwargs) -> None:
        """Adds a list of vectors to the specified collection.

        Args:
            records (List[Document]): List of vectors to be added.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """
        import uuid
        from qdrant_client.http.models import PointStruct, UpdateStatus

        qdrant_points = []

        for p in records:
            # Ensure p.id is a valid point ID (either an integer or UUID)
            if isinstance(p.id, str):
                try:
                    # Attempt to convert the string to an integer, if possible
                    point_id = int(p.id)
                except ValueError:
                    # If conversion to int fails, use a UUID instead
                    point_id = str(uuid.uuid4())
            else:
                point_id = p.id

            # Construct the PointStruct with a valid ID
            qdrant_points.append(
                PointStruct(id=point_id, vector=p.embedding, payload=p.metadata)
            )

        # Perform the upsert operation
        op_info = self._client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points,
            wait=True,
            **kwargs,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                f"Failed to add vectors in Qdrant, operation info: {op_info}."
            )

    def delete_collection(self) -> None:
        r"""Deletes the entire collection in the Qdrant storage."""
        self._delete_collection(self.collection_name)

    def delete(
        self,
        ids: Optional[List[str]] = None,
        payload_filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        r"""Deletes points from the collection based on either IDs or payload
        filters.

        Raises:
            ValueError: If neither `ids` nor `payload_filter` is provided.
            RuntimeError: If there is an error during the deletion process.
        """
        from qdrant_client.http.models import (
            Condition,
            FieldCondition,
            Filter,
            MatchValue,
            PointIdsList,
            UpdateStatus,
        )

        if not ids and not payload_filter:
            raise ValueError(
                "You must provide either `ids` or `payload_filter` to delete points."
            )

        if ids:
            op_info = self._client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=cast(List[Union[int, str]], ids)),
                **kwargs,
            )
            if op_info.status != UpdateStatus.COMPLETED:
                raise RuntimeError(
                    f"Failed to delete vectors in Qdrant, operation info: {op_info}"
                )

        if payload_filter:
            filter_conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in payload_filter.items()
            ]

            op_info = self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=cast(List[Condition], filter_conditions)),
                **kwargs,
            )

            if op_info.status != UpdateStatus.COMPLETED:
                raise RuntimeError(
                    f"Failed to delete vectors in Qdrant, operation info: {op_info}"
                )

    def status(self) -> VectorDBStatus:
        status = self._get_collection_info(self.collection_name)
        return VectorDBStatus(
            vector_dim=status["vector_dim"],
            vector_count=status["vector_count"],
        )

    def query(
        self,
        query: VectorDBQuery,
        filter_conditions: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided query."""
        from qdrant_client.http.models import (
            Condition,
            FieldCondition,
            Filter,
            MatchValue,
        )

        # Construct filter if filter_conditions is provided
        search_filter = None
        if filter_conditions:
            must_conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_conditions.items()
            ]
            search_filter = Filter(must=cast(List[Condition], must_conditions))

        # Execute the search with optional filter
        search_result = self._client.query_points(
            collection_name=self.collection_name,
            query=query.query_vector,
            with_payload=True,
            with_vectors=True,
            limit=query.top_k,
            query_filter=search_filter,
            **kwargs,
        )

        query_results = [
            VectorDBQueryResult.create(
                similarity=point.score,
                id=str(point.id),
                payload=point.payload,
                vector=point.vector,
            )
            for point in search_result.points
        ]

        return query_results

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        self._delete_collection(self.collection_name)
        self._create_collection(
            collection_name=self.collection_name,
            size=self.vector_dim,
            distance=self.distance,
        )

    @property
    def client(self) -> "QdrantClient":
        r"""Provides access to the underlying vector database client."""
        return self._client

    def close_connection(self):
        self.client.close(grpc_grace=5.0)

"""Meilisearch index manager for PyBase."""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from meilisearch import Client as MeilisearchClient
    from meilisearch.errors import MeilisearchApiError

    MEILISEARCH_AVAILABLE = True
except ImportError:
    MEILISEARCH_AVAILABLE = False
    MeilisearchClient = None
    MeilisearchApiError = Exception


class MeilisearchIndexManager:
    """Manager for Meilisearch index configuration and lifecycle."""

    def __init__(self, meilisearch_url: str = "http://localhost:7700", api_key: Optional[str] = None):
        """
        Initialize the Meilisearch index manager.

        Args:
            meilisearch_url: URL of the Meilisearch instance
            api_key: Optional API key for Meilisearch
        """
        self.client = None
        if MEILISEARCH_AVAILABLE:
            self.client = MeilisearchClient(meilisearch_url, api_key)

    def create_base_index(
        self,
        base_id: str,
        primary_key: str = "id",
    ) -> bool:
        """
        Create a Meilisearch index for a base.

        Args:
            base_id: Base ID
            primary_key: Primary key for documents (default: "id")

        Returns:
            True if index was created or already exists, False on failure
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            # Check if index exists
            self.client.get_index(index_name)
            # Index exists, update settings
            return self._configure_base_index(base_id)
        except MeilisearchApiError as e:
            # Index doesn't exist, create it
            if "index_not_found" in str(e) or e.code == "index_not_found":
                try:
                    self.client.create_index(index_name, {"primaryKey": primary_key})
                    return self._configure_base_index(base_id)
                except MeilisearchApiError:
                    return False
            return False

    def _configure_base_index(self, base_id: str) -> bool:
        """
        Configure index settings for faceted search.

        Args:
            base_id: Base ID

        Returns:
            True if configuration succeeded, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)

            # Configure searchable attributes
            index.update_searchable_attributes([
                "id",
                "table_id",
                "base_id",
                "table_name",
                "values",
            ])

            # Configure filterable attributes for faceted search
            index.update_filterable_attributes([
                "table_id",
                "base_id",
                "table_name",
            ])

            # Configure sortable attributes
            index.update_sortable_attributes([
                "table_name",
                "created_at",
            ])

            # Configure displayed attributes
            index.update_displayed_attributes([
                "id",
                "table_id",
                "base_id",
                "table_name",
                "values",
                "created_at",
                "updated_at",
            ])

            # Configure ranking rules for relevance
            index.update_ranking_rules([
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
            ])

            # Configure typo tolerance for fuzzy search
            index.update_typo_tolerance({
                "enabled": True,
                "minWordSizeForTypos": {
                    "oneTypo": 4,
                    "twoTypos": 8,
                },
                "disableOnWords": [],
                "disableOnAttributes": [],
            })

            # Configure faceted search
            index.update_faceting({
                "maxValuesPerFacet": 100,
                "sortFacetValuesBy": {
                    "*": "alpha",
                },
            })

            # Configure pagination
            index.update_pagination({
                "maxTotalHits": 100000,
            })

            return True

        except MeilisearchApiError:
            return False

    def delete_base_index(self, base_id: str) -> bool:
        """
        Delete a Meilisearch index for a base.

        Args:
            base_id: Base ID

        Returns:
            True if index was deleted, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            self.client.delete_index(index_name)
            return True
        except MeilisearchApiError:
            return False

    def index_record(
        self,
        base_id: str,
        record_id: str,
        table_id: str,
        table_name: str,
        values: Dict[str, Any],
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> bool:
        """
        Index a single record in Meilisearch.

        Args:
            base_id: Base ID
            record_id: Record ID
            table_id: Table ID
            table_name: Table name
            values: Field values as dictionary
            created_at: Creation timestamp
            updated_at: Last update timestamp

        Returns:
            True if indexing succeeded, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        # Prepare document for indexing
        document = {
            "id": record_id,
            "table_id": table_id,
            "base_id": base_id,
            "table_name": table_name,
            "values": self._prepare_values_for_indexing(values),
            "created_at": created_at,
            "updated_at": updated_at,
        }

        try:
            index = self.client.index(index_name)
            index.add_documents([document])
            return True
        except MeilisearchApiError:
            return False

    def index_records_batch(
        self,
        base_id: str,
        records: List[Dict[str, Any]],
        batch_size: int = 1000,
    ) -> bool:
        """
        Index multiple records in batch.

        Args:
            base_id: Base ID
            records: List of record dictionaries
            batch_size: Number of records per batch

        Returns:
            True if all batches were indexed successfully, False otherwise
        """
        if not self.client or not records:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)

            # Process in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                # Prepare documents
                documents = []
                for record in batch:
                    document = {
                        "id": record["id"],
                        "table_id": record["table_id"],
                        "base_id": base_id,
                        "table_name": record.get("table_name", ""),
                        "values": self._prepare_values_for_indexing(
                            record.get("values", {})
                        ),
                        "created_at": record.get("created_at"),
                        "updated_at": record.get("updated_at"),
                    }
                    documents.append(document)

                index.add_documents(documents)

            return True

        except MeilisearchApiError:
            return False

    def delete_record(self, base_id: str, record_id: str) -> bool:
        """
        Delete a record from the index.

        Args:
            base_id: Base ID
            record_id: Record ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)
            index.delete_document(record_id)
            return True
        except MeilisearchApiError:
            return False

    def delete_all_records_in_table(self, base_id: str, table_id: str) -> bool:
        """
        Delete all records for a specific table from the index.

        Args:
            base_id: Base ID
            table_id: Table ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)

            # Delete all documents with the given table_id
            index.delete_documents({"filter": f"table_id = {table_id}"})
            return True
        except MeilisearchApiError:
            return False

    def get_index_stats(self, base_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for an index.

        Args:
            base_id: Base ID

        Returns:
            Dictionary with index stats or None on failure
        """
        if not self.client:
            return None

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)
            stats = index.get_stats()
            return {
                "number_of_documents": stats.get("number_of_documents", 0),
                "is_indexing": stats.get("is_indexing", False),
                "field_distribution": stats.get("field_distribution", {}),
            }
        except MeilisearchApiError:
            return None

    def update_index_settings(
        self,
        base_id: str,
        settings: Dict[str, Any],
    ) -> bool:
        """
        Update custom index settings.

        Args:
            base_id: Base ID
            settings: Settings dictionary to update

        Returns:
            True if update succeeded, False otherwise
        """
        if not self.client:
            return False

        index_name = self._get_base_index_name(base_id)

        try:
            index = self.client.index(index_name)
            index.update_settings(settings)
            return True
        except MeilisearchApiError:
            return False

    def _get_base_index_name(self, base_id: str) -> str:
        """
        Get the Meilisearch index name for a base.

        Args:
            base_id: Base ID

        Returns:
            Index name string
        """
        return f"pybase:base:{base_id}"

    def _prepare_values_for_indexing(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare field values for indexing in Meilisearch.

        Converts complex values to searchable strings and handles special types.

        Args:
            values: Field values dictionary

        Returns:
            Prepared values dictionary
        """
        prepared = {}

        for field_id, value in values.items():
            if value is None:
                prepared[field_id] = None
            elif isinstance(value, (str, int, float, bool)):
                # Basic types are directly indexable
                prepared[field_id] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings for search
                if value and all(isinstance(v, (str, int, float)) for v in value):
                    prepared[field_id] = ", ".join(str(v) for v in value)
                else:
                    prepared[field_id] = json.dumps(value)
            elif isinstance(value, dict):
                # Convert dicts to JSON strings
                prepared[field_id] = json.dumps(value)
            else:
                # Convert other types to string
                prepared[field_id] = str(value)

        return prepared

    def check_health(self) -> bool:
        """
        Check if Meilisearch is accessible and healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.health()
            return True
        except MeilisearchApiError:
            return False

    def get_version(self) -> Optional[str]:
        """
        Get Meilisearch version.

        Returns:
            Version string or None if unavailable
        """
        if not self.client:
            return None

        try:
            version_info = self.client.get_version()
            return version_info.get("pkgVersion")
        except MeilisearchApiError:
            return None


def get_index_manager(
    meilisearch_url: str = "http://localhost:7700",
    api_key: Optional[str] = None,
) -> MeilisearchIndexManager:
    """
    Get Meilisearch index manager instance.

    Args:
        meilisearch_url: URL of the Meilisearch instance
        api_key: Optional API key for Meilisearch

    Returns:
        MeilisearchIndexManager instance
    """
    return MeilisearchIndexManager(meilisearch_url, api_key)

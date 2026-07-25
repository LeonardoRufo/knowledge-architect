from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

from .exceptions import NotionConfigurationError, NotionIntegrationError


class NotionClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        data_source_id: str | None = None,
    ) -> None:
        load_dotenv()

        self.token = token or os.getenv("NOTION_ACCESS_TOKEN")
        self.data_source_id = (
            data_source_id or os.getenv("NOTION_DATA_SOURCE_ID")
        )

        if not self.token:
            raise NotionConfigurationError(
                "NOTION_ACCESS_TOKEN não definido."
            )

        if not self.data_source_id:
            raise NotionConfigurationError(
                "NOTION_DATA_SOURCE_ID não definido."
            )

        self._client = Client(auth=self.token)

    def query_by_kir_id(self, kir_id: str) -> list[dict[str, Any]]:
        try:
            response = self._client.data_sources.query(
                data_source_id=self.data_source_id,
                filter={
                    "property": "KIR ID",
                    "rich_text": {
                        "equals": kir_id,
                    },
                },
            )
        except APIResponseError as error:
            raise NotionIntegrationError(
                f"Falha ao consultar KIR ID {kir_id}: {error.message}"
            ) from error

        return response.get("results", [])

    def create_page(
        self,
        *,
        properties: dict[str, Any],
        children: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parent": {
                "type": "data_source_id",
                "data_source_id": self.data_source_id,
            },
            "properties": properties,
        }

        if children:
            payload["children"] = children

        try:
            return self._client.pages.create(**payload)
        except APIResponseError as error:
            raise NotionIntegrationError(
                f"Falha ao criar página: {error.message}"
            ) from error

    def update_page(
        self,
        *,
        page_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return self._client.pages.update(
                page_id=page_id,
                properties=properties,
            )
        except APIResponseError as error:
            raise NotionIntegrationError(
                f"Falha ao atualizar página {page_id}: {error.message}"
            ) from error

    def archive_page(self, page_id: str) -> dict[str, Any]:
        try:
            return self._client.pages.update(
                page_id=page_id,
                archived=True,
            )
        except APIResponseError as error:
            raise NotionIntegrationError(
                f"Falha ao arquivar página {page_id}: {error.message}"
            ) from error

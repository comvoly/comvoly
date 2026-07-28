"""Provider-neutral contracts; external providers are intentionally not selected here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol


@dataclass(frozen=True)
class NormalisedContent:
    external_item_id: str
    external_conversation_id: str
    external_space_id: str
    item_type: str
    source_created_at: str
    body_text: str | None
    author_external_id: str | None = None
    reply_to_external_id: str | None = None
    source_url: str | None = None
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ConnectorPage:
    items: tuple[NormalisedContent, ...]
    next_cursor: Mapping[str, object] | None


class CommunityConnector(Protocol):
    provider: str

    def discover_communities(self) -> Iterable[Mapping[str, object]]: ...
    def verify_permissions(self, external_community_id: str) -> Mapping[str, bool]: ...
    def import_page(self, external_community_id: str, scope: Mapping[str, object],
                    cursor: Mapping[str, object] | None) -> ConnectorPage: ...
    def connection_health(self) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class RetrievalScope:
    account_id: str
    workspace_id: str
    permitted_source_space_ids: frozenset[str] | None = None


class IntelligenceRetriever(Protocol):
    def retrieve(self, scope: RetrievalScope, query: str, limit: int) -> Iterable[Mapping[str, object]]: ...


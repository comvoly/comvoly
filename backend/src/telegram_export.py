"""Versioned, dependency-free parser for Telegram Desktop JSON exports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
from typing import Any, Iterable, Mapping

from service_contracts import NormalisedContent


PARSER_VERSION = "telegram-desktop-json-v1"
MEDIA_KEYS = ("photo", "file", "thumbnail", "sticker_file", "contact_vcard")


class TelegramExportError(ValueError):
    """The supplied document is not a supported Telegram Desktop chat export."""


@dataclass(frozen=True)
class TelegramExportPreview:
    parser_version: str
    external_community_id: str
    community_name: str
    export_type: str
    message_count: int
    service_event_count: int
    participant_count: int
    media_count: int
    history_start: str | None
    history_end: str | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["warnings"] = list(self.warnings)
        return value


def _community_id(document: Mapping[str, Any]) -> str:
    supplied = str(document.get("id", "")).strip()
    if supplied:
        return supplied
    name = str(document.get("name", "")).strip()
    if not name:
        raise TelegramExportError("The export does not contain a chat name or stable chat ID.")
    # Older Telegram exports can omit the chat ID. Mark the deterministic fallback so
    # it can never be confused with a provider-issued identifier.
    return "export-fingerprint:" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]


def _messages(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise TelegramExportError("Choose the result.json file from one Telegram chat export.")
    if len(messages) > 2_000_000:
        raise TelegramExportError("This export is too large for the current pilot limit.")
    return [item for item in messages if isinstance(item, Mapping)]


def extract_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, Mapping):
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""


def _iso_date(item: Mapping[str, Any]) -> str:
    value = str(item.get("date", "")).strip()
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat()
        except ValueError:
            pass
    unix = str(item.get("date_unixtime", "")).strip()
    try:
        return datetime.fromtimestamp(int(unix), UTC).isoformat()
    except (ValueError, TypeError, OSError):
        raise TelegramExportError(f"Message {item.get('id', '?')} has no valid date.")


def preview_export(document: Mapping[str, Any]) -> TelegramExportPreview:
    if not isinstance(document, Mapping):
        raise TelegramExportError("The selected file is not a JSON object.")
    messages = _messages(document)
    name = str(document.get("name", "")).strip() or "Telegram community"
    ordinary = [item for item in messages if str(item.get("type", "message")) == "message"]
    dates: list[str] = []
    warnings: list[str] = []
    for item in ordinary:
        try:
            dates.append(_iso_date(item))
        except TelegramExportError:
            warnings.append(f"Message {item.get('id', '?')} has an invalid date and will be skipped.")
    participants = {str(item.get("from_id") or item.get("from") or "").strip()
                    for item in ordinary if item.get("from_id") or item.get("from")}
    media_count = sum(1 for item in ordinary if any(item.get(key) for key in MEDIA_KEYS))
    if not ordinary:
        warnings.append("No ordinary messages were found in this export.")
    if str(document.get("type", "")).lower() not in {"private_group", "supergroup", "public_supergroup", "channel"}:
        warnings.append("Confirm that this export is the intended owner-authorised community chat.")
    return TelegramExportPreview(
        PARSER_VERSION, _community_id(document), name, str(document.get("type", "unknown")),
        len(ordinary), len(messages) - len(ordinary), len(participants), media_count,
        min(dates) if dates else None, max(dates) if dates else None, tuple(warnings[:100]))


def normalise_messages(messages: Iterable[Mapping[str, Any]], external_community_id: str) -> tuple[NormalisedContent, ...]:
    output: list[NormalisedContent] = []
    for item in messages:
        if str(item.get("type", "message")) != "message":
            continue
        external_id = str(item.get("id", "")).strip()
        if not external_id:
            continue
        try:
            created_at = _iso_date(item)
        except TelegramExportError:
            continue
        media = [{"kind": key, "path": str(item[key])} for key in MEDIA_KEYS if item.get(key)]
        metadata = {
            "parser_version": PARSER_VERSION,
            "edited": item.get("edited"),
            "forwarded_from": item.get("forwarded_from"),
            "media": media,
        }
        output.append(NormalisedContent(
            external_item_id=external_id,
            external_conversation_id=external_community_id,
            external_space_id="main",
            item_type="message",
            source_created_at=created_at,
            body_text=extract_text(item.get("text")) or None,
            author_external_id=str(item.get("from_id") or "") or None,
            reply_to_external_id=str(item.get("reply_to_message_id") or "") or None,
            metadata=metadata,
        ))
    return tuple(output)


def checksum_item(item: NormalisedContent) -> str:
    payload = json.dumps(asdict(item), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

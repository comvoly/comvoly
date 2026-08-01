"""Secure workspace routing for Comvoly's single Telegram Bot API webhook."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import re
import secrets
from typing import Any, Mapping

from authorization import WorkspaceContext
from database import query
from v2_store import new_id, utc_now


class TelegramLiveError(ValueError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def derive_webhook_secret(master_key: str) -> str:
    """Derive Telegram's one global secret-token value without storing it."""
    if len(master_key) < 32:
        raise TelegramLiveError(503, "Telegram live connection is not configured yet.")
    return hmac.new(master_key.encode(), b"telegram:global-webhook:v1", hashlib.sha256).hexdigest()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _telegram_date(value: object) -> str:
    try:
        return datetime.fromtimestamp(int(value), UTC).isoformat()
    except (TypeError, ValueError, OSError) as error:
        raise TelegramLiveError(400, "Telegram supplied an invalid message date.") from error


def _message_body(message: Mapping[str, Any]) -> str | None:
    value = message.get("text") or message.get("caption")
    return str(value).strip() if value is not None and str(value).strip() else None


def _chat(body: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = body.get("chat")
    return value if isinstance(value, Mapping) else None


def _activation_code(message: Mapping[str, Any], bot_username: str) -> str | None:
    text = str(message.get("text") or "").strip()
    match = re.fullmatch(r"/start(?:@([A-Za-z0-9_]+))?\s+([A-Za-z0-9_-]{20,80})", text)
    if not match or (match.group(1) and match.group(1).lower() != bot_username.lower()):
        return None
    return match.group(2)


class TelegramLiveService:
    def __init__(self, connection: Any, master_key: str, bot_user_id: str,
                 bot_username: str, public_api_url: str):
        self.connection = connection
        self.master_key = master_key
        self.bot_user_id = str(bot_user_id).strip()
        self.bot_username = str(bot_username).strip().lstrip("@")
        self.public_api_url = public_api_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return (len(self.master_key) >= 32 and bool(self.bot_user_id)
                and bool(self.bot_username) and self.public_api_url.startswith("https://"))

    def prepare(self, context: WorkspaceContext, source_id: str) -> dict[str, Any]:
        context.require("manage_sources")
        if not self.configured:
            raise TelegramLiveError(503, "The official Comvoly Telegram bot has not been configured yet.")
        source = self.connection.execute(query("""SELECT id FROM source_connections
            WHERE id=? AND workspace_id=? AND provider='telegram'"""),
            (source_id, context.workspace_id)).fetchone()
        if source is None:
            raise TelegramLiveError(404, "Telegram source not found.")
        code = secrets.token_urlsafe(24)
        webhook_secret = derive_webhook_secret(self.master_key)
        now = utc_now()
        self.connection.execute(query("""INSERT INTO telegram_connection_configs
            (source_connection_id, workspace_id, bot_user_id, bot_username,
             expected_chat_id, webhook_secret_digest, activation_code_digest,
             activation_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'awaiting_bot', ?, ?)
            ON CONFLICT(source_connection_id) DO UPDATE SET
            bot_user_id=excluded.bot_user_id, bot_username=excluded.bot_username,
            expected_chat_id=excluded.expected_chat_id,
            webhook_secret_digest=excluded.webhook_secret_digest,
            activation_code_digest=excluded.activation_code_digest,
            activation_state='awaiting_bot', membership_status='unknown', receives_messages=0,
            verified_at=NULL, updated_at=excluded.updated_at"""),
            (source_id, context.workspace_id, self.bot_user_id, self.bot_username,
             f"pending:{source_id}", _digest(webhook_secret), _digest(code), now, now))
        self.connection.execute(query("""UPDATE source_connections SET state='connecting',
            health='unknown', updated_at=? WHERE id=? AND workspace_id=?"""),
            (now, source_id, context.workspace_id))
        self._audit(context.workspace_id, context.account_id, "telegram.live_prepared",
                    source_id, {"bot_username": self.bot_username})
        return {
            "source_id": source_id, "state": "awaiting_bot", "bot_username": self.bot_username,
            "install_url": f"https://t.me/{self.bot_username}?startgroup={code}",
            "webhook_url": f"{self.public_api_url}/v2/telegram/webhooks",
        }

    def status(self, context: WorkspaceContext, source_id: str) -> dict[str, Any]:
        context.require("manage_sources")
        source = self.connection.execute(query("""SELECT id FROM source_connections
            WHERE id=? AND workspace_id=? AND provider='telegram'"""),
            (source_id, context.workspace_id)).fetchone()
        if source is None:
            raise TelegramLiveError(404, "Telegram source not found.")
        row = self.connection.execute(query("""SELECT c.activation_state, c.membership_status,
            c.receives_messages, c.last_received_at, c.verified_at, c.bot_username,
            c.expected_chat_id, s.health FROM telegram_connection_configs c
            JOIN source_connections s ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.source_connection_id=? AND c.workspace_id=?"""),
            (source_id, context.workspace_id)).fetchone()
        if row is None:
            return {"source_id": source_id, "state": "not_prepared", "configured": self.configured}
        result = dict(row)
        result.update(source_id=source_id, configured=self.configured,
                      receives_messages=bool(result["receives_messages"]))
        result["connection_prepared_at"] = result.get("updated_at")
        try:
            result["connection_expired"] = (
                result.get("activation_state") == "awaiting_bot" and
                datetime.now(UTC) - datetime.fromisoformat(str(result["updated_at"])) > timedelta(minutes=10))
        except (KeyError, TypeError, ValueError):
            result["connection_expired"] = False
        if str(result["expected_chat_id"]).startswith("pending:"):
            result["expected_chat_id"] = None
        return result

    def receive(self, supplied_secret: str,
                update: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        expected = derive_webhook_secret(self.master_key)
        if not supplied_secret or not hmac.compare_digest(expected, supplied_secret):
            raise TelegramLiveError(401, "Telegram webhook verification failed.")
        try:
            update_id = int(update["update_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise TelegramLiveError(400, "Telegram update ID is required.") from error
        event_type, body = self._event(update)
        config = self._resolve_config(event_type, body)
        if config is None:
            return 200, {"ok": True, "state": "ignored"}
        source_id, workspace_id = str(config["source_connection_id"]), str(config["workspace_id"])
        if str(config["activation_state"]) == "revoked" or str(config["source_state"]) == "revoked":
            return 200, {"ok": True, "state": "ignored"}
        if not hmac.compare_digest(str(config["webhook_secret_digest"]), _digest(expected)):
            raise TelegramLiveError(401, "Telegram webhook verification failed.")
        existing = self.connection.execute(query("""SELECT state FROM telegram_webhook_events
            WHERE source_connection_id=? AND update_id=?"""), (source_id, update_id)).fetchone()
        if existing is not None:
            return 200, {"ok": True, "duplicate": True, "state": str(existing["state"])}
        now = utc_now()
        self.connection.execute(query("""INSERT INTO telegram_webhook_events
            (source_connection_id, workspace_id, update_id, event_type, state, received_at)
            VALUES (?, ?, ?, ?, 'received', ?)"""),
            (source_id, workspace_id, update_id, event_type, now))
        if event_type == "activation":
            return self._bind(source_id, workspace_id, update_id, body, config)
        if event_type == "membership":
            return self._membership(source_id, workspace_id, update_id, body, config)
        if event_type == "message":
            return self._message(source_id, workspace_id, update_id, body, config)
        self._finish(source_id, update_id, "ignored", None)
        return 200, {"ok": True, "duplicate": False, "state": "ignored"}

    def _event(self, update: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
        for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
            value = update.get(key)
            if isinstance(value, Mapping):
                return ("activation" if _activation_code(value, self.bot_username) else "message"), value
        value = update.get("my_chat_member")
        if isinstance(value, Mapping):
            return "membership", value
        return "unsupported", {}

    def _resolve_config(self, event_type: str, body: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if event_type == "activation":
            code = _activation_code(body, self.bot_username)
            row = self.connection.execute(query("""SELECT c.*, s.state AS source_state
                FROM telegram_connection_configs c JOIN source_connections s
                  ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
                WHERE c.activation_code_digest=? AND c.activation_state='awaiting_bot'"""),
                (_digest(code or ""),)).fetchone()
            return row
        chat = _chat(body)
        if chat is None or chat.get("id") is None:
            return None
        return self.connection.execute(query("""SELECT c.*, s.state AS source_state
            FROM telegram_connection_configs c JOIN source_connections s
              ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.expected_chat_id=?"""), (str(chat["id"]),)).fetchone()

    def _bind(self, source_id: str, workspace_id: str, update_id: int,
              message: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        chat = _chat(message)
        if chat is None or str(chat.get("type", "")) not in {"group", "supergroup"}:
            self._finish(source_id, update_id, "ignored", "not_a_group")
            return 200, {"ok": True, "state": "ignored"}
        chat_id = str(chat.get("id", ""))
        stale = self.connection.execute(query("""SELECT c.source_connection_id
            FROM telegram_connection_configs c
            JOIN source_connections s
              ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.expected_chat_id=? AND c.source_connection_id<>?
              AND (c.activation_state='revoked' OR s.state='revoked')"""),
            (chat_id, source_id)).fetchall()
        for released in stale:
            released_id = str(released["source_connection_id"])
            self.connection.execute(query("""UPDATE telegram_connection_configs
                SET expected_chat_id=?, updated_at=? WHERE source_connection_id=?"""),
                (f"revoked:{released_id}", utc_now(), released_id))
        occupied = self.connection.execute(query("""SELECT c.source_connection_id
            FROM telegram_connection_configs c
            JOIN source_connections s
              ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.expected_chat_id=? AND c.source_connection_id<>?
              AND c.activation_state<>'revoked' AND s.state<>'revoked'"""),
            (chat_id, source_id)).fetchone()
        if occupied is not None:
            self._finish(source_id, update_id, "failed", "chat_already_bound")
            return 409, {"detail": "That Telegram group is already connected."}
        now = utc_now()
        self.connection.execute(query("""UPDATE telegram_connection_configs SET
            expected_chat_id=?, activation_code_digest=NULL, activation_state='verifying',
            membership_status='member', last_update_id=?, last_received_at=?, updated_at=?
            WHERE source_connection_id=? AND workspace_id=?"""),
            (chat_id, update_id, now, now, source_id, workspace_id))
        self._finish(source_id, update_id, "processed", None)
        self._audit(workspace_id, None, "telegram.group_bound", source_id, {"chat_type": chat.get("type")})
        return 200, {"ok": True, "state": "verifying"}

    def _matching_chat(self, body: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
        chat = _chat(body)
        return chat is not None and str(chat.get("id", "")) == str(config["expected_chat_id"])

    def _membership(self, source_id: str, workspace_id: str, update_id: int,
                    body: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self._matching_chat(body, config):
            self._finish(source_id, update_id, "ignored", "chat_mismatch")
            return 200, {"ok": True, "state": "ignored"}
        member = body.get("new_chat_member")
        status = str(member.get("status", "unknown")) if isinstance(member, Mapping) else "unknown"
        active = status in {"member", "administrator"}
        now = utc_now()
        self.connection.execute(query("""UPDATE telegram_connection_configs SET
            activation_state=?, membership_status=?, last_update_id=?, last_received_at=?,
            updated_at=? WHERE source_connection_id=? AND workspace_id=?"""),
            ("verifying" if active else "awaiting_bot", status, update_id, now, now,
             source_id, workspace_id))
        self._finish(source_id, update_id, "processed", None)
        return 200, {"ok": True, "state": "verifying" if active else "awaiting_bot"}

    def _message(self, source_id: str, workspace_id: str, update_id: int,
                 message: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self._matching_chat(message, config):
            self._finish(source_id, update_id, "ignored", "chat_mismatch")
            return 200, {"ok": True, "state": "ignored"}
        try:
            message_id = str(int(message["message_id"]))
            source_created_at = _telegram_date(message.get("date"))
        except (KeyError, TypeError, ValueError, TelegramLiveError) as error:
            self._finish(source_id, update_id, "failed", "invalid_message")
            raise TelegramLiveError(400, "Telegram supplied an invalid message.") from error
        space_id, conversation_id = self._ensure_scope(
            workspace_id, source_id, str(config["expected_chat_id"]), message)
        author = message.get("from")
        author_id = str(author.get("id")) if isinstance(author, Mapping) and author.get("id") is not None else None
        author_name = None
        if isinstance(author, Mapping):
            author_name = " ".join(str(author.get(key, "")).strip() for key in ("first_name", "last_name")).strip() or str(author.get("username") or "") or None
        metadata = {"telegram_update_id": update_id, "has_media": any(
            key in message for key in ("photo", "document", "video", "audio", "voice", "animation", "sticker"))}
        now = utc_now()
        self.connection.execute(query("""INSERT INTO content_items
            (id, workspace_id, source_connection_id, source_space_id, conversation_id,
             external_item_id, item_type, author_external_id, author_display_name, body_text,
             source_created_at, source_edited_at, ingestion_method, ingested_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, 'message', ?, ?, ?, ?, ?, 'telegram_bot_webhook', ?, ?)
            ON CONFLICT(source_connection_id, external_item_id) DO UPDATE SET
            author_external_id=excluded.author_external_id,
            author_display_name=excluded.author_display_name, body_text=excluded.body_text,
            source_edited_at=excluded.source_edited_at, ingested_at=excluded.ingested_at,
            metadata_json=excluded.metadata_json"""),
            (new_id("item"), workspace_id, source_id, space_id, conversation_id, message_id,
             author_id, author_name, _message_body(message), source_created_at,
             now if message.get("edit_date") else None, now,
             json.dumps(metadata, separators=(",", ":"))))
        self.connection.execute(query("""UPDATE telegram_connection_configs SET
            activation_state='connected', receives_messages=1, last_update_id=?,
            last_received_at=?, verified_at=COALESCE(verified_at, ?), updated_at=?
            WHERE source_connection_id=? AND workspace_id=?"""),
            (update_id, now, now, now, source_id, workspace_id))
        self.connection.execute(query("""UPDATE source_connections SET state='connected', health='healthy',
            cutover_at=COALESCE(cutover_at, ?), cursor_json=?, updated_at=?
            WHERE id=? AND workspace_id=?"""),
            (now, json.dumps({"last_update_id": update_id}), now, source_id, workspace_id))
        if str(config["activation_state"]) != "connected":
            self._audit(workspace_id, None, "telegram.live_connected", source_id,
                        {"first_update_id": update_id})
        self._finish(source_id, update_id, "processed", None, message_id)
        return 200, {"ok": True, "duplicate": False, "state": "connected"}

    def _ensure_scope(self, workspace_id: str, source_id: str, chat_id: str,
                      message: Mapping[str, Any]) -> tuple[str, str]:
        chat = _chat(message) or {}
        title = str(chat.get("title") or "Telegram group")[:120]
        row = self.connection.execute(query("SELECT id FROM source_spaces WHERE source_connection_id=? AND external_space_id='main'"), (source_id,)).fetchone()
        space_id = str(row["id"]) if row else new_id("space")
        now = utc_now()
        if row is None:
            self.connection.execute(query("""INSERT INTO source_spaces
                (id, workspace_id, source_connection_id, external_space_id, name, space_type, created_at, updated_at)
                VALUES (?, ?, ?, 'main', ?, 'chat', ?, ?)"""),
                (space_id, workspace_id, source_id, title, now, now))
        row = self.connection.execute(query("SELECT id FROM conversations WHERE source_connection_id=? AND external_conversation_id=?"), (source_id, chat_id)).fetchone()
        conversation_id = str(row["id"]) if row else new_id("conversation")
        if row is None:
            self.connection.execute(query("""INSERT INTO conversations
                (id, workspace_id, source_connection_id, source_space_id,
                 external_conversation_id, conversation_type, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'chat', ?, ?, ?)"""),
                (conversation_id, workspace_id, source_id, space_id, chat_id, title, now, now))
        return space_id, conversation_id

    def _finish(self, source_id: str, update_id: int, state: str,
                error_code: str | None, message_id: str | None = None) -> None:
        self.connection.execute(query("""UPDATE telegram_webhook_events SET state=?, error_code=?,
            external_message_id=?, processed_at=? WHERE source_connection_id=? AND update_id=?"""),
            (state, error_code, message_id, utc_now(), source_id, update_id))

    def _audit(self, workspace_id: str, actor_id: str | None, action: str,
               source_id: str, metadata: Mapping[str, Any]) -> None:
        self.connection.execute(query("""INSERT INTO audit_events
            (id, workspace_id, actor_account_id, action, target_type, target_id,
             outcome, metadata_json, occurred_at)
            VALUES (?, ?, ?, ?, 'source_connection', ?, 'success', ?, ?)"""),
            (new_id("audit"), workspace_id, actor_id, action, source_id,
             json.dumps(dict(metadata), separators=(",", ":")), utc_now()))

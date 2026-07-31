"""Workspace-bound Telegram Bot API webhook ingestion.

The bot token remains in the deployment secret store. A per-source webhook secret is
derived from a separate master key and is never persisted in plaintext.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Any, Mapping

from authorization import WorkspaceContext
from database import query
from v2_store import new_id, utc_now


class TelegramLiveError(ValueError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def derive_webhook_secret(master_key: str, source_id: str) -> str:
    if len(master_key) < 32:
        raise TelegramLiveError(503, "Telegram live connection is not configured yet.")
    return hmac.new(master_key.encode(), f"telegram:{source_id}".encode(), hashlib.sha256).hexdigest()


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

    def prepare(self, context: WorkspaceContext, source_id: str,
                expected_chat_id: str) -> dict[str, Any]:
        context.require("manage_sources")
        if not self.configured:
            raise TelegramLiveError(503, "The official Comvoly Telegram bot has not been configured yet.")
        source = self.connection.execute(query("""SELECT id FROM source_connections
            WHERE id=? AND workspace_id=? AND provider='telegram'"""),
            (source_id, context.workspace_id)).fetchone()
        if source is None:
            raise TelegramLiveError(404, "Telegram source not found.")
        chat_id = str(expected_chat_id).strip()
        if not chat_id or len(chat_id) > 64:
            raise TelegramLiveError(400, "Enter the Telegram group ID from the connection instructions.")
        secret = derive_webhook_secret(self.master_key, source_id)
        now = utc_now()
        self.connection.execute(query("""INSERT INTO telegram_connection_configs
            (source_connection_id, workspace_id, bot_user_id, bot_username,
             expected_chat_id, webhook_secret_digest, activation_state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'awaiting_bot', ?, ?)
            ON CONFLICT(source_connection_id) DO UPDATE SET
            bot_user_id=excluded.bot_user_id, bot_username=excluded.bot_username,
            expected_chat_id=excluded.expected_chat_id,
            webhook_secret_digest=excluded.webhook_secret_digest,
            activation_state='awaiting_bot', membership_status='unknown', receives_messages=0,
            verified_at=NULL, updated_at=excluded.updated_at"""),
            (source_id, context.workspace_id, self.bot_user_id, self.bot_username,
             chat_id, _digest(secret), now, now))
        self.connection.execute(query("""UPDATE source_connections SET state='connecting',
            health='unknown', updated_at=? WHERE id=? AND workspace_id=?"""),
            (now, source_id, context.workspace_id))
        self._audit(context.workspace_id, context.account_id, "telegram.live_prepared",
                    source_id, {"bot_username": self.bot_username})
        return {
            "source_id": source_id,
            "state": "awaiting_bot",
            "bot_username": self.bot_username,
            "install_url": f"https://t.me/{self.bot_username}?startgroup=comvoly",
            "webhook_url": f"{self.public_api_url}/v2/telegram/webhooks/{source_id}",
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
        result["source_id"] = source_id
        result["configured"] = self.configured
        result["receives_messages"] = bool(result["receives_messages"])
        return result

    def receive(self, source_id: str, supplied_secret: str,
                update: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        config = self.connection.execute(query("""SELECT c.source_connection_id, c.workspace_id,
            c.expected_chat_id, c.webhook_secret_digest, c.activation_state, s.state AS source_state
            FROM telegram_connection_configs c JOIN source_connections s
              ON s.id=c.source_connection_id AND s.workspace_id=c.workspace_id
            WHERE c.source_connection_id=?"""),
            (source_id,)).fetchone()
        if config is None:
            raise TelegramLiveError(404, "Not found.")
        if str(config["activation_state"]) == "revoked" or str(config["source_state"]) == "revoked":
            raise TelegramLiveError(404, "Not found.")
        expected = derive_webhook_secret(self.master_key, source_id)
        if (not supplied_secret or not hmac.compare_digest(expected, supplied_secret)
                or not hmac.compare_digest(str(config["webhook_secret_digest"]), _digest(expected))):
            raise TelegramLiveError(401, "Telegram webhook verification failed.")
        try:
            update_id = int(update["update_id"])
        except (KeyError, TypeError, ValueError) as error:
            raise TelegramLiveError(400, "Telegram update ID is required.") from error
        workspace_id = str(config["workspace_id"])
        existing = self.connection.execute(query("""SELECT state FROM telegram_webhook_events
            WHERE source_connection_id=? AND update_id=?"""), (source_id, update_id)).fetchone()
        if existing is not None:
            return 200, {"ok": True, "duplicate": True, "state": str(existing["state"])}

        event_type, body = self._event(update)
        now = utc_now()
        self.connection.execute(query("""INSERT INTO telegram_webhook_events
            (source_connection_id, workspace_id, update_id, event_type, state, received_at)
            VALUES (?, ?, ?, ?, 'received', ?)"""),
            (source_id, workspace_id, update_id, event_type, now))
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
                return "message", value
        value = update.get("my_chat_member")
        if isinstance(value, Mapping):
            return "membership", value
        return "unsupported", {}

    def _matching_chat(self, body: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
        chat = body.get("chat")
        return isinstance(chat, Mapping) and str(chat.get("id", "")) == str(config["expected_chat_id"])

    def _membership(self, source_id: str, workspace_id: str, update_id: int,
                    body: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self._matching_chat(body, config):
            self._finish(source_id, update_id, "ignored", "chat_mismatch")
            return 200, {"ok": True, "state": "ignored"}
        member = body.get("new_chat_member")
        status = str(member.get("status", "unknown")) if isinstance(member, Mapping) else "unknown"
        connected = status in {"member", "administrator"}
        now = utc_now()
        self.connection.execute(query("""UPDATE telegram_connection_configs SET
            activation_state=?, membership_status=?, last_update_id=?, last_received_at=?,
            updated_at=? WHERE source_connection_id=? AND workspace_id=?"""),
            ("verifying" if connected else "awaiting_bot", status, update_id, now, now,
             source_id, workspace_id))
        self._finish(source_id, update_id, "processed", None)
        return 200, {"ok": True, "state": "verifying" if connected else "awaiting_bot"}

    def _message(self, source_id: str, workspace_id: str, update_id: int,
                 message: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self._matching_chat(message, config):
            self._finish(source_id, update_id, "ignored", "chat_mismatch")
            return 200, {"ok": True, "state": "ignored"}
        try:
            message_id = str(int(message["message_id"]))
        except (KeyError, TypeError, ValueError) as error:
            self._finish(source_id, update_id, "failed", "invalid_message_id")
            raise TelegramLiveError(400, "Telegram message ID is required.") from error
        space_id, conversation_id = self._ensure_scope(workspace_id, source_id,
                                                        str(config["expected_chat_id"]), message)
        author = message.get("from")
        author_id = str(author.get("id")) if isinstance(author, Mapping) and author.get("id") is not None else None
        author_name = None
        if isinstance(author, Mapping):
            author_name = " ".join(str(author.get(key, "")).strip() for key in ("first_name", "last_name")).strip() or str(author.get("username") or "") or None
        metadata = {"telegram_update_id": update_id, "has_media": any(
            key in message for key in ("photo", "document", "video", "audio", "voice", "animation", "sticker"))}
        now = utc_now()
        try:
            source_created_at = _telegram_date(message.get("date"))
        except TelegramLiveError:
            self._finish(source_id, update_id, "failed", "invalid_message_date")
            raise
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
            activation_state='connected', membership_status=CASE WHEN membership_status='unknown'
                THEN 'member' ELSE membership_status END, receives_messages=1,
            last_update_id=?, last_received_at=?, verified_at=COALESCE(verified_at, ?), updated_at=?
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
        chat = message.get("chat") if isinstance(message.get("chat"), Mapping) else {}
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

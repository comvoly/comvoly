"""Register or inspect the official Telegram webhook without exposing its token."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

from telegram_live import derive_webhook_secret


def telegram_call(token: str, method: str, payload: dict[str, object] | None = None) -> object:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Telegram rejected {method} with HTTP {error.code}.") from error
    if not result.get("ok"):
        raise RuntimeError(f"Telegram rejected {method}: {result.get('description', 'unknown error')}")
    return result.get("result")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("register", "verify"))
    args = parser.parse_args()
    token = os.getenv("COMVOLY_TELEGRAM_BOT_TOKEN", "").strip()
    master = os.getenv("COMVOLY_TELEGRAM_WEBHOOK_MASTER_KEY", "")
    public_url = os.getenv("COMVOLY_PUBLIC_API_URL", "").rstrip("/")
    if not token or not public_url.startswith("https://"):
        raise SystemExit("Configure the Telegram bot token and HTTPS public API URL in the isolated environment.")
    bot_result = telegram_call(token, "getMe")
    if not isinstance(bot_result, dict):
        raise RuntimeError("Telegram returned an invalid bot identity.")
    bot = bot_result
    if args.action == "register":
        telegram_call(token, "setWebhook", {
            "url": f"{public_url}/v2/telegram/webhooks",
            "secret_token": derive_webhook_secret(master),
            "allowed_updates": ["message", "edited_message", "channel_post",
                                "edited_channel_post", "my_chat_member"],
        })
    info_result = telegram_call(token, "getWebhookInfo")
    if not isinstance(info_result, dict):
        raise RuntimeError("Telegram returned invalid webhook information.")
    info = info_result
    # Never print the token, secret, pending payloads, or Telegram error bodies.
    print(json.dumps({"bot_id": bot.get("id"), "bot_username": bot.get("username"),
                      "webhook_url": info.get("url"),
                      "pending_update_count": info.get("pending_update_count", 0)}, indent=2))


if __name__ == "__main__":
    main()

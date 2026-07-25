"""
N VION Protocol — Telegram Reporter
Real-time ESCALATE and HALT alerts to the Owner.
Per VION.md Section 6.3 — all HALT/ESCALATE events reported via Telegram.
"""

import os
from datetime import datetime, timezone

import requests


class TelegramReporter:
    """
    Sends ESCALATE and HALT alerts to the Owner's Telegram chat.
    Fails silently if Telegram is not configured — system continues,
    but logs a warning. Owner should always configure this.
    """

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._enabled = bool(self.bot_token and self.chat_id)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _send(self, message: str) -> bool:
        """Send a message to the Owner's Telegram chat."""
        if not self._enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # ─── ALERT METHODS ────────────────────────────────────────────────────────

    def send_escalate(self, condition: int, reason: str, agent_id: str = None):
        """ESCALATE alert — system continues, agent suspended."""
        agent_info = f"\n<b>Agent:</b> {agent_id}" if agent_id else ""
        message = (
            f"⚠️ <b>N-VION ESCALATE — Condition {condition}</b>\n"
            f"<b>Time:</b> {self._timestamp()}"
            f"{agent_info}\n"
            f"<b>Reason:</b> {reason}\n\n"
            f"System continues. Affected agent suspended.\n"
            f"Review activity log and decide next action."
        )
        return self._send(message)

    def send_halt(self, condition: int, reason: str):
        """HALT alert — full system shutdown."""
        message = (
            f"🚨 <b>N-VION HALT — Condition {condition}</b>\n"
            f"<b>Time:</b> {self._timestamp()}\n"
            f"<b>Reason:</b> {reason}\n\n"
            f"<b>ALL AGENTS SUSPENDED.</b>\n"
            f"<b>ALL PENDING COMMANDS PURGED.</b>\n\n"
            f"System is halted. Manual Owner restart required.\n"
            f"Review the activity log before restarting."
        )
        return self._send(message)

    def send_condition_6(self, reason: str):
        """Condition 6 — constitutional integrity violation. Critical."""
        message = (
            f"🔴 <b>N-VION CRITICAL — CONDITION 6</b>\n"
            f"<b>CONSTITUTIONAL INTEGRITY VIOLATION</b>\n"
            f"<b>Time:</b> {self._timestamp()}\n"
            f"<b>Details:</b> {reason}\n\n"
            f"<b>FULL SYSTEM HALT.</b>\n"
            f"An attempt was made to modify or override a constitutional document.\n"
            f"This is a Condition 6 event. Immediate Owner review mandatory."
        )
        return self._send(message)

    def send_system_start(self, deployment_name: str, session_id: str):
        """Notify Owner when the orchestrator starts up."""
        message = (
            f"✅ <b>N VION Protocol Online</b>\n"
            f"<b>Deployment:</b> {deployment_name}\n"
            f"<b>Session:</b> {session_id}\n"
            f"<b>Time:</b> {self._timestamp()}\n\n"
            f"Orchestrator active. Awaiting OWNER_COMMANDs."
        )
        return self._send(message)

    def send_system_halt_notice(self, reason: str):
        """Final Telegram message before the system halts."""
        message = (
            f"🛑 <b>N-VION System Halted</b>\n"
            f"<b>Time:</b> {self._timestamp()}\n"
            f"<b>Reason:</b> {reason}\n\n"
            f"All agents suspended. All commands purged.\n"
            f"Restart requires OWNER_COMMAND with valid AUTH token."
        )
        return self._send(message)

    def send_info(self, title: str, message: str):
        """General info message — for non-alert notifications."""
        formatted = (
            f"ℹ️ <b>N-VION: {title}</b>\n"
            f"<b>Time:</b> {self._timestamp()}\n\n"
            f"{message}"
        )
        return self._send(formatted)

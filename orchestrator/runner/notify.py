"""Notification layer — ntfy.sh integration."""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

from .config import NotificationsConfig

log = logging.getLogger(__name__)


@dataclass
class NotifyEvent:
    event: str
    task_id: str = ""
    agent: str = ""
    status: str = ""
    message: str = ""


ICONS = {
    "task_started": "\U0001f680",
    "task_completed": "\u2705",
    "task_failed": "\u274c",
    "limit_hit": "\u23f3",
    "task_resumed": "\U0001f504",
    "task_blocked": "\U0001f6a7",
    "merge_completed": "\U0001f500",
    "queue_empty": "\U0001f3c1",
    "review_required": "\U0001f440",
}


def send_notification(config: NotificationsConfig, event: NotifyEvent) -> None:
    if not config.ntfy_enabled:
        return
    if event.event not in config.events:
        return

    url = config.ntfy_url or config.ntfy_topic
    if not url:
        return

    icon = ICONS.get(event.event, "\U0001f916")
    title = f"{icon} Agent Runner"
    body = event.message
    if not body:
        parts = [event.event.replace("_", " ").title()]
        if event.task_id:
            parts.append(f"task={event.task_id}")
        if event.agent:
            parts.append(f"agent={event.agent}")
        if event.status:
            parts.append(f"status={event.status}")
        body = " | ".join(parts)

    try:
        subprocess.run(
            ["curl", "-s",
             "-H", f"Title: {title}",
             "-H", f"Tags: agent-runner,{event.event}",
             "-d", body,
             url],
            capture_output=True, timeout=10,
        )
    except Exception as e:
        log.warning("ntfy send failed: %s", e)

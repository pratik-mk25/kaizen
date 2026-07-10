import os
import requests
import json

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def _get_webhook_url():
    if DISCORD_WEBHOOK_URL:
        return DISCORD_WEBHOOK_URL
    try:
        from database import supabase
        rows = supabase.table("organizations").select("discord_webhook_url").limit(1).execute().data
        if rows and rows[0].get("discord_webhook_url"):
            return rows[0]["discord_webhook_url"]
    except Exception:
        pass
    return None

def send_discord_notification(content: str, title: str = "Club Update", color: int = 0x00f0ff):
    url = _get_webhook_url()
    if not url:
        return
    payload = {
        "embeds": [{"title": title, "description": content, "color": color, "footer": {"text": "DRONE CLUB OS"}}]
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Discord notification failed: {e}")

def notify_task_created(task: dict, user_name: str):
    content = f"**New Task Created**\n**Title:** {task['title']}\n**Project ID:** {task['project_id']}\n**Created By:** {user_name}"
    send_discord_notification(content, title="NEW TASK", color=0x00f0ff)

def notify_task_status_changed(task: dict, old_status: str, new_status: str, user_name: str):
    content = f"**Status Updated**\n**Task:** {task['title']}\n**Path:** {old_status.upper()} -> {new_status.upper()}\n**Updated By:** {user_name}"
    color = 0x10b981 if new_status == "done" else 0x3b82f6
    send_discord_notification(content, title="STATUS CHANGE", color=color)

def notify_project_created(project: dict, user_name: str):
    content = f"**New Project Created**\n**Name:** {project['name']}\n**Mission ID:** {project['mission_id']}\n**Created By:** {user_name}"
    send_discord_notification(content, title="NEW PROJECT", color=0xf59e0b)

def notify_task_updated(task: dict, user_name: str, changes: list):
    change_text = "\n".join(changes)
    priority = task.get("priority", "medium").upper()
    due_date = task.get("due_date", "No Deadline")
    content = f"**Task Updated**\n**Task:** {task['title']}\n**Priority:** {priority}\n**Deadline:** {due_date}\n\n**Changes:**\n{change_text}\n\n**Updated By:** {user_name}"
    color = 0xef4444 if priority == "HIGH" else 0x3b82f6
    send_discord_notification(content, title="TASK UPDATED", color=color)
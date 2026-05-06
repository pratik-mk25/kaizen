import os
import requests
import json

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_notification(content: str, title: str = "Mission Update", color: int = 0x00f0ff):
    if not DISCORD_WEBHOOK_URL:
        return
    
    payload = {
        "embeds": [
            {
                "title": title,
                "description": content,
                "color": color,
                "footer": {"text": "Mission Tracker // Deploy Excellence"}
            }
        ]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"Discord notification failed: {e}")

def notify_task_created(task: dict, user_name: str):
    content = f"**New Task Created**\n**Title:** {task['title']}\n**Project ID:** {task['project_id']}\n**Created By:** {user_name}"
    send_discord_notification(content, title="🚨 NEW TASK", color=0x00f0ff)

def notify_task_status_changed(task: dict, old_status: str, new_status: str, user_name: str):
    content = f"**Status Updated**\n**Task:** {task['title']}\n**Path:** {old_status.upper()} ➔ {new_status.upper()}\n**Updated By:** {user_name}"
    color = 0x10b981 if new_status == "done" else 0x3b82f6
    send_discord_notification(content, title="🔄 STATUS CHANGE", color=color)

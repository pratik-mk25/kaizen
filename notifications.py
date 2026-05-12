import os
import requests
import json
import crud

DISCORD_WEBHOOK_URL_FALLBACK = os.environ.get("DISCORD_WEBHOOK_URL")

def get_webhook_url(org_id: str | None):
    if not org_id:
        return DISCORD_WEBHOOK_URL_FALLBACK
    try:
        org = crud.get_organization(org_id)
        return org.get("discord_webhook_url") or DISCORD_WEBHOOK_URL_FALLBACK
    except:
        return DISCORD_WEBHOOK_URL_FALLBACK

def send_discord_notification(content: str, org_id: str | None = None, title: str = "Mission Update", color: int = 0x00f0ff):
    webhook_url = get_webhook_url(org_id)
    if not webhook_url:
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
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Discord notification failed: {e}")

def notify_task_created(task: dict, user_name: str, org_id: str | None = None):
    content = f"**New Task Created**\n**Title:** {task['title']}\n**Project ID:** {task['project_id']}\n**Created By:** {user_name}"
    send_discord_notification(content, org_id=org_id, title="🚨 NEW TASK", color=0x00f0ff)

def notify_task_status_changed(task: dict, old_status: str, new_status: str, user_name: str, org_id: str | None = None):
    content = f"**Status Updated**\n**Task:** {task['title']}\n**Path:** {old_status.upper()} ➔ {new_status.upper()}\n**Updated By:** {user_name}"
    color = 0x10b981 if new_status == "done" else 0x3b82f6
    send_discord_notification(content, org_id=org_id, title="🔄 STATUS CHANGE", color=color)

def notify_project_created(project: dict, user_name: str, org_id: str | None = None):
    content = f"**New Project Created**\n**Name:** {project['name']}\n**Mission ID:** {project['mission_id']}\n**Created By:** {user_name}"
    send_discord_notification(content, org_id=org_id, title="🏗️ NEW PROJECT", color=0xf59e0b)

import requests
from dotenv import load_dotenv
import os

load_dotenv()
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")


def send_job_to_discord(job):
    embed = {
        "title": job["job_title"],
        "url": job["link"],
        "color": 3066993,
        "fields": [
            {"name": "Công ty", "value": job["company"], "inline": False},
            {"name": "Lương", "value": job["salary"], "inline": True},
            {"name": "Địa điểm", "value": job["city"], "inline": True},
            {"name": "Kinh nghiệm", "value": job["exp"], "inline": True},
        ],
        "footer": {"text": f"Job ID: {job['job_id']}"}
    }

    data = {
        "content": "🔔 **Có job Data Engineer mới!**",
        "embeds": [embed]
    }

    response = requests.post(webhook_url, json=data)
    return response.status_code == 204
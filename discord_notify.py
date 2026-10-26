import os
import requests
from dotenv import load_dotenv

# Read DISCORD_WEBHOOK_URL from the .env file (on GitHub Actions it comes from a Secret instead)
load_dotenv()
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")


def send_job_to_discord(job):
    """Send one job to Discord. Returns True only if Discord accepted the message."""
    embed = {
        "title": job["job_title"],
        "url": job["link"],
        "color": 3066993,
        "fields": [
            {"name": "Company", "value": job["company"], "inline": False},
            {"name": "Salary", "value": job["salary"], "inline": True},
            {"name": "Location", "value": job["city"], "inline": True},
            {"name": "Experience", "value": job["exp"], "inline": True},
        ],
        "footer": {"text": f"Job ID: {job['job_id']}"},
    }
    data = {"content": "New Data Engineer job on TopCV", "embeds": [embed]}

    try:
        response = requests.post(webhook_url, json=data, timeout=10)
        return response.status_code == 204  # Discord answers 204 when the message is accepted
    except requests.RequestException:
        return False  # no internet, bad webhook, timeout... the job stays "owed" and is retried
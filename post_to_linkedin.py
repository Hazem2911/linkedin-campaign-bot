#!/usr/bin/env python3
"""
LinkedIn Campaign Bot
Posts a scheduled campaign (image + caption) to a personal LinkedIn profile
using the OFFICIAL LinkedIn API (no scraping, ToS-safe).

Usage:
  python post_to_linkedin.py --due          # post whatever is due today (used by GitHub Actions)
  python post_to_linkedin.py --post 3       # force-post a specific post id
  python post_to_linkedin.py --due --dry-run  # show what would happen, post nothing

Required environment variables:
  LINKEDIN_ACCESS_TOKEN   OAuth token with the w_member_social scope (see get_token.py)
  LINKEDIN_PERSON_URN     e.g. urn:li:person:AbC123xYz (printed by get_token.py)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).parent
SCHEDULE_FILE = ROOT / "schedule.json"
STATE_DIR = ROOT / "state"
API = "https://api.linkedin.com/v2"
TIMEZONE = ZoneInfo("Africa/Cairo")


def load_schedule() -> list[dict]:
    return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))["posts"]


def already_posted(post_id: int) -> bool:
    return (STATE_DIR / f"post-{post_id}.posted").exists()


def mark_posted(post_id: int, post_urn: str) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(TIMEZONE).isoformat()
    (STATE_DIR / f"post-{post_id}.posted").write_text(f"{stamp}\n{post_urn}\n", encoding="utf-8")


def find_due_post(posts: list[dict]) -> dict | None:
    """A post is due if its date is today (Cairo time) and it was not posted yet."""
    today = datetime.now(TIMEZONE).date().isoformat()
    for post in posts:
        if post["date"] == today and not already_posted(post["id"]):
            return post
    return None


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def upload_image(token: str, person_urn: str, image_path: Path) -> str:
    """Register + upload an image, return the asset URN."""
    register_body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    r = requests.post(
        f"{API}/assets?action=registerUpload",
        headers=headers(token),
        json=register_body,
        timeout=30,
    )
    r.raise_for_status()
    value = r.json()["value"]
    asset_urn = value["asset"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]

    with open(image_path, "rb") as f:
        up = requests.put(
            upload_url,
            data=f,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
            timeout=120,
        )
    up.raise_for_status()
    return asset_urn


def create_post(token: str, person_urn: str, caption: str, asset_urn: str, alt_text: str) -> str:
    """Publish the post, return the post URN."""
    body = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": caption},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
                        "description": {"text": alt_text[:200]},
                        "title": {"text": alt_text[:100]},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = requests.post(f"{API}/ugcPosts", headers=headers(token), json=body, timeout=30)
    if r.status_code >= 400:
        print("LinkedIn API error:", r.status_code, r.text, file=sys.stderr)
    r.raise_for_status()
    return r.headers.get("x-restli-id", r.json().get("id", "unknown"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Post a scheduled campaign post to LinkedIn.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--due", action="store_true", help="post whatever is due today")
    group.add_argument("--post", type=int, metavar="ID", help="force-post a specific post id")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, post nothing")
    args = parser.parse_args()

    posts = load_schedule()

    if args.due:
        post = find_due_post(posts)
        if post is None:
            print(f"Nothing due today ({datetime.now(TIMEZONE).date().isoformat()} Cairo). Bye.")
            return 0
    else:
        matches = [p for p in posts if p["id"] == args.post]
        if not matches:
            print(f"No post with id {args.post} in schedule.json", file=sys.stderr)
            return 1
        post = matches[0]
        if already_posted(post["id"]) and not args.dry_run:
            print(f"Post {post['id']} was already posted (see state/). Refusing to double-post.")
            return 0

    caption = (ROOT / post["caption_file"]).read_text(encoding="utf-8").strip()
    image_path = ROOT / post["image"]
    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 1

    print(f"── Post {post['id']}: {post['title']}")
    print(f"   date: {post['date']}  image: {post['image']}")
    print(f"   caption preview: {caption[:90]!r}...")

    if args.dry_run:
        print("DRY RUN — nothing was posted.")
        return 0

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.environ.get("LINKEDIN_PERSON_URN")
    if not token or not person_urn:
        print("Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN env vars.", file=sys.stderr)
        return 1

    print("Uploading image…")
    asset_urn = upload_image(token, person_urn, image_path)
    print(f"Image uploaded: {asset_urn}")

    print("Publishing post…")
    post_urn = create_post(token, person_urn, caption, asset_urn, post.get("alt", post["title"]))
    print(f"✅ Published: {post_urn}")

    mark_posted(post["id"], post_urn)
    return 0


if __name__ == "__main__":
    sys.exit(main())

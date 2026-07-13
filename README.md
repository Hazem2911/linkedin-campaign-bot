# LinkedIn Campaign Bot 🤖

A small bot that publishes my LinkedIn content series — **"My Claude Diaries"** — automatically, on schedule, with images and captions. Built with [Claude](https://claude.com), runs **free** on GitHub Actions, and uses the **official LinkedIn API** (no scraping, no fake browsers, account-safe).

> The twist: this bot is part of the campaign it publishes. The series is about working with AI — and AI wrote the posts, designed the images, and built this bot. I directed.

## How it works

```
schedule.json          GitHub Actions (cron, Sun+Wed 09:05 Cairo)
     │                        │
     ▼                        ▼
 "what is due today?"  ──►  post_to_linkedin.py
                              │  1. upload image  (LinkedIn Assets API)
                              │  2. publish post  (LinkedIn UGC API)
                              │  3. save state    (never double-posts)
                              ▼
                        your LinkedIn profile ✨
```

Everything lives in the repo: captions in `posts/`, images in `images/`, dates in `schedule.json`, published-state in `state/`.

## Setup (10 minutes, once)

**1. Create a LinkedIn app** (free) at [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
   - Products tab → request **"Share on LinkedIn"** and **"Sign In with LinkedIn using OpenID Connect"** (instant approval)
   - Auth tab → add redirect URL: `http://localhost:8914/callback`

**2. Get your token** (locally):

```bash
pip install -r requirements.txt
export LINKEDIN_CLIENT_ID=your_client_id
export LINKEDIN_CLIENT_SECRET=your_client_secret
python get_token.py
```

Your browser opens, you approve once, and it prints `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN`.

**3. Add GitHub secrets:** repo → Settings → Secrets and variables → Actions → add both values as secrets.

**4. Push and forget.** The workflow wakes up Sunday and Wednesday at 09:05 Cairo time, checks `schedule.json`, and posts whatever is due. Done.

## Useful commands

```bash
python post_to_linkedin.py --due --dry-run   # what would post today?
python post_to_linkedin.py --post 3 --dry-run # preview post 3
python post_to_linkedin.py --post 3           # force-post post 3 right now
```

You can also trigger a post manually from the Actions tab (workflow_dispatch → enter a post id).

## Edit the campaign

Change dates in `schedule.json`, captions in `posts/*.txt`, images in `images/`. That's the whole CMS.

## Notes

- The access token lives ~60 days — longer than the campaign. Re-run `get_token.py` if it expires.
- Posting time is `05 6 * * 0,3` UTC = 09:05 Cairo during Egypt's summer time (UTC+3). If your campaign runs November–April (UTC+2), change it to `05 7 * * 0,3`.
- Uses LinkedIn's official `/v2/assets` + `/v2/ugcPosts` endpoints with the `w_member_social` scope. One profile, your own content — exactly what the API is for.

## Built with

Claude (planning, copy, image generation pipeline, and this code) · Python · GitHub Actions · the LinkedIn API

---

*If this repo helps you run your own content series, a ⭐ makes my day.*

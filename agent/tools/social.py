"""
Social media posting — Twitter/X and Bluesky.
"""
from __future__ import annotations

import os


# ── Twitter/X ─────────────────────────────────────────────────────────────────

def post_to_twitter(text: str) -> str | None:
    """
    Post a tweet via Twitter API v2.
    Returns the tweet URL on success, None if credentials are missing.
    """
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

    if os.environ.get("LOCAL_MODE", "").lower() == "true":
        print(f"[LOCAL] Would tweet: {text[:80]}...")
        return None

    if not all([api_key, api_secret, access_token, access_secret]):
        print("[social] Twitter credentials not configured — skipping.")
        return None

    try:
        import tweepy

        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]

        # Derive username from access token (format: userId-...)
        user_response = client.get_me()
        username = user_response.data.username if user_response.data else "i"

        url = f"https://twitter.com/{username}/status/{tweet_id}"
        print(f"[social] Tweeted: {url}")
        return url

    except Exception as e:
        print(f"[social] Twitter post failed: {e}")
        return None


# ── Bluesky ───────────────────────────────────────────────────────────────────

def post_to_bluesky(text: str) -> str | None:
    """
    Post to Bluesky via AT Protocol.
    Returns the post URL on success, None if credentials are missing.
    """
    handle = os.environ.get("BLUESKY_HANDLE")
    app_password = os.environ.get("BLUESKY_APP_PASSWORD")

    if os.environ.get("LOCAL_MODE", "").lower() == "true":
        print(f"[LOCAL] Would post to Bluesky: {text[:80]}...")
        return None

    if not all([handle, app_password]):
        print("[social] Bluesky credentials not configured — skipping.")
        return None

    try:
        from atproto import Client as ATClient

        client = ATClient()
        client.login(handle, app_password)

        # Bluesky has a 300 char limit
        if len(text) > 300:
            text = text[:297] + "..."

        post = client.send_post(text)

        # Build URL from AT URI
        # AT URI format: at://did:plc:.../app.bsky.feed.post/rkey
        at_uri = post.uri
        rkey = at_uri.split("/")[-1]
        clean_handle = handle.lstrip("@")
        url = f"https://bsky.app/profile/{clean_handle}/post/{rkey}"

        print(f"[social] Posted to Bluesky: {url}")
        return url

    except Exception as e:
        print(f"[social] Bluesky post failed: {e}")
        return None


# ── Shared helper ─────────────────────────────────────────────────────────────

def share_post(title: str, summary: str, url: str) -> dict[str, str | None]:
    """
    Share a blog post to both platforms.
    Returns {"twitter": url_or_none, "bluesky": url_or_none}.
    """
    text = f"{title}\n\n{summary}\n\n{url}"

    # Twitter has a 280-char limit
    twitter_text = text if len(text) <= 280 else f"{title}\n\n{url}"

    return {
        "twitter": post_to_twitter(twitter_text),
        "bluesky": post_to_bluesky(text),
    }

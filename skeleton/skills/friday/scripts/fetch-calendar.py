#!/usr/bin/env python3
"""Fetch Google Calendar events directly via the Google Calendar API.

Uses the same OAuth credentials as the google-calendar-mcp-server.
Reads timezone from ~/.anamnesis.yaml (falls back to UTC).

Usage: fetch-calendar.py <output.json> [--date YYYY-MM-DD]
"""
import json
import ssl
import sys
import os
from datetime import datetime, timezone, timedelta

# SSL context for macOS — use system certs or certifi
def _ssl_context():
    ctx = ssl.create_default_context()
    for cafile in [
        "/etc/ssl/cert.pem",
        "/opt/homebrew/etc/ca-certificates/cert.pem",
    ]:
        if os.path.exists(cafile):
            ctx.load_verify_locations(cafile)
            return ctx
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx

SSL_CTX = _ssl_context()

TOKEN_FILE = os.path.expanduser("~/.gcalendar-mcp-token.json")
CREDENTIALS_FILE = os.path.expanduser("~/.gdrive-credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def load_config_timezone():
    """Read timezone from ~/.anamnesis.yaml, fallback to UTC."""
    config_path = os.path.expanduser("~/.anamnesis.yaml")
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            # Try calendar.timezone, then schedule.timezone, then UTC
            tz = cfg.get("calendar", {}).get("timezone") or \
                 cfg.get("schedule", {}).get("timezone") or "UTC"
            return tz
        except Exception:
            pass
    return "UTC"


def iana_to_utc_offset(tz_name):
    """Convert IANA timezone name to UTC offset string for API queries."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)
        offset = now.utcoffset()
        total_seconds = int(offset.total_seconds())
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes = remainder // 60
        sign = "+" if total_seconds >= 0 else "-"
        return f"{sign}{hours:02d}:{minutes:02d}"
    except Exception:
        return "+00:00"


def load_and_refresh_token():
    """Load OAuth token, refresh if expired, return access token string."""
    import urllib.request
    import urllib.parse

    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    expiry_str = token_data.get("expiry", "")
    needs_refresh = True
    if expiry_str:
        try:
            expiry_str = expiry_str.replace("Z", "+00:00")
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            needs_refresh = datetime.now(timezone.utc) >= expiry - timedelta(minutes=5)
        except (ValueError, TypeError):
            needs_refresh = True

    if not needs_refresh:
        return token_data["token"]

    refresh_token = token_data.get("refresh_token")
    client_id = token_data.get("client_id")
    client_secret = token_data.get("client_secret")
    token_uri = token_data.get("token_uri", "https://oauth2.googleapis.com/token")

    if not all([refresh_token, client_id, client_secret]):
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
        installed = creds.get("installed", creds.get("web", {}))
        client_id = client_id or installed.get("client_id")
        client_secret = client_secret or installed.get("client_secret")
        token_uri = token_uri or installed.get("token_uri")

    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(token_uri, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
        result = json.loads(resp.read())

    new_token = result["access_token"]
    expires_in = result.get("expires_in", 3600)

    token_data["token"] = new_token
    token_data["expiry"] = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()
    if "refresh_token" in result:
        token_data["refresh_token"] = result["refresh_token"]

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    return new_token


def fetch_events(access_token, time_min, time_max):
    import urllib.request
    import urllib.parse

    params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "maxResults": 25,
        "singleEvents": "true",
        "orderBy": "startTime",
    })

    url = f"{CALENDAR_API}/calendars/primary/events?{params}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")

    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
        return json.loads(resp.read())


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch-calendar.py <output.json> [--date YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    output_file = sys.argv[1]

    target_date = None
    for i, arg in enumerate(sys.argv):
        if arg == "--date" and i + 1 < len(sys.argv):
            target_date = sys.argv[i + 1]

    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    tz_name = load_config_timezone()
    offset = iana_to_utc_offset(tz_name)

    time_min = f"{target_date}T00:00:00{offset}"
    time_max = f"{target_date}T23:59:59{offset}"

    try:
        access_token = load_and_refresh_token()
    except Exception as e:
        print(f"ERROR: Failed to load/refresh OAuth token: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = fetch_events(access_token, time_min, time_max)
    except Exception as e:
        print(f"ERROR: Failed to fetch calendar events: {e}", file=sys.stderr)
        sys.exit(1)

    output = {"events": result.get("items", [])}

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    event_count = len(output["events"])
    print(f"Fetched {event_count} events for {target_date} (tz: {tz_name})")


if __name__ == "__main__":
    main()

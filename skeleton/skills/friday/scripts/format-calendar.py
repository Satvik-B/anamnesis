#!/usr/bin/env python3
"""Format raw Google Calendar JSON into calendar.md markdown.

Usage: format-calendar.py <input.json> <output.md> <sync_time> [timezone]
  timezone: IANA timezone name (e.g. "Asia/Kolkata"). Default: UTC.
            Also reads from ~/.anamnesis.yaml if not provided.
"""
import json
import sys
import os
from datetime import datetime, timezone, timedelta


def load_config_timezone():
    """Read timezone from ~/.anamnesis.yaml, fallback to UTC."""
    config_path = os.path.expanduser("~/.anamnesis.yaml")
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            return cfg.get("calendar", {}).get("timezone") or \
                   cfg.get("schedule", {}).get("timezone") or "UTC"
        except Exception:
            pass
    return "UTC"


def get_tz(tz_name):
    """Get timezone object from IANA name."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.utc


def parse_time(event, key, tz):
    """Parse start/end time from event, return datetime or None for all-day."""
    obj = event.get(key, {})
    if "dateTime" in obj:
        dt = datetime.fromisoformat(obj["dateTime"])
        return dt.astimezone(tz)
    return None


def format_duration(start, end):
    if not start or not end:
        return "All day"
    mins = int((end - start).total_seconds() / 60)
    if mins < 60:
        return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h{m}m" if m else f"{h}h"


def format_time_range(start, end):
    if not start:
        return "All day"
    s = start.strftime("%H:%M")
    e = end.strftime("%H:%M") if end else ""
    return f"{s}-{e}"


def classify_event(event):
    """Classify event as meeting, focus, social, etc."""
    summary = (event.get("summary") or "").lower()
    if any(w in summary for w in ["focus", "block", "heads down"]):
        return "Focus"
    if any(w in summary for w in ["1:1", "1on1", "sync", "standup", "stand-up", "scrum"]):
        return "1:1/Sync"
    if any(w in summary for w in ["lunch", "break", "coffee"]):
        return "Break"
    if any(w in summary for w in ["interview"]):
        return "Interview"
    attendees = event.get("attendees", [])
    if len(attendees) > 5:
        return "Large meeting"
    if len(attendees) > 1:
        return "Meeting"
    return "Event"


def extract_location(event):
    """Extract location from event, truncate if long."""
    loc = event.get("location", "") or ""
    # Clean up Google Meet / Zoom URLs from location
    if loc.startswith("http"):
        return ""
    if len(loc) > 40:
        loc = loc[:37] + "..."
    return loc


def extract_zoom_link(event):
    """Extract Zoom/Meet link from event."""
    # Check conferenceData first
    conf = event.get("conferenceData", {})
    for entry in conf.get("entryPoints", []):
        uri = entry.get("uri", "")
        if "zoom.us" in uri or "meet.google" in uri:
            return uri

    # Check location
    loc = event.get("location", "") or ""
    if "zoom.us" in loc or "meet.google" in loc:
        return loc

    # Check description
    desc = event.get("description", "") or ""
    for line in desc.split("\n"):
        line = line.strip()
        if "zoom.us" in line or "meet.google" in line:
            # Extract URL
            for word in line.split():
                if word.startswith("http") and ("zoom.us" in word or "meet.google" in word):
                    return word
    return ""


def format_attendees(event, max_show=3):
    """Format attendee list, truncating if too many."""
    attendees = event.get("attendees", [])
    if not attendees:
        return ""
    names = []
    for a in attendees:
        if a.get("self"):
            continue
        name = a.get("displayName") or a.get("email", "").split("@")[0]
        names.append(name)
    if len(names) > max_show:
        return ", ".join(names[:max_show]) + f" +{len(names) - max_show}"
    return ", ".join(names)


def main():
    if len(sys.argv) < 4:
        print("Usage: format-calendar.py <input.json> <output.md> <sync_time> [timezone]",
              file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    sync_time = sys.argv[3]
    tz_name = sys.argv[4] if len(sys.argv) > 4 else load_config_timezone()
    tz = get_tz(tz_name)

    with open(input_file) as f:
        data = json.load(f)

    events = data.get("events", [])
    today = datetime.now(tz).strftime("%Y-%m-%d")
    day_name = datetime.now(tz).strftime("%A")

    lines = [
        f"# Calendar",
        f"",
        f"*Last synced: {sync_time} ({tz_name})*",
        f"",
        f"## {today} ({day_name})",
        f"",
    ]

    if not events:
        lines.append("No events today.")
    else:
        lines.append("| Time | Duration | Event | Type | Attendees | Location | Zoom | Notes |")
        lines.append("|------|----------|-------|------|-----------|----------|------|-------|")

        for event in events:
            start = parse_time(event, "start", tz)
            end = parse_time(event, "end", tz)
            summary = event.get("summary", "(No title)")
            time_range = format_time_range(start, end)
            duration = format_duration(start, end)
            event_type = classify_event(event)
            attendees = format_attendees(event)
            location = extract_location(event)
            zoom = extract_zoom_link(event)

            lines.append(
                f"| {time_range} | {duration} | {summary} | {event_type} "
                f"| {attendees} | {location} | {zoom} | |"
            )

    lines.append("")

    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    print(f"Formatted {len(events)} events for {today}")


if __name__ == "__main__":
    main()

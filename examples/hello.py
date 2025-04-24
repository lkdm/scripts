#!/usr/bin/env -S uv --quiet run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
# "ffmpeg-normalize",
# ]
# ///

def day_kind(day):
    match day:
        case ("Monday"
            | "Tuesday"
            | "Wednesday"
            | "Thursday"
            | "Friday"):
            return "Weekday"
        case "Saturday" | "Sunday":
            return "Weekend"

print(f"Hello it is a {day_kind('Tuesday')}")

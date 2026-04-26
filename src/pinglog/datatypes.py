from typing import TypedDict


class XPBreakdown(TypedDict):
    base_xp: int
    first_log_bonus: int
    comeback_bonus: int
    early_morning_bonus: int
    late_night_bonus: int
    accuracy_bonus: int
    streak_bonus: int
    total_xp: int


class ParsedReply(TypedDict):
    entry: str
    xp: XPBreakdown
    snooze: int
    silent: bool
    timestamp: int

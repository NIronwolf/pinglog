from pinglog.db.queries import (
    create_or_update_state,
    get_timezone,
    insert_log,
    get_next_ping,
    set_next_ping,
    set_silent_next,
    get_ping_interval,
    is_silent_next,
    get_total_xp,
    get_streak,
    get_day,
    get_recent_logs,
    delete_log_entry,
    edit_log_entry,
)
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from pinglog.util import parse_reply, time_string_to_seconds
from telegram.helpers import escape_markdown
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import logging

logger = logging.getLogger(__name__)


async def handle_start(update, context):
    user_timezone = get_timezone(update.effective_user.id)
    now = int(datetime.now(timezone.utc).timestamp())
    next_ping_time = now + 60 * 60  # 60 minutes in seconds
    create_or_update_state(update.effective_user.id, user_timezone, next_ping_time)

    await update.message.reply_text(
        "Hello! I'm your PingLog bot.  You can send a message any time and I'll log it as your activity."
    )
    await update.message.reply_text(
        "I'll ping you every hour to check in. You can also snooze the pings for a certain amount of time if you need a break."
        "Just add snooze or silent and a duration as XhYm at the end.  For example: 'Went for a run snooze 2h' or 'Feeling tired silent 8h'"
    )


async def handle_log_message(update, context):
    if not await check_registered(update, context):
        return

    if not update.message or not update.message.text or not update.effective_user:
        return

    log = parse_reply(update.message.text, update.effective_user.id)

    insert_log(update.effective_user.id, log["timestamp"], log["entry"], log["xp"])

    snooze = (
        log["snooze"]
        if log["snooze"] > 0
        else get_ping_interval(update.effective_user.id)
    )
    set_next_ping(
        update.effective_user.id,
        log["timestamp"] + snooze,
    )
    set_silent_next(update.effective_user.id, log["silent"])

    safe_entry = escape_markdown(log["entry"], version=2)
    safe_total = escape_markdown(str(log["xp"]["total_xp"]), version=2)

    parts = [
        f"Logged: *{safe_entry}*",
        f"XP Earned: *{safe_total} XP*",
        f"  Base: \\+{log['xp']['base_xp']} XP",
    ]
    if log["xp"]["first_log_bonus"]:
        parts.append(f"  First Log Bonus: \\+{log['xp']['first_log_bonus']} XP")
    if log["xp"]["comeback_bonus"]:
        parts.append(f"  Comeback Bonus: \\+{log['xp']['comeback_bonus']} XP")
    if log["xp"]["early_morning_bonus"]:
        parts.append(f"  Early Morning Bonus: \\+{log['xp']['early_morning_bonus']} XP")
    if log["xp"]["late_night_bonus"]:
        parts.append(f"  Late Night Bonus: \\+{log['xp']['late_night_bonus']} XP")
    if log["xp"]["accuracy_bonus"]:
        parts.append(f"  Accuracy Bonus: \\+{log['xp']['accuracy_bonus']} XP")
    if log["xp"]["streak_bonus"]:
        parts.append(f"  Streak Bonus: \\+{log['xp']['streak_bonus']} XP")

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def handle_status(update, context):
    """Replys with the current status of the user.
    Streak: X days
    Total XP: Y XP
    Today: Z entries, W XP

    Next ping: HH:MM (in N minutes) [Silent]"""
    user_timezone = get_timezone(update.effective_user.id)
    next_ping_time = get_next_ping(update.effective_user.id)
    next_ping_local = (
        datetime.fromtimestamp(next_ping_time, tz=timezone.utc).astimezone(
            ZoneInfo(user_timezone)
        )
        if next_ping_time
        else None
    )
    next_ping_silent = is_silent_next(update.effective_user.id)
    streak_days = get_streak(update.effective_user.id)
    total_xp = get_total_xp(update.effective_user.id)
    activity_today = get_day(
        update.effective_user.id,
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date(),
    )
    entries_today = len(activity_today)
    xp_today = sum(entry["xp_earned"] for entry in activity_today)

    parts = [
        f"Streak: *{streak_days} days*",
        f"Total XP: *{total_xp} XP*",
        f"Today: *{entries_today} entries*, *{xp_today} XP*",
        "",
        f"Next ping: *{next_ping_local.strftime('%H:%M') if next_ping_local else 'N/A'}*"
        + (" \\[Silent\\]" if next_ping_silent else ""),
    ]

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def handle_today(update, context):
    user_timezone = get_timezone(update.effective_user.id)
    today = datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
    await _show_log(update, context, today)


async def handle_yesterday(update, context):
    user_timezone = get_timezone(update.effective_user.id)
    yesterday = datetime.now(timezone.utc).astimezone(
        ZoneInfo(user_timezone)
    ).date() - timedelta(days=1)
    await _show_log(update, context, yesterday)


async def handle_date(update, context):
    user_timezone = get_timezone(update.effective_user.id)

    if context.args:
        try:
            target_date = date.fromisoformat(context.args[0])
        except ValueError:
            relative_seconds = time_string_to_seconds(context.args[0])
            if relative_seconds is not None:
                target_date = datetime.now(timezone.utc).astimezone(
                    ZoneInfo(user_timezone)
                ).date() - timedelta(seconds=relative_seconds)
            else:
                await update.message.reply_markdown_v2(
                    "Invalid date entered\\.  Format 'YYYY\\-MM\\-DD' or '3d'\\."
                )
                return
    else:
        await update.message.reply_markdown_v2(
            "Invalid date entered\\.  Format 'YYYY\\-MM\\-DD' or '3d'\\."
        )
        return

    await _show_log(update, context, target_date)


async def handle_delete(update, context):
    if context.args:
        if context.args[0].isdigit():
            idx = int(context.args[0])
            recent_logs = get_recent_logs(update.effective_user.id)
            if 0 <= idx < len(recent_logs):
                log_to_delete = recent_logs[idx]
                logger.debug(f"Log entry selected for deletion: {log_to_delete}")

                keyboard = [
                    [
                        InlineKeyboardButton("Cancel", callback_data="cancel"),
                        InlineKeyboardButton(
                            "DELETE", callback_data=f"delete:{log_to_delete['id']}"
                        ),
                    ],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                safe_activity = escape_markdown(log_to_delete["activity"], version=2)
                user_timezone = get_timezone(update.effective_user.id)
                entry_time = (
                    datetime.fromtimestamp(log_to_delete["timestamp"], tz=timezone.utc)
                    .astimezone(ZoneInfo(user_timezone))
                    .strftime("%H:%M")
                )

                await update.message.reply_markdown_v2(
                    f"*Delete* this log entry?\n\n{entry_time} \\- *{safe_activity}*",
                    reply_markup=reply_markup,
                    reply_to_message_id=update.message.message_id,
                )
                return

        await update.message.reply_markdown_v2(
            "Invalid log index\\. Use /delete to see valid indices\\."
        )
        return
    await _show_recent(update, context)


async def handle_delete_callback(update, context):
    query = update.callback_query

    idx = int(query.data.split(":")[1])
    logger.debug(f"delete callback received for log index: {idx}")

    delete_log_entry(idx)

    await query.answer()

    entry_text = query.message.text.split("this log entry?\n\n", 1)[1]
    await query.edit_message_text(
        text=f"*Deleted log entry*:\n\n~{escape_markdown(entry_text, version=2)}~",
        parse_mode="MarkdownV2",
    )


async def handle_edit(update, context):
    if context.args:
        if context.args[0].isdigit():
            if "pending_edits" not in context.user_data:
                context.user_data["pending_edits"] = {}
            if 10 <= len(context.user_data["pending_edits"]):
                await update.message.reply_markdown_v2(
                    "Too many pending edits\\. Please complete or cancel existing edits before creating new ones\\.\n"
                    "Or you can clear all edits using /clearedits"
                )
                return
            idx = int(context.args[0])
            recent_logs = get_recent_logs(update.effective_user.id)
            if 0 <= idx < len(recent_logs):
                log_to_edit = recent_logs[idx]
                logger.debug(f"Log entry selected to edit: {log_to_edit}")

                parsed = parse_reply(
                    " ".join(context.args[1:]), update.effective_user.id
                )
                if parsed["entry"] == "":
                    await update.message.reply_markdown_v2(
                        "No new activity text provided\\.\n"
                        "Please provide the new activity text after the index\\."
                    )
                    return
                else:
                    updated_activity = f"{parsed['entry']}"
                    safe_updated_activity = escape_markdown(updated_activity, version=2)

                safe_old_activity = escape_markdown(log_to_edit["activity"], version=2)
                user_timezone = get_timezone(update.effective_user.id)
                old_time = (
                    datetime.fromtimestamp(log_to_edit["timestamp"], tz=timezone.utc)
                    .astimezone(ZoneInfo(user_timezone))
                    .strftime("%H:%M")
                )
                edit_timestamp = (
                    parsed["timestamp"]
                    if parsed["timestamp_was_set"]
                    else log_to_edit["timestamp"]
                )
                updated_time = (
                    datetime.fromtimestamp(edit_timestamp, tz=timezone.utc)
                    .astimezone(ZoneInfo(user_timezone))
                    .strftime("%H:%M")
                )

                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Cancel",
                            callback_data=f"cancel:{update.message.message_id}",
                        ),
                        InlineKeyboardButton(
                            "EDIT", callback_data=f"edit:{update.message.message_id}"
                        ),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                confirmation = await update.message.reply_markdown_v2(
                    f"*Edit* this log entry?\n\n"
                    f"{old_time} \\- *{safe_old_activity}*\n"
                    f"  \\- to \\-\n"
                    f"{updated_time} \\- *{safe_updated_activity}*",
                    reply_markup=reply_markup,
                    reply_to_message_id=update.message.message_id,
                )

                # Store edit for callback handling
                context.user_data["pending_edits"][update.message.message_id] = {
                    "id": log_to_edit["id"],
                    "parsed": parsed,
                    "confirm_message_id": confirmation.message_id,  # Probably don't need this or confmation variable
                }
                logger.debug(
                    f"Stored pending edit for message {update.message.message_id}: "
                    f"{context.user_data['pending_edits'][update.message.message_id]}"
                )
                return

        await update.message.reply_markdown_v2(
            "Invalid log index\\. Use /edit to see valid indices\\."
        )
        return
    await _show_recent(update, context)


async def handle_edit_callback(update, context):
    query = update.callback_query

    idx = int(query.data.split(":")[1])
    logger.debug(f"edit callback received for message index: {idx}")

    pending = context.user_data.get("pending_edits", {}).get(idx)
    if pending is None:
        logger.error(f"No pending edit found for message index: {idx}")
        await query.answer(text="Error: No pending edit found.", show_alert=True)
        await query.edit_message_text(text="Edit expired.")
        return
    parsed = pending["parsed"]

    timestamp_to_update = parsed["timestamp"] if parsed["timestamp_was_set"] else None
    edit_log_entry(
        log_id=pending["id"],
        new_activity=parsed["entry"],
        new_timestamp=timestamp_to_update,
    )
    del context.user_data["pending_edits"][idx]

    await query.answer()

    entry_text = query.message.text.split("this log entry?\n\n", 1)[1]
    old_entry = entry_text.split("\n  - to -\n", 1)[0]
    edited_entry = entry_text.split("\n  - to -\n", 1)[1]
    await query.edit_message_text(
        text=f"*Edited log entry*:\n\n~{escape_markdown(old_entry, version=2)}~\n"
        f"  \\- to \\-\n"
        f"{escape_markdown(edited_entry, version=2)}",
        parse_mode="MarkdownV2",
    )


async def handle_clearedits(update, context):
    context.user_data.pop("pending_edits", None)
    await update.message.reply_markdown_v2("All pending edits cleared\\.")


async def handle_cancel_callback(update, context):
    query = update.callback_query

    parts = query.data.split(":")
    if len(parts) > 1:
        msg_id = int(parts[1])
        context.user_data.get("pending_edits", {}).pop(msg_id, None)
        logger.debug(f"Cancelled pending edit for message index: {msg_id}")

    await query.answer()

    await query.edit_message_text(text="Action cancelled.")


async def _show_log(update, context, log_date: date):
    """Replys with date's entries in the format:
    Today/Yesterday/X days ago - *Month D* (Y endtries, W XP)

    *HH:MM* _+X XP_
    Entry text

    *HH:MM* _+X XP_
    Entry text
    """
    user_timezone = get_timezone(update.effective_user.id)
    activity_today = get_day(update.effective_user.id, log_date)

    entries_today = len(activity_today)
    xp_today = sum(entry["xp_earned"] for entry in activity_today)

    day_diff = (
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date() - log_date
    ).days
    day_str = (
        "Today"
        if day_diff == 0
        else "Yesterday"
        if day_diff == 1
        else f"{day_diff} days ago"
    )

    parts = [
        f"{day_str} \\- *{log_date.strftime('%B %-d')}*"
        + f" \\({entries_today} entries, {xp_today} XP\\)",
    ]
    for entry in activity_today:
        entry_time = (
            datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc)
            .astimezone(ZoneInfo(user_timezone))
            .strftime("%H:%M")
        )
        parts.append(
            f"\n*{entry_time}* _\\+{entry['xp_earned']} XP_\n{escape_markdown(entry['activity'], version=2)}"
        )

    message = "\n".join(parts)

    await update.message.reply_markdown_v2(message)


async def _show_recent(update, context):
    recent_logs = get_recent_logs(update.effective_user.id)
    if recent_logs is None or len(recent_logs) == 0:
        await update.message.reply_markdown_v2("No recent activity found\\.")
        return
    user_timezone = get_timezone(update.effective_user.id)

    formated_logs = []
    idx = 0
    current_day = entry_date = (
        datetime.fromtimestamp(recent_logs[0]["timestamp"], tz=timezone.utc)
        .astimezone(ZoneInfo(user_timezone))
        .date()
    )
    logger.debug(f"Current Day initialized to: {current_day}")
    for log in recent_logs:
        entry_date = (
            datetime.fromtimestamp(log["timestamp"], tz=timezone.utc)
            .astimezone(ZoneInfo(user_timezone))
            .date()
        )
        if entry_date != current_day:
            day_diff = (
                datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
                - current_day
            ).days  # - 1
            logger.debug(
                f"Day Diff: {day_diff}, Entry Date: {entry_date}, Current Date: {datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()}"
            )
            day_str = (
                "Today"
                if day_diff == 0
                else "Yesterday"
                if day_diff == 1
                else f"{day_diff} days ago"
            )
            formated_logs.append(
                f"\n*{day_str}* \\- {current_day.strftime('%B %-d')}\n"
            )
            current_day = entry_date
        formated_logs.append(
            f"*{idx}* \\- "
            f"{datetime.fromtimestamp(log['timestamp'], tz=timezone.utc).astimezone(ZoneInfo(user_timezone)).strftime('%H:%M')} "
            f"{escape_markdown(log['activity'], version=2)}\n"
        )
        idx += 1

    day_diff = (
        datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()
        - entry_date
    ).days
    logger.debug(
        f"Day Diff: {day_diff}, Entry Date: {entry_date}, Current Date: {datetime.now(timezone.utc).astimezone(ZoneInfo(user_timezone)).date()}"
    )
    day_str = (
        "Today"
        if day_diff == 0
        else "Yesterday"
        if day_diff == 1
        else f"{day_diff} days ago"
    )
    formated_logs.append(f"\n*{day_str}* \\- {entry_date.strftime('%B %-d')}\n")

    formated_logs = list(reversed(formated_logs))

    parts = ["Recent activity:"]
    for log in formated_logs:
        logger.debug(f"Formatted log entry: {log}")
        parts.append(log)

    await update.message.reply_markdown_v2("\n".join(parts))


async def check_registered(update, context) -> bool:
    if get_next_ping(update.effective_user.id) is None:
        await update.message.reply_text(
            "Please send /start first to set up your account!"
        )
        return False
    return True

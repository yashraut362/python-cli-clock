import math
import threading
from datetime import datetime, timedelta

from notify import announce

_lock = threading.Lock()
_alarms = {}
_next_id = 1


def _parse_time(raw):
    parts = raw.split(":")
    if len(parts) != 2:
        return None

    hour_text, minute_text = parts
    if not hour_text.isdigit() or not minute_text.isdigit():
        return None
    if not 1 <= len(hour_text) <= 2 or len(minute_text) != 2:
        return None

    hour = int(hour_text)
    minute = int(minute_text)
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def _next_target(hour, minute, now=None):
    now = now or datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def _run(alarm_id, label, target, cancel):
    delay = (target - datetime.now()).total_seconds()
    if delay > 0 and cancel.wait(delay):
        return
    if cancel.is_set():
        return

    with _lock:
        entry = _alarms.get(alarm_id)
        if entry is None or entry["cancel"] is not cancel:
            return
        del _alarms[alarm_id]

    when = target.strftime("%H:%M")
    announce(f"🔔 Alarm — {label} at {when}", "Ping")


def _schedule(target, label):
    label = (label or "").strip() or "Alarm"
    cancel = threading.Event()

    global _next_id
    with _lock:
        alarm_id = _next_id
        _next_id += 1
        thread = threading.Thread(
            target=_run,
            args=(alarm_id, label, target, cancel),
            name=f"alarm-{alarm_id}",
        )
        _alarms[alarm_id] = {
            "label": label,
            "target": target,
            "cancel": cancel,
            "thread": thread,
        }
        thread.start()

    return alarm_id


def start_alarm(hour, minute, label="Alarm"):
    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError("hour must be a whole number from 0 to 23")
    if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute <= 59:
        raise ValueError("minute must be a whole number from 0 to 59")

    target = _next_target(hour, minute)
    return _schedule(target, label), target


def list_alarms():
    with _lock:
        now = datetime.now()
        return [
            (
                alarm_id,
                entry["label"],
                entry["target"].strftime("%H:%M"),
                max(0, math.ceil((entry["target"] - now).total_seconds())),
            )
            for alarm_id, entry in sorted(_alarms.items())
        ]


def remove_alarm(alarm_id):
    with _lock:
        entry = _alarms.pop(alarm_id, None)
        if entry is None:
            return False
        entry["cancel"].set()
        thread = entry["thread"]

    thread.join()
    return True


def stop_alarms():
    with _lock:
        entries = list(_alarms.values())
        _alarms.clear()
        for entry in entries:
            entry["cancel"].set()

    for entry in entries:
        entry["thread"].join()


def set_alarm():
    parsed = _parse_time(input("Enter time (HH:MM): ").strip())
    if parsed is None:
        print("Enter a time in HH:MM format.")
        return

    hour, minute = parsed
    label = input("Enter label (optional): ").strip()
    alarm_id, target = start_alarm(hour, minute, label)
    day = "tomorrow" if target.date() > datetime.now().date() else "today"
    print(f"Alarm {alarm_id} set for {target.strftime('%H:%M')} {day}.")


def view_alarms():
    alarms = list_alarms()
    if not alarms:
        print("No alarms.")
        return

    for alarm_id, label, when, remaining in alarms:
        print(f"{alarm_id}. {label} - {when} - {remaining}s left")


def delete_alarm():
    raw = input("Enter alarm id: ").strip()
    if not raw.isdigit() or not remove_alarm(int(raw)):
        print("No alarm with that id.")
        return

    print(f"Alarm {raw} deleted.")

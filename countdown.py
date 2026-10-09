import math
import threading
import time

_lock = threading.Lock()
_countdowns = {}
_next_id = 1


def _parse_seconds(raw):
    if not raw.isdigit():
        return None
    seconds = int(raw)
    if seconds <= 0:
        return None
    return seconds


def _run(countdown_id, label, seconds, cancel):
    finished = not cancel.wait(seconds)
    if not finished:
        return

    with _lock:
        entry = _countdowns.get(countdown_id)
        if entry is None or entry["cancel"] is not cancel:
            return
        del _countdowns[countdown_id]

    print(f"\n\aCountdown finished: {label}", flush=True)


def start_countdown(seconds, label="Countdown"):
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
        raise ValueError("seconds must be a whole number greater than 0")

    label = (label or "").strip() or "Countdown"
    cancel = threading.Event()

    global _next_id
    with _lock:
        countdown_id = _next_id
        _next_id += 1
        thread = threading.Thread(
            target=_run,
            args=(countdown_id, label, seconds, cancel),
            name=f"countdown-{countdown_id}",
        )
        _countdowns[countdown_id] = {
            "label": label,
            "seconds": seconds,
            "end": time.monotonic() + seconds,
            "cancel": cancel,
            "thread": thread,
        }
        thread.start()

    return countdown_id


def list_countdowns():
    with _lock:
        now = time.monotonic()
        return [
            (
                countdown_id,
                entry["label"],
                max(0, math.ceil(entry["end"] - now)),
            )
            for countdown_id, entry in sorted(_countdowns.items())
        ]


def remove_countdown(countdown_id):
    with _lock:
        entry = _countdowns.pop(countdown_id, None)
        if entry is None:
            return False
        entry["cancel"].set()
        thread = entry["thread"]

    thread.join()
    return True


def stop_countdowns():
    with _lock:
        entries = list(_countdowns.values())
        _countdowns.clear()
        for entry in entries:
            entry["cancel"].set()

    for entry in entries:
        entry["thread"].join()


def set_countdown():
    seconds = _parse_seconds(input("Enter seconds: ").strip())
    if seconds is None:
        print("Enter a whole number of seconds greater than 0.")
        return

    label = input("Enter label (optional): ").strip()
    countdown_id = start_countdown(seconds, label)
    print(f"Countdown {countdown_id} set for {seconds}s.")


def view_countdowns():
    countdowns = list_countdowns()
    if not countdowns:
        print("No countdowns.")
        return

    for countdown_id, label, remaining in countdowns:
        print(f"{countdown_id}. {label} - {remaining}s left")


def delete_countdown():
    raw = input("Enter countdown id: ").strip()
    if not raw.isdigit() or not remove_countdown(int(raw)):
        print("No countdown with that id.")
        return

    print(f"Countdown {raw} deleted.")

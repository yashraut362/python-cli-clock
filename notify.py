import os
import subprocess

_SOUNDS_DIR = "/System/Library/Sounds"


def announce(message, sound):
    print(f"\n{message}", flush=True)

    path = os.path.join(_SOUNDS_DIR, f"{sound}.aiff")
    if not os.path.isfile(path):
        return

    try:
        subprocess.run(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return

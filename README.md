# Python Alarm Clock

A local command-line clock. Set alarms for a time of day, or start countdowns in seconds. Several can run at once. Nothing is saved to a database.

Requires Python 3. No extra packages.

## Run

```bash
python3 main.py
```

```
===== PYTHON ALARM CLOCK =====
1. Alarm
2. Countdown
3. Exit
```

Choose **Exit**, or press Ctrl+C or Ctrl+D. Running alarms and countdowns are stopped before the program ends.

## Alarms

From the alarm menu you can set, view, or delete an alarm.

* Time is 24-hour `HH:MM`. `7:30` and `07:30` both work.
* The label is optional. A blank label is stored as `Alarm`.
* A time still ahead today rings today. A time that has already passed is set for tomorrow.
* **View** shows the id, label, time, and seconds left.

When it rings, the program prints `🔔 Alarm — Wake at 07:30`, plays the Mac Ping sound, and removes that alarm.

## Countdowns

From the countdown menu you can set, view, or delete a countdown.

* Enter a whole number of seconds greater than 0.
* The label is optional. A blank label is stored as `Countdown`.
* **View** shows the id, label, and seconds left.

When it ends, the program prints `⏰ Countdown finished — Tea`, plays the Mac Glass sound, and removes that countdown.

## Sounds

Alerts use the built-in Mac sounds through `afplay`:

| Alert | Sound |
| --- | --- |
| Alarm | Ping |
| Countdown | Glass |

If the sound file or `afplay` is unavailable, the message still prints.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Layout

| File | Role |
| --- | --- |
| `main.py` | Menus and exit cleanup |
| `alarm.py` | Alarm storage and threads |
| `countdown.py` | Countdown storage and threads |
| `notify.py` | Alert message and sound |
| `tests/test_app.py` | unittest suite |

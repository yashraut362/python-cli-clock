# CLI app countdown logic
_Exported on 09/10/2026 at 13:37:27 GMT+5:30 from Cursor (3.24.9)_

---

**User**

we want to build CLI based app , no ui , no DB basic local cli app. 
lets do step by step 

i have initiated python project with main.py by adding menu and submenu for CLI.
use minimal architecture using Python's standard library where practical.
keep impelementation minimal , i have already added menu and submenu. 

Next thing to build is countdown. 
lets create a new file to keep countdown logic sepearte. 
everything will be local for countdown , dict to store countdown , for running/ triggering countfown use threads
before exiting cli make sure to cleanup triggered countdowns. 

---

**Cursor**

I'll start from the menu you already built and add a separate countdown module that stays local, uses threads, and cleans up before the CLI exits. Let me read the project and the relevant workflow first.

The menu in `main.py` is already in place: Alarm, Countdown, and Exit, with Set / View / Delete under Countdown. Countdown choices do not do anything yet.

One behavior choice changes how the threads and cleanup should work.

When a countdown reaches zero, what should the CLI do?

1. **Print once and remove it** — one message plus a terminal bell, then drop it from the list.
2. **Print once and keep it** — same alert, but leave it listed as finished until you delete it.
3. **Repeat until dismissed** — keep alerting until you acknowledge it from the menu.

I would use option 1. The menu stays usable while the countdown runs in the background, and exit stops every running countdown before the process ends.

---

**User**

lets do , Print once and remove it 

---

**Cursor**

Print once, ring the terminal bell, and drop that countdown from the list. The menu stays open while it runs.

One input choice still changes the set flow.

How should Set Countdown ask for the length?

1. **Seconds only** — enter `90`. A short optional label is fine.
2. **Minutes and seconds** — enter `1 30`.
3. **Hours, minutes, and seconds** — enter `0 1 30`.

I would use option 1. Several countdowns can run at once, View shows the label and remaining time, and Delete stops that thread and removes it.

---

**User**

lets do seconds only 

---

**Cursor**

Seconds only. A countdown is a positive number of seconds, with an optional short label so View can tell them apart.

Three ways to run that in the background:

1. **One thread per countdown.** Each entry in a dict holds the label, end time, and a thread. The thread waits with a cancel event, so Delete and Exit can stop it early. When it finishes on its own, it prints once, rings the bell, and removes itself. This matches a local dict plus threads, and cleanup is a loop that signals every event and joins the threads.
2. **One scheduler thread.** A single thread wakes about once a second and checks the dict. Fewer threads, but Delete and Exit share that one loop, and a missed wake makes the alert late.
3. **`threading.Timer` per countdown.** Smallest API, and `cancel()` covers Delete and Exit. Remaining time still has to live in the dict, and a timer is awkward to interrupt cleanly if we later want a message on cancel.

I would use option 1. The menu stays responsive, several countdowns can run together, and leaving the CLI stops every live thread before the process exits.

---

**User**

since we want to keep multiple countdown at once , lets do One thread per countdown  

---

**Cursor**

One thread per countdown is the right fit. Here is the design for that piece, kept to the menu you already have.

**Storage.** `countdown.py` keeps one dict in memory. Each entry is an id, a label, the original seconds, a monotonic end time, a `threading.Event`, and the thread. A lock guards the dict. Ids are `1`, `2`, `3`, and so on.

**Set.** Ask for seconds, then an optional label. Empty label becomes `Countdown`. Seconds must be a whole number greater than 0. Start a thread that waits on the event for that many seconds. If the wait finishes on its own, print one line, ring the terminal bell, and remove the entry. If Delete or Exit sets the event first, the thread stops quietly.

**View and Delete.** View lists id, label, and whole seconds left. An empty list prints a short message. Delete asks for an id, sets that event, joins the thread, and removes the entry. An unknown id prints a short message and returns to the menu.

**Exit.** Choosing Exit, or leaving with Ctrl+C, signals every running countdown and joins those threads before the process ends. The menu stays usable while countdowns run. Alarm stays as it is.

Does this look right?

---

**User**

yes lets build ! 

---

**Cursor**

The design is settled: one thread per countdown, seconds only, print once, then remove it. I'll add `countdown.py` and wire it into the menu, including cleanup on exit.

Countdown now runs in the background from the menu you already built. The logic lives in `countdown.py`, and `main.py` only calls it.

* **Set** asks for a whole number of seconds, then an optional label. A blank label is stored as `Countdown`. Each countdown gets its own thread.
* **View** lists the id, label, and whole seconds left. Several can run at the same time.
* **Delete** stops that thread and removes it.
* When a countdown finishes on its own, it prints one line, rings the terminal bell, and removes itself.
* **Exit** and Ctrl+C signal every running countdown and wait for those threads to stop before the process ends.

Alarm is unchanged. A scripted menu run set a 30-second countdown, showed it, deleted it, and exited with no finish message. A separate check confirmed a 1-second countdown prints once and drops off the list.

---

**User**

lets add alarms similar to countdown only diff is adding time , lets ask user in HH:MM format 

---

**Cursor**

Alarms will follow the countdown setup: a separate module, one thread each, and cleanup on exit. The input difference is a clock time in `HH:MM`. I'll match the existing countdown code and wire it into the alarm menu.

The alarm menu will work like countdown: local dict, one thread per alarm, print once, then remove it. The time is a 24-hour `HH:MM`; if that time has already passed today, it is set for tomorrow.

Alarms now follow the same pattern as countdowns, in `alarm.py`. Set, View, and Delete are wired into the alarm menu, and Exit or Ctrl+C stops both alarms and countdowns.

* **Set** asks for a time in 24-hour `HH:MM`, then an optional label. `7:30` and `07:30` both work. A blank label is stored as `Alarm`.
* If that time is still ahead today, it rings today. If the minute has already passed, it is set for tomorrow.
* **View** shows the id, label, time, and seconds left. Each alarm runs on its own thread.
* **Delete** stops that thread and removes it.
* When it rings, it prints one line, rings the terminal bell, and removes itself.

A scripted menu run rejected `25:00`, set `07:30`, showed it, deleted it, and exited without ringing. A separate check confirmed an alarm fires once and drops off the list.

---

**User**

wheenver Countdown finished: or Alarm: is triggered show better message with emoji. 
another thing which is required is some notiifcation sound , for mac we can use internal notification sounds. 

---

**Cursor**

The finish lines are easy to miss, and the terminal bell is easy to miss on a Mac. I'll give both alerts a clearer message and play a built-in macOS sound.

Both alerts now print a clearer line and play a built-in Mac sound through `afplay`.

* A countdown ends with `⏰ Countdown finished — Tea` and the Glass sound.
* An alarm rings with `🔔 Alarm — Wake at 07:30` and the Ping sound.

Restart the running `python main.py` so it picks this up. Exit and start it again.

---

**User**

lets add some tests :- 
Review complete application and implementaion add a comprehensive but focused automated test. 
Use Python's built-in unittest framework for now since its just a small cli app . 

---

**Cursor**

I'll review the alarm, countdown, and notification flow, then add a focused `unittest` suite around the behavior that matters.

The app is four modules with shared in-memory state: menus in `main.py`, timers in `alarm.py` and `countdown.py`, and Mac sounds in `notify.py`. I'll cover parsing, scheduling, cancel, finish, and exit without playing sounds or waiting on real clock times.

The review matched the implementation: menus in `main.py`, one thread per alarm or countdown, and Mac sounds only when an alert actually fires. No behavior change was needed. The suite is in `tests/test_app.py` and uses `unittest`.

30 tests cover the paths that matter:

* Countdown and alarm parsing, including bad input that returns to the menu without asking for a label.
* An alarm set for a time already passed today is stored for tomorrow.
* A blank label becomes `Countdown` or `Alarm`.
* View, delete, and unknown ids.
* A finished timer alerts once, then removes itself, and leaves any other timer running.
* Delete and exit stop the thread and do not play the alert.
* Stopping alarms leaves countdowns running, and the reverse.
* The notification prints even when the sound file is missing or `afplay` fails. Sounds are mocked, so the suite stays quiet.
* A full menu session, a normal exit, Ctrl+D, and Ctrl+C.

All 30 passed in about 3.5 seconds. Run them from the project folder with:

```bash
python3 -m unittest discover -s tests -v
```

---

**User**

lets also update Readme file 

---

**Cursor**

The README is still a title only. I'll update it to match how the clock actually runs, including alarms, countdowns, sounds, and tests.

The README is only a title. I'll fill it in with how to run the clock, how alarms and countdowns behave, and how to run the tests.

The README now describes the clock as it works today.

It covers how to start `python3 main.py`, the alarm and countdown menus, the `HH:MM` and seconds inputs, today-versus-tomorrow alarms, the Ping and Glass sounds, exit cleanup, and how to run the tests.


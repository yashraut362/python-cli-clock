import io
import signal
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import alarm
import countdown
import main
import notify


def _reset_state():
    countdown.stop_countdowns()
    alarm.stop_alarms()
    countdown._next_id = 1
    alarm._next_id = 1


class AppTestCase(unittest.TestCase):
    def setUp(self):
        _reset_state()

    def tearDown(self):
        _reset_state()


class NotifyTests(unittest.TestCase):
    def test_prints_message_and_plays_system_sound(self):
        stdout = io.StringIO()
        with patch("notify.os.path.isfile", return_value=True), \
             patch("notify.subprocess.run") as run, \
             patch("sys.stdout", stdout):
            notify.announce("⏰ Countdown finished — Tea", "Glass")

        self.assertIn("⏰ Countdown finished — Tea", stdout.getvalue())
        run.assert_called_once_with(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def test_skips_missing_sound(self):
        with patch("notify.os.path.isfile", return_value=False), \
             patch("notify.subprocess.run") as run, \
             patch("sys.stdout", io.StringIO()):
            notify.announce("🔔 Alarm — Wake at 07:30", "Ping")

        run.assert_not_called()

    def test_sound_failure_still_prints(self):
        stdout = io.StringIO()
        with patch("notify.os.path.isfile", return_value=True), \
             patch("notify.subprocess.run", side_effect=OSError), \
             patch("sys.stdout", stdout):
            notify.announce("🔔 Alarm — Wake at 07:30", "Ping")

        self.assertIn("🔔 Alarm — Wake at 07:30", stdout.getvalue())


class CountdownTests(AppTestCase):
    def test_parse_seconds(self):
        cases = {
            "1": 1,
            "60": 60,
            "0005": 5,
            "0": None,
            "00": None,
            "": None,
            "-1": None,
            "1.5": None,
            "abc": None,
            " 5": None,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(countdown._parse_seconds(raw), expected)

    def test_start_rejects_invalid_seconds(self):
        for seconds in (0, -1, True, False, 1.5):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    countdown.start_countdown(seconds, "Tea")
        self.assertEqual(countdown.list_countdowns(), [])

    def test_blank_label_defaults(self):
        first = countdown.start_countdown(30, "")
        second = countdown.start_countdown(30, "   ")
        labels = [item[1] for item in countdown.list_countdowns()]
        self.assertEqual([first, second], [1, 2])
        self.assertEqual(labels, ["Countdown", "Countdown"])

    def test_set_view_and_reject_bad_input(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            with patch("builtins.input", side_effect=["0"]):
                countdown.set_countdown()
            with patch("builtins.input", side_effect=[" 5 ", "  Tea  "]):
                countdown.set_countdown()
            countdown.view_countdowns()

        text = stdout.getvalue()
        self.assertIn("Enter a whole number of seconds greater than 0.", text)
        self.assertIn("Countdown 1 set for 5s.", text)
        self.assertIn("1. Tea - ", text)
        self.assertIn("s left", text)
        listed = countdown.list_countdowns()
        self.assertEqual(listed[0][1], "Tea")
        self.assertGreaterEqual(listed[0][2], 4)
        self.assertLessEqual(listed[0][2], 5)

    def test_view_empty(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            countdown.view_countdowns()
        self.assertIn("No countdowns.", stdout.getvalue())

    def test_delete_removes_without_alert(self):
        countdown.start_countdown(30, "Tea")
        thread = countdown._countdowns[1]["thread"]
        stdout = io.StringIO()
        with patch("countdown.announce") as announce, \
             patch("sys.stdout", stdout), \
             patch("builtins.input", return_value="1"):
            countdown.delete_countdown()

        self.assertIn("Countdown 1 deleted.", stdout.getvalue())
        self.assertEqual(countdown.list_countdowns(), [])
        self.assertFalse(thread.is_alive())
        announce.assert_not_called()

    def test_delete_unknown_id(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", return_value="nope"):
            countdown.delete_countdown()
        self.assertIn("No countdown with that id.", stdout.getvalue())
        self.assertFalse(countdown.remove_countdown(1))

    def test_finish_alerts_once_and_removes_itself(self):
        with patch("countdown.announce") as announce:
            countdown.start_countdown(1, "Eggs")
            self._wait_until(lambda: countdown.list_countdowns() == [])

        announce.assert_called_once_with("⏰ Countdown finished — Eggs", "Glass")

    def test_finished_countdown_leaves_the_other_running(self):
        with patch("countdown.announce") as announce:
            countdown.start_countdown(1, "Eggs")
            countdown.start_countdown(30, "Tea")
            self._wait_until(lambda: len(countdown.list_countdowns()) == 1)

        remaining = countdown.list_countdowns()
        self.assertEqual(remaining[0][1], "Tea")
        announce.assert_called_once_with("⏰ Countdown finished — Eggs", "Glass")

    def test_stop_clears_every_countdown(self):
        countdown.start_countdown(60, "A")
        countdown.start_countdown(60, "B")
        started = time.monotonic()
        countdown.stop_countdowns()
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(countdown.list_countdowns(), [])
        countdown.stop_countdowns()

    def _wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("timed out waiting for countdown")
            time.sleep(0.05)


class AlarmTests(AppTestCase):
    def test_parse_time(self):
        accepted = {
            "07:30": (7, 30),
            "7:30": (7, 30),
            "00:00": (0, 0),
            "23:59": (23, 59),
        }
        rejected = ("", "25:00", "12:60", "7:3", "07:30:00", "noon", "24:00", "007:00")
        for raw, expected in accepted.items():
            with self.subTest(raw=raw):
                self.assertEqual(alarm._parse_time(raw), expected)
        for raw in rejected:
            with self.subTest(raw=raw):
                self.assertIsNone(alarm._parse_time(raw))

    def test_next_target_rolls_to_tomorrow_after_the_minute(self):
        now = datetime(2026, 10, 9, 13, 20, 30)
        self.assertEqual(
            alarm._next_target(14, 5, now),
            datetime(2026, 10, 9, 14, 5, 0),
        )
        self.assertEqual(
            alarm._next_target(13, 20, now),
            datetime(2026, 10, 10, 13, 20, 0),
        )
        self.assertEqual(
            alarm._next_target(0, 0, now),
            datetime(2026, 10, 10, 0, 0, 0),
        )

    def test_start_rejects_invalid_clock_time(self):
        for hour, minute in ((24, 0), (-1, 0), (True, 0), (12, 60), (12, False)):
            with self.subTest(hour=hour, minute=minute):
                with self.assertRaises(ValueError):
                    alarm.start_alarm(hour, minute, "Wake")
        self.assertEqual(alarm.list_alarms(), [])

    def test_set_view_today_and_tomorrow(self):
        class FixedNow(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 9, 13, 20, 30)

        stdout = io.StringIO()
        with patch("alarm.datetime", FixedNow), \
             patch("sys.stdout", stdout), \
             patch("builtins.input", side_effect=["14:00", "Lunch", "13:20", ""]):
            alarm.set_alarm()
            alarm.set_alarm()
            alarm.view_alarms()

        text = stdout.getvalue()
        self.assertIn("Alarm 1 set for 14:00 today.", text)
        self.assertIn("Alarm 2 set for 13:20 tomorrow.", text)
        self.assertIn("1. Lunch - 14:00 - 2370s left", text)
        self.assertIn("2. Alarm - 13:20 - 86370s left", text)

    def test_set_rejects_bad_time_without_asking_for_label(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", side_effect=["25:00"]):
            alarm.set_alarm()

        self.assertIn("Enter a time in HH:MM format.", stdout.getvalue())
        self.assertEqual(alarm.list_alarms(), [])

    def test_view_empty(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            alarm.view_alarms()
        self.assertIn("No alarms.", stdout.getvalue())

    def test_delete_removes_without_alert(self):
        alarm.start_alarm(0, 0, "Wake")
        thread = alarm._alarms[1]["thread"]
        stdout = io.StringIO()
        with patch("alarm.announce") as announce, \
             patch("sys.stdout", stdout), \
             patch("builtins.input", return_value="1"):
            alarm.delete_alarm()

        self.assertIn("Alarm 1 deleted.", stdout.getvalue())
        self.assertEqual(alarm.list_alarms(), [])
        self.assertFalse(thread.is_alive())
        announce.assert_not_called()

    def test_delete_unknown_id(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", return_value="9"):
            alarm.delete_alarm()
        self.assertIn("No alarm with that id.", stdout.getvalue())

    def test_finish_alerts_once_and_removes_itself(self):
        target = datetime.now() + timedelta(seconds=1)
        with patch("alarm.announce") as announce:
            alarm._schedule(target, "Standup")
            self._wait_until(lambda: alarm.list_alarms() == [])

        announce.assert_called_once_with(
            f"🔔 Alarm — Standup at {target.strftime('%H:%M')}",
            "Ping",
        )

    def test_stop_leaves_countdowns_running(self):
        countdown.start_countdown(30, "Tea")
        alarm._schedule(datetime.now() + timedelta(hours=1), "Wake")
        alarm.stop_alarms()
        self.assertEqual(alarm.list_alarms(), [])
        self.assertEqual([item[1] for item in countdown.list_countdowns()], ["Tea"])

    def test_stop_clears_every_alarm(self):
        alarm._schedule(datetime.now() + timedelta(hours=1), "A")
        alarm._schedule(datetime.now() + timedelta(hours=2), "B")
        started = time.monotonic()
        alarm.stop_alarms()
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(alarm.list_alarms(), [])

    def _wait_until(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("timed out waiting for alarm")
            time.sleep(0.05)


class MenuTests(AppTestCase):
    def test_invalid_choice_then_exit(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", side_effect=["nope", "3"]):
            main.main_menu()

        text = stdout.getvalue()
        self.assertIn("PYTHON ALARM CLOCK", text)
        self.assertIn("Invalid choice. Please try again.", text)
        self.assertIn("Goodbye!", text)
        self.assertNotIn("Alarm clock stopped.", text)

    def test_submenus_return_to_main_menu(self):
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", side_effect=["1", "4", "2", "4", "3"]):
            main.main_menu()

        text = stdout.getvalue()
        self.assertIn("ALARM MENU", text)
        self.assertIn("COUNTDOWN MENU", text)
        self.assertIn("Goodbye!", text)

    def test_session_sets_views_and_deletes_both(self):
        answers = [
            "1", "1", "25:99", "1", "7:05", "Wake", "2", "3", "1", "4",
            "2", "1", "nope", "1", "45", "Tea", "2", "3", "1", "4",
            "3",
        ]
        stdout = io.StringIO()
        with patch("sys.stdout", stdout), \
             patch("builtins.input", side_effect=answers):
            main.main_menu()

        text = stdout.getvalue()
        self.assertIn("Enter a time in HH:MM format.", text)
        self.assertRegex(text, r"Alarm 1 set for 07:05 (today|tomorrow)\.")
        self.assertIn("1. Wake - 07:05 - ", text)
        self.assertIn("Alarm 1 deleted.", text)
        self.assertIn("Enter a whole number of seconds greater than 0.", text)
        self.assertIn("Countdown 1 set for 45s.", text)
        self.assertIn("1. Tea - ", text)
        self.assertIn("Countdown 1 deleted.", text)
        self.assertIn("Goodbye!", text)
        self.assertNotIn("⏰", text)
        self.assertNotIn("🔔", text)
        self.assertEqual(alarm.list_alarms(), [])
        self.assertEqual(countdown.list_countdowns(), [])

    def test_script_exit_says_goodbye(self):
        completed = self._run_script("3\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Goodbye!", completed.stdout)
        self.assertNotIn("Alarm clock stopped.", completed.stdout)

    def test_script_eof_stops_cleanly(self):
        completed = self._run_script("")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Alarm clock stopped.", completed.stdout)

    def test_script_interrupt_stops_cleanly(self):
        process = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "main.py")],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.4)
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertIn("Alarm clock stopped.", stdout)

    def _run_script(self, stdin):
        return subprocess.run(
            [sys.executable, "-u", str(ROOT / "main.py")],
            input=stdin,
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()

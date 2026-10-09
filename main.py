from alarm import delete_alarm, set_alarm, stop_alarms, view_alarms
from countdown import delete_countdown, set_countdown, stop_countdowns, view_countdowns


def menu(title, options):
    while True:
        print(f"\n===== {title} =====")
        for key, label in options.items():
            print(f"{key}. {label}")

        choice = input("Enter your choice: ").strip()
        if choice in options:
            return choice

        print("Invalid choice. Please try again.")


def alarm_menu():
    while True:
        choice = menu("ALARM MENU", {
            "1": "Set Alarm",
            "2": "View Alarms",
            "3": "Delete Alarm",
            "4": "Back to Main Menu",
        })
        if choice == "1":
            set_alarm()
        elif choice == "2":
            view_alarms()
        elif choice == "3":
            delete_alarm()
        elif choice == "4":
            return


def countdown_menu():
    while True:
        choice = menu("COUNTDOWN MENU", {
            "1": "Set Countdown",
            "2": "View Countdowns",
            "3": "Delete Countdown",
            "4": "Back to Main Menu",
        })
        if choice == "1":
            set_countdown()
        elif choice == "2":
            view_countdowns()
        elif choice == "3":
            delete_countdown()
        elif choice == "4":
            return


def main_menu():
    while True:
        choice = menu("PYTHON ALARM CLOCK", {
            "1": "Alarm",
            "2": "Countdown",
            "3": "Exit",
        })

        if choice == "1":
            alarm_menu()
        elif choice == "2":
            countdown_menu()
        elif choice == "3":
            stop_alarms()
            stop_countdowns()
            print("Goodbye!")
            return


if __name__ == "__main__":
    try:
        main_menu()
    except (KeyboardInterrupt, EOFError):
        stop_alarms()
        stop_countdowns()
        print("\nAlarm clock stopped.")

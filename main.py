"""Application entry point for the MODI Brain Lab prototype."""

from __future__ import annotations

import argparse

from tasks.task1_reaction import run_task1
from tasks.task2_memory import run_task2


def main() -> None:
    parser = argparse.ArgumentParser(description="MODI Brain Lab")
    parser.add_argument("--participant-id", default="P001", help="Anonymous participant ID")
    parser.add_argument("--task", default="task1", choices=["task1", "task2"], help="Task to run")
    args = parser.parse_args()

    if args.task == "task1":
        run_task1(args.participant_id)
    elif args.task == "task2":
        run_task2(args.participant_id)


if __name__ == "__main__":
    main()

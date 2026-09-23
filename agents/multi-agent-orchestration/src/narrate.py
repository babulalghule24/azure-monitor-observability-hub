"""Presentation layer for the lab.

The framework emits raw event objects. That is fine for debugging and useless for
teaching. This module turns a run into something a room can follow:

    * a header saying WHICH step this is and WHAT it adds
    * each agent's turn, clearly attributed and readable
    * a closing "what just happened" with the point of the step

Import it in a step file and the story tells itself.
"""

import os
import shutil
import textwrap

WIDTH = min(shutil.get_terminal_size((100, 24)).columns, 100)
PLAIN = os.environ.get("LAB_PLAIN") == "1"          # set to 1 to disable colour


class C:
    """Minimal ANSI. Windows Terminal and VS Code handle these fine."""
    HEAD = "" if PLAIN else "\033[1;36m"     # bright cyan
    AGENT = "" if PLAIN else "\033[1;33m"    # bright yellow
    OK = "" if PLAIN else "\033[1;32m"       # green
    DIM = "" if PLAIN else "\033[2m"
    BOLD = "" if PLAIN else "\033[1m"
    OFF = "" if PLAIN else "\033[0m"


def _wrap(text: str, indent: str = "  ") -> str:
    out = []
    for para in str(text).split("\n"):
        if not para.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(para, width=WIDTH - len(indent),
                                 initial_indent=indent, subsequent_indent=indent,
                                 replace_whitespace=False, drop_whitespace=False)
                   or [indent])
    return "\n".join(out)


def step_header(number: int, title: str, adds: str, watch_for: str = "") -> None:
    """Open a step. Say what it is and what it adds - before anything runs."""
    bar = "=" * WIDTH
    print(f"\n{C.HEAD}{bar}")
    print(f"  STEP {number}  ·  {title}")
    print(f"{bar}{C.OFF}")
    print(f"\n{C.BOLD}  What this adds{C.OFF}")
    print(_wrap(adds, "    "))
    if watch_for:
        print(f"\n{C.BOLD}  Watch for{C.OFF}")
        print(_wrap(watch_for, "    "))
    print(f"\n{C.DIM}  running...{C.OFF}\n")


def turn(speaker: str, text: str, note: str = "") -> None:
    """One agent's contribution, attributed and readable."""
    bar = "-" * WIDTH
    print(f"\n{C.AGENT}{bar}")
    print(f"  {speaker.upper()}" + (f"   {C.DIM}({note}){C.OFF}{C.AGENT}" if note else ""))
    print(f"{bar}{C.OFF}")
    print(_wrap(text, "  "))


def event(label: str, detail: str = "") -> None:
    """A protocol or control-flow moment worth calling out mid-run."""
    print(f"\n{C.DIM}  >> {label}" + (f": {detail}" if detail else "") + f"{C.OFF}")


def takeaway(*points: str) -> None:
    """Close the step. This is the line the room should leave with."""
    bar = "=" * WIDTH
    print(f"\n{C.OK}{bar}")
    print("  WHAT JUST HAPPENED")
    print(f"{bar}{C.OFF}")
    for p in points:
        print(_wrap(f"• {p}", "  "))
    print()


def ask(*questions: str) -> None:
    """Check-your-understanding prompts, for the learner working alone."""
    print(f"{C.DIM}  Check your understanding:{C.OFF}")
    for q in questions:
        print(_wrap(f"? {q}", "    "))
    print()

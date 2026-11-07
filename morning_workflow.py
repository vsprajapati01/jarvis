#!/usr/bin/env python3
"""
Jarvis morning workflow - what runs on a double clap.
Keeps it short and useful for Vishal: time, weather, today's focus,
and the top jobs still waiting for his click.

Sunday Nov 8 plan is in here (training, job applications, finish the
last PL-300 visualization module, then exam practice) because that is
his agreed plan for that day. Other days use the normal pattern:
training 10:45am, job applications in the free window before 4:30pm
(Friday 3pm), PL-300 self-study where stuck.
"""
import datetime

import jarvis as core

TOP_JOBS = [
    "Terrakotta - Software Engineer, Product New Grad, Seattle, $130-150K (resume ready)",
    "Jerry.ai - Associate Data Scientist, Remote, $110-140K (resume ready)",
    "IBM - Associate Data Scientist 2027, New York, $88,800-133,200",
    "Palantir - Forward Deployed Engineer, New Grad, New York (form filled, needs your submit click)",
]


def morning_briefing(now=None):
    now = now or datetime.datetime.now()
    day = now.strftime("%A")
    weather = core.get_weather("Gainesville")

    if day == "Sunday":
        focus = ("Today is Sunday. Training, then job applications, "
                 "finish the last PL-300 visualization module, then PL-300 exam practice.")
    elif day == "Friday":
        focus = ("Today is Friday. Free window until 3pm, then your shift 3pm to midnight. "
                 "Use the morning for job applications.")
    else:
        focus = ("Training at 10:45am, job applications in your free window "
                 "before 4:30pm, PL-300 study where you get stuck.")

    lines = [
        f"Good morning. It is {now.strftime('%A, %B %d, %I:%M %p')}.",
        weather,
        focus,
        "Top jobs waiting for your click:",
    ]
    lines += [f"- {job}" for job in TOP_JOBS]
    return "\n".join(lines)


def run_morning_workflow():
    """Speak + print the briefing. Returns the briefing text."""
    text = morning_briefing()
    core.speak(text)
    return text


if __name__ == "__main__":
    print(run_morning_workflow())

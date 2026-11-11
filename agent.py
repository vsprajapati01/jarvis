#!/usr/bin/env python3
"""
Jarvis v8 - the agent loop. Talk normally, Jarvis decides what to do.

This is the part that makes Jarvis feel like ChatGPT / Gemini with
hands, instead of a list of rigid commands.

When Vishal talks normally, the loop decides, in this order:

  1. CRITICAL?  submit / send / pay / delete / shutdown / restart /
     sign in / share personal details.
     -> NEVER done silently. Jarvis asks first, through
     permissions.py. Even after a yes, Jarvis only does the safe
     part that already exists (open the site in his own Chrome) -
     the submit / send / pay / delete click itself stays his.
     Jarvis never stores or types a password.
  2. TASK?  A thing to do on his PC, in plain words:
     "open youtube for me", "set a timer for 5 minutes",
     "make a word document about...", "find companies hiring
     data analysts", "what is the weather in Tampa",
     "remind me to drink water in 10 minutes", "save a note",
     "give me my morning briefing".
     -> The loop turns it into the matching command Jarvis
     already knows, and runs it with the existing code in
     jarvis.py / find_companies.py / create_docs.py /
     research.py / morning_workflow.py. No new PC actions
     are invented here - if Jarvis cannot do it, it says so.
  3. RESEARCH?  "research X", "look up X", "find out about X",
     "what is the latest on X", or a question about something
     current (news, 2026, jobs, prices).
     -> research.py searches the web FIRST, then the brain
     answers in short plain words from what it found, and
     says which sources it used. It does not answer from
     its own knowledge alone when the facts are current.
  4. CHAT?  Everything else - questions, explanations,
     "how do I...", "tell me more", "make it shorter",
     "give me an example", or just talking.
     -> The brain answers, short and plain, step by step
     for how-to questions. The last 6 turns are remembered
     (brain.py), so follow-ups work.

No brain key is needed for steps 1 and 2 - local tasks and the
safety check work offline. Steps 3 and 4 need a brain key in
.env (Gemini / Groq / Cerebras / OpenRouter free, see brain.py).
If no brain is set up, research still returns the real search
results, and chat says honestly that no brain is set up yet.

Usage from jarvis.py:
    from agent import route
    route(command, execute_fn, speak_fn)   # True if handled

    # Critical flow: route() proposes (ask first, via the
    # permissions.py gate), jarvis.py collects the yes/no
    # (typed in text mode, spoken in voice mode), then calls
    # confirm_pending(answer=True/False). confirm_pending(answer=None)
    # asks interactively through permissions.ask_permission().
"""
import re

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_FILLERS = (
    r"(?:hey jarvis[,.]?\s*)?"
    r"(?:please\s+)?"
    r"(?:can you\s+|could you\s+|would you\s+|will you\s+)?"
)


def _clean(text):
    """Lowercase, drop wake word / politeness, keep the meaning."""
    t = text.strip().lower()
    t = re.sub(r"^(hey|hi|hello)\s+jarvis[,.]?\s*", "", t)
    t = re.sub(r"^jarvis[,.]?\s*", "", t)
    t = re.sub(r"^(please\s+)?(can you|could you|would you|will you)\s+", "", t)
    t = re.sub(r"\s+(for me|please)$", "", t)
    t = t.strip(" .")
    return t


def _strip_filler(text):
    return _clean(text)


# ------------------------------------------------------------------
# 1. Critical actions - gated by permissions.py, never silent
# ------------------------------------------------------------------

_PENDING = None          # (action_text, kind) awaiting a yes/no


def has_pending():
    return _PENDING is not None


def pending_action():
    return _PENDING[0] if _PENDING else ""


def _detect_critical(text):
    """Return a short label for the critical action, or '' if none.
    Uses permissions.is_critical() as the gate - this file does not
    invent its own list of dangerous words."""
    try:
        from permissions import is_critical
    except Exception:
        return ""
    if not is_critical(text):
        return ""
    t = text.lower()
    if "submit" in t or "apply" in t:
        return "submit a job application"
    if "send" in t:
        return "send an email or a message"
    if "pay" in t or "buy" in t or "purchase" in t:
        return "pay for something"
    if "delete" in t or "remove" in t and "file" in t:
        return "delete a file"
    if "shutdown" in t or "shut down" in t or "restart" in t or "reboot" in t:
        return "shut down or restart the PC"
    if "sign in" in t or "log in" in t or "login" in t:
        return "sign in to a site"
    if "share my" in t:
        return "share your personal details"
    return "a critical action"


def _safe_prep_for_critical(label, text):
    """The only safe part Jarvis may do after a yes, using actions
    that already exist. Returns (prep_command_or_None, note)."""
    t = text.lower()
    if label == "submit a job application":
        # Open the site in his own Chrome; the submit click stays his.
        m = re.search(r"(?:to|at|on)\s+([a-z0-9][a-z0-9.\-]+\.[a-z]{2,})", t)
        site = m.group(1) if m else None
        if site:
            return site, "I will open it in your browser. The submit click is yours - I never submit anything by myself."
        return None, "You said yes, but you did not name a site to open. Tell me the site, or open it yourself - the submit click is yours, I never submit anything by myself."
    if label == "send an email or a message":
        return "gmail.com", "I will open Gmail in your browser. You write and send it yourself - I never send anything by myself."
    if label == "sign in to a site":
        m = re.search(r"(?:to|at|on)\s+([a-z0-9][a-z0-9.\-]+\.[a-z]{2,})", t)
        site = m.group(1) if m else None
        if site:
            return site, "I will open the site in your browser. You sign in yourself there - I never store or type passwords."
        return None, "You said yes, but you did not name a site. Tell me which site, or open it yourself - I never store or type passwords."
    # pay / delete / shutdown / restart / share details: no safe prep.
    return None, "I cannot do that step for you. It needs your own click, and I never do it silently."


def propose_critical(text):
    """Store the critical request and ask first. Returns the message
    Jarvis should speak. Nothing is executed here."""
    global _PENDING
    label = _detect_critical(text)
    _PENDING = (text.strip(), label)
    return (
        f"That is a critical step - {label} - so I need your permission first. "
        f"Say yes to go ahead with the safe part only, or no to stop. "
        f"I will never submit, send, pay, delete, shut down, sign in, "
        f"or share your details by myself."
    )


def cancel_pending():
    """Drop a pending critical request without doing anything."""
    global _PENDING
    _PENDING = None


def confirm_pending(answer=None):
    """Confirm (or decline) a pending critical request.
    `answer=True` means Vishal already said yes to the proposal
    (the proposal IS the ask - it happens in propose_critical,
    and the yes/no is collected by jarvis.py's main loop, typed
    or spoken). `answer=False` means he said no.
    `answer=None` means nobody asked yet: ask interactively
    through permissions.ask_permission().
    Returns (did_go_ahead, message). On yes, only the safe prep
    (if any) is returned as a command for jarvis.py to run -
    the critical part itself is never run. On no, the message
    is "" because the caller already says it stopped."""
    global _PENDING
    if _PENDING is None:
        return False, ""
    text, label = _PENDING
    _PENDING = None
    if answer is None:
        try:
            from permissions import ask_permission
            ok = ask_permission(f"{label}: {text}")
        except Exception:
            ok = False
        if not ok:
            # ask_permission already printed that it stopped.
            return False, ""
    else:
        ok = bool(answer)
    if not ok:
        return False, ""
    prep, note = _safe_prep_for_critical(label, text)
    if prep:
        return True, note + " __PREP__:" + prep
    return True, note


# ------------------------------------------------------------------
# 2. Task detection - plain words -> a command Jarvis already knows
# ------------------------------------------------------------------

def _normalise_task(text):
    """Return the rigid command for a plain-words task, or ''.
    Only maps to actions that already exist in jarvis.py."""
    t = _clean(text)

    # Morning briefing
    if re.search(r"(morning briefing|morning workflow|start my day|good morning)", t):
        return "morning briefing"

    # Open an app or a website
    m = re.match(r"(?:open|launch|go to|show)\s+(.+)$", t)
    if m:
        target = m.group(1).strip()
        if target in ("chrome", "vs code", "notepad", "calculator"):
            return "open " + target
        # "open youtube" -> youtube.com; "open youtube.com" stays as is
        if " " not in target:
            if "." not in target:
                target = target + ".com"
            return "open " + target
        return "open " + target

    # Weather
    m = re.match(r"(?:what(?:'s| is) the weather(?: in| for)?|weather)\s*(.*)$", t)
    if m and ("weather" in t):
        city = m.group(1).strip() or "Gainesville"
        city = re.sub(r"\s+(today|tomorrow|now)$", "", city)
        return "weather " + city

    # Time / date
    if re.match(r"what(?:'s| is) the time", t) or t in ("time", "tell me the time"):
        return "time"
    if re.match(r"what(?:'s| is) (?:the )?date|what day is it", t) or t == "date":
        return "date"

    # Timer / reminder
    if t.startswith("timer") or re.match(r"set (?:a )?timer", t):
        m2 = re.search(r"(\d+)\s*(hours?|minutes?|mins?|seconds?|secs?)", t)
        if m2:
            return "timer " + m2.group(0)
        return "timer"
    if t.startswith("remind me to") or re.match(r"remind me", t):
        return t if t.startswith("remind me to") else "remind me to " + t[len("remind me"):].strip()

    # Note
    m = re.match(r"(?:save|take|write down)(?: a)? note(?: that|:)?\s+(.+)$", t)
    if m:
        return "note " + m.group(1).strip()
    if t.startswith("note "):
        return t

    # Find companies / jobs
    if re.search(r"find (companies|jobs)", t):
        return t
    m = re.match(r"(?:look for|find)\s+(.+?)\s+(jobs|companies).*$", t)
    if m:
        return "find companies " + m.group(1).strip()

    # Create Word / PDF
    m = re.match(r"(?:make|create)(?: a)? (word|pdf)(?: (?:document|file))?(?: (?:about|called|named|titled))?\s+(.+)$", t)
    if m:
        kind, rest = m.group(1), m.group(2).strip()
        if ":" in rest:
            title, _, body = rest.partition(":")
        else:
            title, body = rest, "Created by Jarvis."
        return f"create {kind} {title.strip()} : {body.strip()}"

    # Web search
    m = re.match(r"search (?:the web )?(?:for )?(.+)$", t)
    if m:
        return "search " + m.group(1).strip()

    # God's Eye View
    if "god" in t and "eye" in t:
        return "open gods eye"
    if re.search(r"show (flights|ships|satellites|earthquakes)", t):
        return t

    return ""


# ------------------------------------------------------------------
# 3. Research detection
# ------------------------------------------------------------------

_RESEARCH_WORDS = (
    "research", "look up", "look into", "find out about",
    "find out what", "what is the latest", "what's the latest",
    "latest news", "what is happening", "what's happening",
    "search the web for",
)


def _detect_research(text):
    """Return the topic to research, or ''."""
    t = _clean(text)
    for phrase in _RESEARCH_WORDS:
        if t.startswith(phrase):
            topic = t[len(phrase):].strip(" :")
            topic = re.sub(r"^(about|on|for)\s+", "", topic)
            topic = re.sub(r"\s+and tell me.*$", "", topic)
            if topic:
                return topic
    # "tell me about X" + current words -> research, not just chat
    if re.search(r"\b(latest|news|current|2026|2025|price|hiring|deadline)\b", t):
        m = re.match(r"(?:tell me about|what is|what are|who is)\s+(.+)$", t)
        if m:
            return m.group(1).strip()
    return ""


def research_and_answer(topic):
    """Search first (research.py), then let the brain summarise
    what was found in short plain words, naming its sources.
    Works even with no brain key - then the raw results are
    returned instead of a brain summary."""
    topic = topic.strip()
    if not topic:
        return "Tell me what to research, like: research Anthropic residency program"
    try:
        from research import research as do_research
        summary, _filename, err = do_research(topic)
    except Exception as e:
        return f"Could not research that right now: {e}"
    if err:
        return err
    # summary already lists titles + source links; hand it to the brain
    # so the answer is short and plain, not a raw list.
    try:
        from brain import summarise_research
        answer, err2 = summarise_research(topic, summary)
        if err2 is None and answer:
            return answer
        # No brain / brain failed: fall back to the real results.
        return summary
    except Exception:
        return summary


# ------------------------------------------------------------------
# 4. Chat / follow-ups
# ------------------------------------------------------------------

_FOLLOWUPS = (
    "tell me more", "more detail", "more details", "go on",
    "make it shorter", "shorter", "make it simpler", "simpler",
    "give me an example", "give an example", "an example",
    "what do you mean", "explain that", "explain again",
    "and then", "continue",
)


def _is_followup(text):
    t = _clean(text)
    return t in _FOLLOWUPS or t.startswith("tell me more") or t.startswith("give me an example")


def chat_answer(text):
    """Normal conversation through the brain, with history.
    Returns (answer, error_or_None)."""
    try:
        from brain import ask_brain
    except Exception as e:
        return "", f"Brain unavailable: {e}"
    return ask_brain(text.strip())


# ------------------------------------------------------------------
# Main entry: decide, then act
# ------------------------------------------------------------------

def classify(text):
    """Return (kind, data). kind is one of:
    'critical', 'task', 'research', 'chat'."""
    if not text or not text.strip():
        return "chat", {}
    if _detect_critical(text):
        return "critical", {"label": _detect_critical(text)}
    topic = _detect_research(text)
    if topic:
        return "research", {"topic": topic}
    cmd = _normalise_task(text)
    if cmd:
        return "task", {"command": cmd}
    return "chat", {}


def route(text, execute_fn, speak_fn):
    """Decide what plain-words input means and do it.
    execute_fn(command) runs a rigid jarvis.py command and returns
    True to keep listening. speak_fn(text) speaks/prints.
    Returns True if handled (jarvis.py should not fall through to
    the old brain fallback), False if not handled."""
    # v9: PC control first - type / search / open Chrome / stop.
    # This is the "touch anything" layer: keyboard + mouse, watched.
    try:
        from pc_control import PCControl, handle_pc_command
        _pc = getattr(route, "_pc", None)
        if _pc is None:
            # Dry-run by default here - live only on his Windows PC
            # with the screen on, after he says go live.
            _pc = PCControl(dry_run=True)
            route._pc = _pc
        handled, reply = handle_pc_command(text, _pc)
        if handled:
            speak_fn(reply)
            return True
    except Exception:
        pass
    kind, data = classify(text)
    if kind == "critical":
        speak_fn(propose_critical(text))
        return True
    if kind == "task":
        cmd = data["command"]
        if cmd == "morning briefing":
            try:
                from morning_workflow import run_morning_workflow
                run_morning_workflow()
            except Exception as e:
                speak_fn(f"Could not run the morning briefing: {e}")
            return True
        execute_fn(cmd)
        return True
    if kind == "research":
        speak_fn(research_and_answer(data["topic"]))
        return True
    # chat (includes follow-ups - history in brain.py handles them)
    answer, err = chat_answer(text)
    speak_fn(err or answer)
    return True

"""Wake-word gating: detect keyword, split off the command that follows it."""


def detect(text, wake_words):
    """Return (matched_keyword, command_after_keyword) or (None, text)."""
    low = text.lower()
    for kw in wake_words:
        k = kw.lower()
        idx = low.find(k)
        if idx != -1:
            cmd = text[idx + len(k):].strip(" .,!?")
            return kw, cmd
    return None, text


def is_command_empty(cmd):
    return not cmd or len(cmd.split()) < 1

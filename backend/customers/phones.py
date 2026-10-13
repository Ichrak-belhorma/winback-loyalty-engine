import re

_NON_DIGITS = re.compile(r"\D")


def normalize_phone(raw: str) -> str:
    """E.164-ish: '+' and digits; bare 10-digit numbers are assumed to be US (+1)."""
    digits = _NON_DIGITS.sub("", raw or "")
    if not digits:
        return ""
    if len(digits) == 10 and not raw.strip().startswith("+"):
        digits = "1" + digits
    return "+" + digits

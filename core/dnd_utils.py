"""D&D 5e utility helpers (CR, proficiency bonus, etc.)."""


def parse_cr_to_float(cr) -> float:
    """
    Parse challenge rating to a numeric value.
    Accepts: int, float, or str like "1/2", "1/4", "2", "17 (18,000 XP)".
    Returns 0.0 if unparseable.
    """
    if cr is None:
        return 0.0
    if isinstance(cr, (int, float)):
        return max(0.0, float(cr))
    s = str(cr).strip()
    if not s:
        return 0.0
    # Strip parenthetical XP part if present, e.g. "17 (18,000 XP)"
    if "(" in s:
        s = s.split("(")[0].strip()
    # Fractional CR: "1/2", "1/4"
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                if den != 0:
                    return max(0.0, num / den)
            except (ValueError, TypeError):
                pass
        return 0.0
    try:
        return max(0.0, float(s))
    except (ValueError, TypeError):
        return 0.0


def proficiency_bonus_from_cr(cr) -> int:
    """
    Return proficiency bonus for a given challenge rating (D&D 5e table).
    CR 0–4   → +2
    CR 5–8   → +3
    CR 9–12  → +4
    CR 13–16 → +5
    CR 17–20 → +6
    CR 21–24 → +7
    CR 25–28 → +8
    CR 29–30 → +9
    """
    value = parse_cr_to_float(cr)
    if value <= 4:
        return 2
    if value <= 8:
        return 3
    if value <= 12:
        return 4
    if value <= 16:
        return 5
    if value <= 20:
        return 6
    if value <= 24:
        return 7
    if value <= 28:
        return 8
    if value <= 30:
        return 9
    # CR 30+ use +9 (same as 29-30)
    return 9

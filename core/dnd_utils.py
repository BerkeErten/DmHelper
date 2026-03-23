"""D&D 5e utility helpers (CR, proficiency bonus, etc.)."""
import math

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


def calculate_initiative_from_ability_score(ability_score: int, proficiency_bonus: int = 0, bonus_modifier: int = 0) -> int:
    """
    Calculate initiative based on ability score (DEX modifier + optional proficiency and bonus).
    """
    base_initiative = (ability_score - 10) // 2
    return base_initiative + proficiency_bonus + bonus_modifier


# Alias for backward compatibility
calculate_initiative = calculate_initiative_from_ability_score


def calculate_jump_distance_us(
    strength_score: int,
    dexterity_score: int,
    height_in_feet: int,
    height_in_inches: int,
    *,
    is_tiger_barbarian: bool = False,
    is_remarkable_athlete: bool = False,
    is_step_of_the_wind: bool = False,
    is_jump_spell: bool = False,
    is_boots_of_striding_and_spring: bool = False,
    is_athlete_feat: bool = False,
    is_second_story: bool = False,
) -> dict:
    """Calculate D&D 5e jump distances (long jump, high jump, reach). Returns a dict of feet values.

    Jump distance calculation logic based on Fexlabs.
    """
    # TODO: implement stacking rules (e.g. Jump + Step of the Wind)
    str_mod = (strength_score - 10) // 2
    dex_mod = (dexterity_score - 10) // 2
    height = height_in_feet + height_in_inches / 12
    
    lateLongMod = 0
    lateHighMod = 0
    runningLongMod = 0
    runningHighMod = 0
    globalMultiplier = 1
    
    if is_tiger_barbarian:
        lateLongMod += 10
        lateHighMod += 3
    if is_remarkable_athlete:
        runningLongMod += str_mod
    if is_step_of_the_wind:
        globalMultiplier *= 2
    if is_jump_spell:
        globalMultiplier *= 3
    if is_boots_of_striding_and_spring:
        globalMultiplier *= 3
    """
    if is_athlete_feat:
        info = 5 feet of movement
    else:
        info = 10 feet of movement
    """
    if is_second_story:
        runningLongMod += dex_mod
        runningHighMod += dex_mod
    
    run_horizontal = globalMultiplier * (strength_score +lateLongMod +runningLongMod)
    stand_horizontal = globalMultiplier * (strength_score*0.5 +lateLongMod)
    obstacle = globalMultiplier * ((strength_score *2.5)/10)
    run_vertical = globalMultiplier * (3 + str_mod + lateHighMod + runningHighMod)
    stand_vertical = globalMultiplier * ((3 + str_mod)/2 + lateHighMod)
    run_grab = math.floor((globalMultiplier * (3+str_mod + lateHighMod +runningHighMod) + height*1.5)*10)/10
    stand_grab = math.floor(((globalMultiplier * (3+str_mod)/2 + lateHighMod) + height*1.5)*10)/10    
    
    return {
        "run_horizontal": run_horizontal,
        "stand_horizontal": stand_horizontal,
        "obstacle": obstacle,
        "run_vertical": run_vertical,
        "stand_vertical": stand_vertical,
        "run_grab": run_grab,
        "stand_grab": stand_grab
    }
def main():
    print(calculate_jump_distance_us(18, 14, 6, 0, is_tiger_barbarian=True, is_remarkable_athlete=True, is_step_of_the_wind=True, is_jump_spell=True, is_boots_of_striding_and_spring=True, is_athlete_feat=True, is_second_story=True))

if __name__ == "__main__":
    main()
"""Dice rolling engine for DM Helper."""
import random
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RollResult:
    """Result of a dice roll."""
    expression: str
    rolls: List[Tuple[int, List[int]]]  # (sides, [individual rolls])
    modifier: int
    total: int
    details: str
    
    def __str__(self):
        return f"{self.expression} = {self.total}"


class DiceRoller:
    """Dice rolling engine supporting standard D&D notation."""
    
    # Regex pattern for dice notation: XdY+Z or XdY-Z or XdYkhN or XdYklN
    DICE_PATTERN = re.compile(r'(\d+)d(\d+)(?:kh(\d+)|kl(\d+))?([+-]\d+)?', re.IGNORECASE)
    
    @staticmethod
    def roll(expression: str) -> Optional[RollResult]:
        """
        Roll dice based on expression.
        
        Supports formats like:
        - 1d20
        - 2d6+3
        - 3d8-2
        - d20 (assumes 1d20)
        - 2d20kh1 (keep highest 1 - advantage)
        - 2d20kl1 (keep lowest 1 - disadvantage)
        - 4d6kh3 (keep highest 3 - ability scores)
        """
        expression = expression.strip().lower().replace(' ', '')
        
        # Handle "d20" as "1d20"
        if expression.startswith('d') and not expression[1:2].isalpha():
            expression = '1' + expression
        
        # Try to match the pattern
        match = DiceRoller.DICE_PATTERN.match(expression)
        if not match:
            return None
        
        num_dice = int(match.group(1))
        num_sides = int(match.group(2))
        keep_high = int(match.group(3)) if match.group(3) else None
        keep_low = int(match.group(4)) if match.group(4) else None
        modifier_str = match.group(5) or '+0'
        modifier = int(modifier_str)
        
        # Validate
        if num_dice < 1 or num_dice > 100:
            return None
        if num_sides < 2 or num_sides > 1000:
            return None
        
        # Roll the dice
        rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
        
        # Handle keep highest/lowest
        if keep_high is not None:
            if keep_high < 1 or keep_high > num_dice:
                return None
            sorted_rolls = sorted(rolls, reverse=True)
            kept_rolls = sorted_rolls[:keep_high]
            dropped_rolls = sorted_rolls[keep_high:]
            total = sum(kept_rolls) + modifier
            
            # Create details string with dropped dice
            kept_str = ' + '.join(map(str, kept_rolls))
            if dropped_rolls:
                dropped_str = ', '.join(map(str, dropped_rolls))
                base_details = f"({kept_str}) [dropped: {dropped_str}]"
            else:
                base_details = f"({kept_str})"
                
        elif keep_low is not None:
            if keep_low < 1 or keep_low > num_dice:
                return None
            sorted_rolls = sorted(rolls)
            kept_rolls = sorted_rolls[:keep_low]
            dropped_rolls = sorted_rolls[keep_low:]
            total = sum(kept_rolls) + modifier
            
            # Create details string with dropped dice
            kept_str = ' + '.join(map(str, kept_rolls))
            if dropped_rolls:
                dropped_str = ', '.join(map(str, dropped_rolls))
                base_details = f"({kept_str}) [dropped: {dropped_str}]"
            else:
                base_details = f"({kept_str})"
        else:
            # Normal roll
            total = sum(rolls) + modifier
            rolls_str = ' + '.join(map(str, rolls))
            base_details = f"({rolls_str})"
        
        # Add modifier to details
        if modifier > 0:
            details = f"{base_details} + {modifier}"
        elif modifier < 0:
            details = f"{base_details} - {abs(modifier)}"
        else:
            details = base_details
        
        return RollResult(
            expression=expression,
            rolls=[(num_sides, rolls)],
            modifier=modifier,
            total=total,
            details=details
        )
    
    @staticmethod
    def roll_with_advantage() -> Tuple[int, int, int]:
        """Roll 2d20 and return (roll1, roll2, higher)."""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        return roll1, roll2, max(roll1, roll2)
    
    @staticmethod
    def roll_with_disadvantage() -> Tuple[int, int, int]:
        """Roll 2d20 and return (roll1, roll2, lower)."""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        return roll1, roll2, min(roll1, roll2)
    
    @staticmethod
    def roll_ability_score() -> Tuple[int, List[int]]:
        """Roll 4d6 and drop the lowest (for ability scores)."""
        rolls = sorted([random.randint(1, 6) for _ in range(4)])
        dropped = rolls[0]
        kept = rolls[1:]
        total = sum(kept)
        return total, rolls
    
    @staticmethod
    def roll_multiple(expression: str, count: int) -> List[RollResult]:
        """Roll the same expression multiple times."""
        results = []
        for _ in range(min(count, 20)):  # Limit to 20 rolls
            result = DiceRoller.roll(expression)
            if result:
                results.append(result)
        return results


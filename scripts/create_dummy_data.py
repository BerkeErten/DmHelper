"""Create dummy data for testing the stat block editor and data manager."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import DatabaseManager, init_database
from models.entity import Entity
from models.entity_property import EntityProperty
from models.entity_section import EntitySection
from datetime import datetime


def create_dummy_entities():
    """Create sample entities with properties and sections."""
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    with DatabaseManager() as db:
        # 1. Adult Red Dragon (Creature)
        print("\n1. Creating Adult Red Dragon...")
        dragon = Entity(
            type="creature",
            name="Adult Red Dragon"
        )
        db.add(dragon)
        db.flush()
        
        # Dragon properties
        dragon_props = [
            ("ac", "19"),
            ("hp", "256 (19d12 + 133)"),
            ("speed", '["40 ft", "Climb 40 ft", "Fly 80 ft"]'),
            ("str", "27 (+8)"),
            ("dex", "10 (+0)"),
            ("con", "25 (+7)"),
            ("int", "16 (+3)"),
            ("wis", "13 (+1)"),
            ("cha", "23 (+6)"),
            ("skills", "Perception +13, Stealth +6"),
            ("damage_immunities", "Fire"),
            ("senses", "Blindsight 60 ft., Darkvision 120 ft., Passive Perception 23"),
            ("languages", "Common, Draconic"),
            ("challenge_rating", "17 (18,000 XP)"),
            ("proficiency_bonus", "+6"),
        ]
        
        for key, value in dragon_props:
            prop = EntityProperty(entity_id=dragon.id, key=key, value=value)
            db.add(prop)
        
        # Dragon sections
        dragon_sections = [
            {
                "section_type": "traits",
                "sort_order": 1,
                "content": """**Legendary Resistance (3/Day, or 4/Day in Lair).** If the dragon fails a saving throw, it can choose to succeed instead."""
            },
            {
                "section_type": "actions",
                "sort_order": 2,
                "content": """**Multiattack.** The dragon makes three Rend attacks. It can replace one attack with a use of Spellcasting to cast Scorching Ray.

**Rend.** *Melee Weapon Attack:* +14 to hit, reach 10 ft., one target. *Hit:* 13 (1d10 + 8) slashing damage plus 5 (2d4) fire damage.

**Fire Breath (Recharge 5-6).** The dragon exhales fire in a 60-foot cone. Each creature in that area must make a DC 21 Dexterity saving throw, taking 59 (17d6) fire damage on a failed save, or half as much damage on a successful one."""
            },
            {
                "section_type": "legendary_actions",
                "sort_order": 3,
                "content": """The dragon can take 3 legendary actions, choosing from the options below.

**Commanding Presence.** The dragon uses Spellcasting to cast Command (2nd level).

**Fiery Rays.** The dragon uses Spellcasting to cast Scorching Ray.

**Pounce.** The dragon moves up to half its Speed, and it makes one Rend attack."""
            }
        ]
        
        for section_data in dragon_sections:
            section = EntitySection(
                entity_id=dragon.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {dragon.id}")
        
        # 2. Goblin Warrior (Creature)
        print("\n2. Creating Goblin Warrior...")
        goblin = Entity(
            type="creature",
            name="Goblin Warrior"
        )
        db.add(goblin)
        db.flush()
        
        goblin_props = [
            ("ac", "15 (Leather Armor, Shield)"),
            ("hp", "7 (2d6)"),
            ("speed", "30 ft."),
            ("str", "8 (-1)"),
            ("dex", "14 (+2)"),
            ("con", "10 (+0)"),
            ("int", "10 (+0)"),
            ("wis", "8 (-1)"),
            ("cha", "8 (-1)"),
            ("skills", "Stealth +6"),
            ("senses", "Darkvision 60 ft., Passive Perception 9"),
            ("languages", "Common, Goblin"),
            ("challenge_rating", "1/4 (50 XP)"),
        ]
        
        for key, value in goblin_props:
            prop = EntityProperty(entity_id=goblin.id, key=key, value=value)
            db.add(prop)
        
        goblin_sections = [
            {
                "section_type": "traits",
                "sort_order": 1,
                "content": """**Nimble Escape.** The goblin can take the Disengage or Hide action as a bonus action on each of its turns."""
            },
            {
                "section_type": "actions",
                "sort_order": 2,
                "content": """**Scimitar.** *Melee Weapon Attack:* +4 to hit, reach 5 ft., one target. *Hit:* 5 (1d6 + 2) slashing damage.

**Shortbow.** *Ranged Weapon Attack:* +4 to hit, range 80/320 ft., one target. *Hit:* 5 (1d6 + 2) piercing damage."""
            }
        ]
        
        for section_data in goblin_sections:
            section = EntitySection(
                entity_id=goblin.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {goblin.id}")
        
        # 3. Gandalf the Grey (NPC)
        print("\n3. Creating Gandalf the Grey (NPC)...")
        gandalf = Entity(
            type="npc",
            name="Gandalf the Grey"
        )
        db.add(gandalf)
        db.flush()
        
        gandalf_props = [
            ("race", "Maia (Wizard)"),
            ("alignment", "Neutral Good"),
            ("age", "Immortal"),
            ("location", "Various"),
            ("affiliation", "The Fellowship, White Council"),
        ]
        
        for key, value in gandalf_props:
            prop = EntityProperty(entity_id=gandalf.id, key=key, value=value)
            db.add(prop)
        
        gandalf_sections = [
            {
                "section_type": "description",
                "sort_order": 1,
                "content": """Gandalf is a wise and powerful wizard, one of the Istari sent to Middle-earth to aid in the fight against Sauron. He is known for his long grey beard, pointed hat, and staff. He is a friend to hobbits and often appears when least expected."""
            },
            {
                "section_type": "traits",
                "sort_order": 2,
                "content": """**Wise Counselor.** Gandalf provides sage advice and guidance to those who seek it.

**Powerful Magic.** Though he rarely shows his full power, Gandalf is capable of great magical feats.

**Friend of All Races.** Gandalf has connections and friendships across Middle-earth."""
            }
        ]
        
        for section_data in gandalf_sections:
            section = EntitySection(
                entity_id=gandalf.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {gandalf.id}")
        
        # 4. The Prancing Pony (Location)
        print("\n4. Creating The Prancing Pony (Location)...")
        prancing_pony = Entity(
            type="location",
            name="The Prancing Pony"
        )
        db.add(prancing_pony)
        db.flush()
        
        location_props = [
            ("type", "Inn/Tavern"),
            ("location", "Bree"),
            ("owner", "Barliman Butterbur"),
            ("atmosphere", "Cozy, welcoming"),
        ]
        
        for key, value in location_props:
            prop = EntityProperty(entity_id=prancing_pony.id, key=key, value=value)
            db.add(prop)
        
        location_sections = [
            {
                "section_type": "description",
                "sort_order": 1,
                "content": """The Prancing Pony is a well-known inn in the town of Bree, located at the crossroads of the Great East Road and the Greenway. It's a popular stopping point for travelers and locals alike."""
            },
            {
                "section_type": "features",
                "sort_order": 2,
                "content": """**Common Room.** Large, warm room with a fireplace, tables, and benches. Often filled with locals and travelers sharing news.

**Rooms.** Several guest rooms available for rent on the upper floor.

**Stables.** Secure stables for horses and ponies.

**Kitchen.** Serves hearty meals and ale."""
            }
        ]
        
        for section_data in location_sections:
            section = EntitySection(
                entity_id=prancing_pony.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {prancing_pony.id}")
        
        # 5. Flame Tongue Sword (Item)
        print("\n5. Creating Flame Tongue Sword (Item)...")
        flame_tongue = Entity(
            type="item",
            name="Flame Tongue Sword"
        )
        db.add(flame_tongue)
        db.flush()
        
        item_props = [
            ("type", "Weapon (Longsword)"),
            ("rarity", "Rare"),
            ("requires_attunement", "Yes"),
            ("damage", "1d8 slashing + 2d6 fire"),
            ("properties", "Versatile (1d10)"),
        ]
        
        for key, value in item_props:
            prop = EntityProperty(entity_id=flame_tongue.id, key=key, value=value)
            db.add(prop)
        
        item_sections = [
            {
                "section_type": "description",
                "sort_order": 1,
                "content": """A magical longsword that bursts into flame when its command word is spoken. The blade glows with a warm orange light and deals additional fire damage to its targets."""
            },
            {
                "section_type": "properties",
                "sort_order": 2,
                "content": """**Ignite.** You can use a bonus action to speak the sword's command word, causing flames to erupt from the blade. These flames shed bright light in a 40-foot radius and dim light for an additional 40 feet. While the sword is ablaze, it deals an extra 2d6 fire damage to any target it hits. The flames last until you use a bonus action to speak the command word again or until you drop or sheathe the sword."""
            }
        ]
        
        for section_data in item_sections:
            section = EntitySection(
                entity_id=flame_tongue.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {flame_tongue.id}")
        
        # 6. Fireball (Spell)
        print("\n6. Creating Fireball (Spell)...")
        fireball = Entity(
            type="spell",
            name="Fireball"
        )
        db.add(fireball)
        db.flush()
        
        spell_props = [
            ("level", "3rd"),
            ("school", "Evocation"),
            ("casting_time", "1 action"),
            ("range", "150 feet"),
            ("components", "V, S, M (a tiny ball of bat guano and sulfur)"),
            ("duration", "Instantaneous"),
            ("damage", "8d6 fire damage"),
            ("save", "Dexterity (half damage)"),
        ]
        
        for key, value in spell_props:
            prop = EntityProperty(entity_id=fireball.id, key=key, value=value)
            db.add(prop)
        
        spell_sections = [
            {
                "section_type": "description",
                "sort_order": 1,
                "content": """A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame. Each creature in a 20-foot-radius sphere centered on that point must make a Dexterity saving throw. A target takes 8d6 fire damage on a failed save, or half as much damage on a successful one."""
            },
            {
                "section_type": "at_higher_levels",
                "sort_order": 2,
                "content": """When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd."""
            }
        ]
        
        for section_data in spell_sections:
            section = EntitySection(
                entity_id=fireball.id,
                section_type=section_data["section_type"],
                content=section_data["content"],
                sort_order=section_data["sort_order"]
            )
            db.add(section)
        
        print(f"   Created with ID: {fireball.id}")
        
        db.commit()
        
        print("\n" + "="*60)
        print("DUMMY DATA CREATION COMPLETE!")
        print("="*60)
        print(f"\nCreated {6} entities:")
        print(f"  - 2 Creatures (Adult Red Dragon, Goblin Warrior)")
        print(f"  - 1 NPC (Gandalf the Grey)")
        print(f"  - 1 Location (The Prancing Pony)")
        print(f"  - 1 Item (Flame Tongue Sword)")
        print(f"  - 1 Spell (Fireball)")
        print("\nThese entities should now appear in the Data Manager!")
        print("Double-click any entity to open it in the Stat Block Editor.")


if __name__ == "__main__":
    try:
        create_dummy_entities()
    except Exception as e:
        print(f"\nError creating dummy data: {e}")
        import traceback
        traceback.print_exc()


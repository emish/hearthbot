"""Provides the hearthstone card database to clients.
"""

import json, logging
from hearthbot import HEARTH_DB

logger = logging.getLogger('CARD-DATA')

class CardData(object):
    def __init__(self, filepath=HEARTH_DB+"/AllSets.json"):
        """Holds the data of all the cards"""
        self.filepath = filepath
        self.cardDB = json.loads(file(self.filepath, 'r').read())

    def find_card(self, cardId):
        """Don't prematurely optimize.
        Returns a dict that represents this card with its values.
        """
        for k in self.cardDB.keys():
            for d in self.cardDB[k]:
                if d.get('id') == cardId:
                    return d
        return None

# Singleton
card_data = CardData()

class Card(object):
    def __init__(self, data, card_id):
        self.name = data['name']
        self.cost = data.get('cost', 0)
        self.health = data.get('health', 0)
        # Every card in the game has a unique id
        self.id = card_id
        # A card's zone can be PLAY, HAND, GRAVEYARD
        self.zone = "NO_ZONE"
        # A card's position in a zone
        self.pos = None
        # The amount of damage a card has taken
        self.damage = 0
        # Whether or not a card can be used (minion summoning sickness or having attacked)
        self.active = False
        # Any card can have mechanics. They are strings.
        self.mechanics = data.get('mechanics', [])

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

class Hero(Card):
    def __init__(self, data, card_id):
        Card.__init__(self, data, card_id)
        self.attack = data.get('attack', 0)
        self.damage = 0
        self._has_attacked = False

    def __repr__(self):
        return "{} ({}/{}) - (id:{})".format(self.name, self.attack,
                                             self.health, self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

    def performs_attack(self):
        self._has_attacked = True
        self.deactivate()       # Can't attack anymore

class HeroPower(Card):
    def __init__(self, data, card_id):
        Card.__init__(self, data, card_id)

    def __repr__(self):
        return "{} - (id:{})".format(self.name, self.id)
    
class Minion(Card):
    def __init__(self, data, card_id):
        """Battlecry-triggered events will change the minion state appropriately after they occur.
        """
        Card.__init__(self, data, card_id)
        self.attack = data['attack']
        self.health = data['health']
        self.damage = 0
        self._has_attacked = False

        # Check for specific mechanics
        if self.has_charge():
            self.activate()

    def __repr__(self):
        return "{} ({}:{}/{}) (id:{}) (pos:{})".format(self.name, self.cost,
                                                       self.attack, self.health, self.id, self.pos)
            
    def has_charge(self):
        return 'Charge' in self.mechanics

    def has_stealth(self):
        return (not self.has_attacked()) and 'Stealth' in self.mechanics

    def has_attacked(self):
        return self._has_attacked

    def performs_attack(self):
        """Apply state changes that take place when attacking.
        """
        # TODO: Check if any mechanics allow the card to attack more than once.
        # TODO: Check if any mechanics need status updates (stealth, other auras)
        self._has_attacked = True
        self.deactivate()       # Can't attack anymore
    
    def remaining_health(self):
        return int(self.health) - int(self.damage)

class Spell(Card):
    def __init__(self, data, card_id):
        Card.__init__(self, data, card_id)

    def __repr__(self):
        return "{} - {} mana (id:{})".format(self.name, self.cost, self.id)

class Weapon(Card):
    def __init__(self, data, card_id):
        Card.__init__(self, data, card_id)
        self.attack = data['attack']
        # For the purposes of scorekeeping, a weapon's durability is basically health
        # (Weapons take damage when they lose durability)
        self.health = data['durability']
        self.damage = 0

    def __repr__(self):
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack,
                                                     self.health, self.cost, self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

class Enchantment(Card):
    def __init__(self, data, card_id):
        Card.__init__(self, data, card_id)

    def __repr__(self):
        return "{} - {} mana (id:{})".format(self.name, self.cost, self.id)

def card_from_id(cardId, card_id):
    """Given a string that is the name of a card,
    return the entity as an instance of our classes.
    Give the entity an id provided by the game log.
    """
    data = card_data.find_card(cardId)
    if not data:
        return None

    card = None
    
    if data['type'] == 'Minion':
        card = Minion(data, card_id)
    elif data['type'] == 'Weapon':
        card = Weapon(data, card_id)
    elif data['type'] == 'Spell':
        card = Spell(data, card_id)
    elif data['type'] == 'Enchantment':
        card = Enchantment(data, card_id)
    elif data['type'] == 'Hero':
        card = Hero(data, card_id)
    elif data['type'] == 'Hero Power':
        card = HeroPower(data, card_id)
    else:
        logger.error("No card type found for cardId: "+cardId)

    return card

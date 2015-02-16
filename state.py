"""
The game state. 
Cardlogger updates the state.
Bot reads the state.

If a card has no position, it is not considered to be in play and usable
(hero, hero power)
"""

import json
import logging
import pprint

import kooloolimpah

logger = logging.getLogger('STATE')

class Player(object):
    def __init__(self, name):
        self.name = name
        # whether a player goes first or second
        self.num = None
        self.hand = []
        # players minions on the field
        self.minions = []
        self.weapon = None
        self.hero = None
        # The amount of mana a player has available this turn
        self.mana = 0
        # The amount of mana spent this turn
        self.mana_spent = 0
        self.max_mana = 10

    def mana_available(self):
        return int(self.mana) - int(self.mana_spent)

    def spend_mana(self, amount):
        self.mana_spent += amount
        logger.info("Spending {} mana. Total spent = {}".format(amount, self.mana_spent))

    def prepare_for_new_turn(self):
        """Prepares a player for their turn.
        - Restore and increment mana.
        - Wake minions from summoning sickness.
        - Set can_attack of minions and self.
        """
        # Add a mana to our pool and reset our spent mana
        self.mana_spent = 0
        if self.mana < self.max_mana:
            self.mana += 1
        
        # All minions we have are now active (barring any edge cases)
        for minion in self.minions:
            minion.activate()

    def has_card(self, card_name):
        """Returns the Card object if the player has a card in hand with name card_name.
        Returns None if no card has that name.
        """
        for c in self.hand:
            if c.name == card_name:
                return c

        return None

class GameState(object):
    def __init__(self):
        "Tracks the game state."
        # Players
        self.tingle = Player("TINGLE")
        self.opponent = Player("OPPONENT")

        # Tracking all cards
        # id to card object mapping
        self.all_cards = {}     # All cards seen (a history)
        self.cards_in_play = {} # Cards currently active (in play or hand)
        self.graveyard = {}     # Cards in the graveyard

        # Game state
        self.turn = "OURS"      # or "THEIRS"
        self.game_started = False
        self.game_ended = False
        self.num = None
        self.opp_num = None

    def __repr__(self):
        return "GameState: started: {}".format(self.game_started)

    def init(self):
        """Initialize all aspects of the game.
        """
        # Players
        self.tingle = Player("TINGLE")
        self.opponent = Player("OPPONENT")

        # Tracking all cards
        # id to card object mapping
        self.all_cards = {}     # All cards seen (a history)
        self.cards_in_play = {} # Cards currently active (in play or hand)
        self.graveyard = {}     # Cards in the graveyard

        # Game state
        self.turn = "OURS"      # or "THEIRS"
        self.game_started = False
        self.game_ended = False
        self.num = None
        self.opp_num = None
        
    def start_game(self):
        self.init()
        self.game_started = True
        logger.info("*"*26)
        logger.info("*"*5+" STARTING GAME "+"*"*5)
        logger.info("*"*26)
        
    def set_our_turn(self):
        self.turn = "OURS"
        self.tingle.prepare_for_new_turn()
        logger.info("*"*10)
        logger.info("TINGLE's TURN - {} mana".format(self.tingle.mana_available()))
        logger.info("*"*10)

    def set_opponent_turn(self):
        self.turn = "THEIRS"
        logger.info("*"*10)
        logger.info("OPPONENT TURN")
        logger.info("*"*10)

    def set_player_number(self, number):
        self.tingle.num = number
        self.opponent.num = "1" if self.num == "2" else "2"
        logger.info("TINGLE is player {}".format(self.tingle.num))
        logger.info("OPPONENT is player {}".format(self.opponent.num))
        self.game_started = True

    def send_to_graveyard(self, card_id):
        """Send a card to the graveyard. If it's already there,
        just ignore this update.
        """
        card = self.card_with_id(card_id)
        if card:
            if card.zone == "GRAVEYARD":
                return
            self.graveyard[card_id] = card
            self.cards_in_play.pop(card_id)
            if card in self.tingle.minions:
                self.tingle.minions.remove(card)
            if card in self.opponent.minions:
                self.opponent.minions.remove(card)
            card.zone = "GRAVEYARD"
            logger.info("{} has been moved to graveyard".format(card))
        else:
            logger.error("Can't find {} to send to graveyard".format(card))

        assert card not in self.opponent.minions
        assert card not in self.tingle.minions
        assert card not in self.cards_in_play.values()
            
    def add_card_to_game(self, card):
        """Add a card to this game's state. Keep track of the card by id.
        """
        if not self.all_cards.has_key(card.id):
            self.all_cards[card.id] = card
            if card.zone == "PLAY" or card.zone == "HAND":
                self.cards_in_play[card.id] = card
                logger.info("Adding {} to active cards in zone {}".format(card, card.zone))
            #logger.debug("Cards in play:\n"+pprint.pformat(self.cards_in_play))
            return True
        elif self.graveyard.has_key(card.id):
            logger.warn("Trying to add card to play but its already in the graveyard, so skipping: {}".format(card))
            return False
        else:
            logger.error("Adding card to play but it already exists and is not in graveyard: {}".format(card))
            return False

    def remove_card_from_game(self, card):
        self.all_cards.pop(card.id)
        self.cards_in_play.pop(card.id)
        
    def add_card_to_hand(self, cardId, card_id):
        """Add a card with cardId and id to hand.
        Add it to game.
        """
        card = card_from_id(cardId, card_id)
        if card:
            logger.info("DRAW CARD: {}".format(card))
            card.zone = "HAND"
            self.add_card_to_game(card)
            self.tingle.hand.append(card)
        else:
            logger.error("Trying to add card {} (card_id={}) to HAND but no card with that name found".\
                          format(cardId, card_id))
        logger.info("Cards in HAND:\n"+ pprint.pformat(self.tingle.hand))
        
    def play_minion(self, cardId, card_id):
        # If the minion was already in our hand, use that one
        card = self.card_with_id(card_id)
        if card:
            card.zone = "PLAY"
            self.tingle.minions.append(card)
            logger.info("TINGLE plays minion from hand: {}".format(card))
            self.tingle.spend_mana(int(card.cost))
            return

        # this is a minion that was not in our hand (or in play)
        if not card:
            minion = card_from_id(cardId, card_id)
            if minion:
                minion.zone = "PLAY"
                # if its a hero or hero power, add it to game but not our play area
                if isinstance(minion, HeroPower) or isinstance(minion, Weapon):
                    logger.info("Moving Hero Power/Weapon to play but not as a minion: {}".\
                                 format(minion))
                    self.add_card_to_game(minion)
                    return
                
                if isinstance(minion, Hero):
                    logger.info("Adding our hero to play: {}".format(minion))
                    self.add_card_to_game(minion)
                    self.tingle.hero = minion
                    return
                
                logger.info("Playing a minion that was not in our hand!")
                if self.add_card_to_game(minion):
                    self.tingle.minions.append(minion)
                    logger.info("TINGLE plays: {}".format(minion))
                    logger.info("TINGLE's minions:\n"+pprint.pformat(self.tingle.minions))
            else:
                logger.error("Trying to add minion {} (card_id={}) to PLAY but no minion found with that name".\
                             format(cardId, card_id))

    def opp_play_minion(self, cardId, card_id, pos):
        """The opponent plays a minion with a specific position.
        """
        minion = card_from_id(cardId, card_id)
        if minion:
            minion.zone = "PLAY"
            minion.pos = pos
            # if its a hero power or weapon, add it to game but not our play area
            if isinstance(minion, HeroPower) or isinstance(minion, Weapon):
                logger.info("Moving Hero Power/Weapon to play but not as minion: {}".\
                             format(minion))
                self.add_card_to_game(minion)
                return
            
            if isinstance(minion, Hero):
                logger.info("Adding opponent hero to play: {}".format(minion))
                self.add_card_to_game(minion)
                self.opponent.hero = minion
                return

            if self.add_card_to_game(minion):
                self.opponent.minions.append(minion)
                logger.info("OPPONENT plays: {}".format(minion))
                logger.info("OPPONENT's minions:\n"+pprint.pformat(self.opponent.minions))
        else:
            logger.error("Trying to add opponent minion {} (card_id={}) to PLAY but no minion found with that name.".\
                         format(cardId, card_id))

    def hero_power(self, player, card_id, target_id=None):
        """
        Player with num `player` plays hero power with id `id` against 
        possible target `target_id`
        """
        hpower = self.card_with_id(card_id)
        if hpower:
            if player == self.tingle.num:
                logger.info("TINGLE plays hero power {} -> {}".\
                             format(hpower, target_id))
            else:
                logger.info("OPPONENT plays hero power {} -> {}".\
                             format(hpower, target_id))
        else:
            logger.error("Trying to play a hero power that we don't know exists {}".\
                          format(card_id))
            
    def opp_play_spell(self, cardId, card_id):
        spell = card_from_id(cardId, card_id)
        if spell:
            spell.zone = "PLAY"
            logger.info("OPPONENT plays: {}".format(spell))
            self.add_card_to_game(spell)
        else:
            logger.error("Trying to add opponent spell {} (card_id={}) to PLAY but no spell found with that name.".\
                         format(cardId, card_id))

    def update_zone(self, card_id, player, zone):
        card = self.card_with_id(card_id)
        if card and card.zone != "GRAVEYARD":
            logger.info("Update {} to zone {}".format(card, zone))
            if zone == "GRAVEYARD":
                self.send_to_graveyard(card_id)
            if zone == "DECK":
                if card in self.tingle.hand:
                    self.tingle.hand.remove(card)
                self.remove_card_from_game(card)
            if zone == "PLAY":
                if card in self.tingle.hand:
                    self.tingle.hand.remove(card)
            # if zone == "PLAY":
            #     if player == "1":
            #         logger.info("TINGLE puts minion into play: {}".format(card))
            #     else:
            #         logger.info("OPPONENT puts minion into play: {}".format(card))
        else:
            pass
            #logger.debug("update_zone: Unknown card with id {}".format(id))
            
    def add_target_to_card(self, card_id, target_id):
        card = self.card_with_id(card_id)
        target = self.card_with_id(target_id)
        if not card:
            #logger.debug("No card id {} to give target to".format(id))
            pass
        elif not target:
            logger.error("No target id {} for card {}".format(target_id, card))
        else:
            logger.info("{} has a target: {}".format(card, target))
            
    def perform_attack(self, att_id, def_id):
        """Character with att_id attacks character with def_id.
        """
        att_card = self.card_with_id(att_id)
        def_card = self.card_with_id(def_id)
        logger.info("ATTACK: {} -> {}".format(att_card, def_card))        
        att_card.performs_attack()

    def update_card_tag(self, card_id, tag, value):
        """Update a specific property of a card.
        TODO: If a card doesn't exist yet in our game, we create a stub to store the tag change until
        the card is revealed.
        """
        card = self.card_with_id(card_id)
        if not card:
            logger.warn("No id {} found to perform tag update for {} = {}".format(card_id, tag, value))
            # Push this update off until later (we might have more information by then)
            #self.add_tag_update_to_queue(card_id, tag, value)
            return
        if card.zone == "GRAVEYARD":
            # we don't care
            return
        else:
            if tag == "ATK":
                card.attack = value
                logger.info("{} has {} ATTACK".format(card, card.attack))                
            elif tag == "DAMAGE":
                card.damage = value
                logger.info("{} has {} DAMAGE".format(card, card.damage))
                if int(card.damage) >= int(card.health):
                    logger.info("{} has fatal damage".format(card))
            elif tag == "HEALTH":
                card.health = value
                logger.info("{} has {} HEALTH".format(card, card.health))
            elif tag == "ARMOR":
                card.armor = value
                logger.info("{} has {} ARMOR".format(card, card.armor))
            elif tag == "COST":
                card.cost = value
                logger.info("{} has {} cost".format(card, card.cost))
            elif tag == "CONTROLLER":
                self.set_card_controller(card_id, value)
            else:
                pass
                #logger.debug("Unused tag {}".format(tag))

    def set_card_controller(self, card_id, controller):
        """Set card's controller
        """
        card = self.card_with_id(card_id)
        if card:
            if controller == self.num:
                logger.info("{} is now under TINGLE's control".format(card))
                self.opponent.minions.remove(card)
                self.tingle.minions.append(card)
            elif controller == self.opp_num:
                logger.info("{} is now under OPPONENT's control".format(card))
                self.tingle.minions.remove(card)
                self.opponent.minions.append(card)
            else:
                logger.error("Can't have no controller")
                
        else:
            logger.error("Can't find card id {} to change controller".format(card_id))
            
    def card_with_id(self, card_id):
        return self.all_cards.get(card_id)

    def update_card_pos(self, card_id, pos):
        """Update a card's position.
        Card with id gets position pos.
        """
        card = self.card_with_id(card_id)
        if not card:
            logger.warn("Trying to update ID of a card we haven't seen before.")
            return
        if card.zone == "GRAVEYARD":
            # we don't care
            return
        card.pos = pos
        logger.info("Update card {} to position {} in {}".\
                     format(card, card.pos, card.zone))

    def set_won(self):
        logger.info("TINGLE wins!")
        self.game_started = False
        self.game_ended = True
        kooloolimpah.magic()

    def set_lost(self):
        logger.info("TINGLE lost!")
        self.game_started = False
        self.game_ended = True
        kooloolimpah.grouch()
    
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
        self.attack = data['attack']
        self.health = data['health']
        self.damage = 0

    def __repr__(self):
        return "{} ({}/{}) - (id:{})".format(self.name, self.attack,
                                             self.health, self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

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
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack,
                                                     self.health, self.cost, self.id)
            
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

class CardData(object):
    def __init__(self, filepath="AllSets.json"):
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

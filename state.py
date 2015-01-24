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

        logging.info("*"*26)
        logging.info("*"*5+" STARTING GAME "+"*"*5)
        logging.info("*"*26)
        
    def set_our_turn(self):
        self.turn = "OURS"
        logging.info("*"*10)
        logging.info("TINGLE's TURN")
        logging.info("*"*10)

    def set_opponent_turn(self):
        self.turn = "THEIRS"
        logging.info("*"*10)
        logging.info("OPPONENT TURN")
        logging.info("*"*10)

    def set_player_number(self, number):
        self.tingle.num = number
        self.opponent.num = "1" if self.num == "2" else "2"
        logging.info("TINGLE is player {}".format(self.tingle.num))
        logging.info("OPPONENT is player {}".format(self.opponent.num))
        self.game_started = True

    def send_to_graveyard(self, card_id):
        card = self.card_with_id(card_id)
        if card:
            self.graveyard[card_id] = card
            self.cards_in_play.pop(card_id)
            if card in self.tingle.minions:
                self.tingle.minions.remove(card)
            if card in self.opponent.minions:
                self.opponent.minions.remove(card)
            card.zone = "GRAVEYARD"
            logging.info("{} has been moved to graveyard".format(card))
        else:
            logging.error("Can't find {} to send to graveyard".format(card))

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
                logging.info("Adding {} to active cards in zone {}".format(card, card.zone))
            logging.info("Cards in play:\n"+pprint.pformat(self.cards_in_play))
            return True
        elif self.graveyard.has_key(card.id):
            logging.warn("Trying to add card to play but its already in the graveyard, so skipping: {}".format(card))
            return False
        else:
            logging.error("Adding card to play but it already exists and is not in graveyard: {}".format(card))
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
            logging.info("DRAW CARD: {}".format(card))
            card.zone = "HAND"
            self.add_card_to_game(card)
            self.tingle.hand.append(card)
        else:
            logging.error("Trying to add card {} (card_id={}) to HAND but no card with that name found".\
                          format(cardId, card_id))
        logging.info("Cards in HAND:\n"+ pprint.pformat(self.tingle.hand))
        
    def play_minion(self, cardId, card_id):
        # If the minion was already in our hand, use that one
        card = self.card_with_id(card_id)
        if card:
            self.tingle.minions.append(card)
            logging.info("TINGLE plays minion from hand: {}".format(card))
            return

        # this is a minion that was not in our hand (or in play)
        if not card:
            minion = card_from_id(cardId, card_id)
            if minion:
                # if its a hero or hero power, add it to game but not our play area
                if isinstance(minion, HeroPower):
                    logging.info("Ignoring moving Hero Power to play: {}".\
                                 format(minion))
                    self.add_card_to_game(minion)
                    return
                
                # Anything else is considered "in play"
                minion.zone = "PLAY"
                if isinstance(minion, Hero):
                    logging.info("Adding our hero to play: {}".format(minion))
                    self.add_card_to_game(minion)
                    self.tingle.hero = minion
                    return
                
                logging.info("Playing a minion that was not in our hand!")
                if self.add_card_to_game(minion):
                    self.tingle.minions.append(minion)
                    logging.info("TINGLE plays: {}".format(minion))
                    logging.info("TINGLE's minions:\n"+pprint.pformat(self.tingle.minions))
            else:
                logging.error("Trying to add minion {} (card_id={}) to PLAY but no minion found with that name".\
                             format(cardId, card_id))

    def opp_play_minion(self, cardId, card_id):
        minion = card_from_id(cardId, card_id)
        if minion:
            # if its a hero or hero power, add it to game but not our play area
            if isinstance(minion, HeroPower):
                logging.info("Ignoring moving Hero/Hero Power to play: {}".\
                             format(minion))
                self.add_card_to_game(minion)
                return
            
            # Anything else is considered "in play"            
            minion.zone = "PLAY"
            if isinstance(minion, Hero):
                logging.info("Adding opponent hero to play: {}".format(minion))
                self.add_card_to_game(minion)
                self.opponent.hero = minion
                return

            if self.add_card_to_game(minion):
                self.opponent.minions.append(minion)
                logging.info("OPPONENT plays: {}".format(minion))
                logging.info("OPPONENT's minions:\n"+pprint.pformat(self.opponent.minions))
        else:
            logging.error("Trying to add opponent minion {} (card_id={}) to PLAY but no minion found with that name.".\
                         format(cardId, card_id))

    def hero_power(self, player, card_id, target_id=None):
        """
        Player with num `player` plays hero power with id `id` against 
        possible target `target_id`
        """
        hpower = self.card_with_id(card_id)
        if hpower:
            if player == self.tingle.num:
                logging.info("TINGLE plays hero power {} -> {}".\
                             format(hpower, target_id))
            else:
                logging.info("OPPONENT plays hero power {} -> {}".\
                             format(hpower, target_id))
        else:
            logging.error("Trying to play a hero power that we don't know exists {}".\
                          format(card_id))
            
    def opp_play_spell(self, cardId, card_id):
        spell = card_from_id(cardId, card_id)
        if spell:
            spell.zone = "PLAY"
            logging.info("OPPONENT plays: {}".format(spell))
            self.add_card_to_game(spell)
        else:
            logging.error("Trying to add opponent spell {} (card_id={}) to PLAY but no spell found with that name.".\
                         format(cardId, card_id))

    def update_zone(self, card_id, player, zone):
        card = self.card_with_id(card_id)
        if card and card.zone != "GRAVEYARD":
            logging.info("Update {} to zone {}".format(card, zone))
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
            #         logging.info("TINGLE puts minion into play: {}".format(card))
            #     else:
            #         logging.info("OPPONENT puts minion into play: {}".format(card))
        else:
            pass
            #logging.debug("update_zone: Unknown card with id {}".format(id))
            
    def add_target_to_card(self, card_id, target_id):
        card = self.card_with_id(card_id)
        target = self.card_with_id(target_id)
        if not card:
            #logging.debug("No card id {} to give target to".format(id))
            pass
        elif not target:
            logging.error("No target id {} for card {}".format(target_id, card))
        else:
            logging.info("{} has a target: {}".format(card, target))
            
    def perform_attack(self, att_id, def_id):
        """Character with att_id attacks character with def_id.
        """
        att_card = self.card_with_id(att_id)
        def_card = self.card_with_id(def_id)
        logging.info("ATTACK: {} -> {}".format(att_card, def_card))

    def update_card_tag(self, card_id, tag, value):
        """Update a specific property of a card.
        TODO: If a card doesn't exist yet in our game, we create a stub to store the tag change until
        the card is revealed.
        """
        card = self.card_with_id(card_id)
        if not card:
            logging.warn("No id {} found to perform tag update for {} = {}".format(card_id, tag, value))
            # Push this update off until later (we might have more information by then)
            #self.add_tag_update_to_queue(card_id, tag, value)
            return
        if card.zone == "GRAVEYARD":
            # we don't care
            return
        else:
            if tag == "ATK":
                card.attack = value
                logging.info("{} has {} ATTACK".format(card, card.attack))                
            elif tag == "DAMAGE":
                card.damage = value
                logging.info("{} has {} DAMAGE".format(card, card.damage))
                if int(card.damage) >= int(card.health):
                    logging.info("{} has fatal damage".format(card))
            elif tag == "HEALTH":
                card.health = value
                logging.info("{} has {} HEALTH".format(card, card.health))
            elif tag == "ARMOR":
                card.armor = value
                logging.info("{} has {} ARMOR".format(card, card.armor))
            elif tag == "COST":
                card.cost = value
                logging.info("{} has {} cost".format(card, card.cost))
            elif tag == "CONTROLLER":
                self.set_card_controller(card_id, value)
            else:
                logging.debug("Unused tag {}".format(tag))

    def set_card_controller(self, card_id, controller):
        """Set card's controller
        """
        card = self.card_with_id(card_id)
        if card:
            if controller == self.num:
                logging.info("{} is now under TINGLE's control".format(card))
                self.opponent.minions.remove(card)
                self.tingle.minions.append(card)
            elif controller == self.opp_num:
                logging.info("{} is now under OPPONENT's control".format(card))
                self.tingle.minions.remove(card)
                self.opponent.minions.append(card)
            else:
                logging.error("Can't have no controller")
                
        else:
            logging.error("Can't find card id {} to change controller".format(card_id))
            
    def card_with_id(self, card_id):
        return self.all_cards.get(card_id)

    def update_card_pos(self, card_id, pos):
        """Update a card's position.
        Card with id gets position pos.
        """
        card = self.card_with_id(card_id)
        if not card:
            logging.warn("Trying to update ID of a card we haven't seen before.")
            return
        if card.zone == "GRAVEYARD":
            # we don't care
            return
        card.pos = pos
        logging.info("Update card {} to position {} in {}".\
                     format(card, pos, card.zone))

    def set_won(self):
        logging.info("TINGLE wins!")
        self.game_ended = True

    def set_lost(self):
        logging.info("TINGLE lost!")
        self.game_ended = True
    
class Card(object):
    def __init__(self, name, card_id, cost=0, health=0):
        self.name = name
        self.cost = cost
        # Every card in the game has a unique id
        self.id = card_id
        # A card's zone can be PLAY, HAND, GRAVEYARD
        self.zone = "NO_ZONE"
        # A card's position in a zone
        self.pos = None
        # The amount of damage a card has taken
        self.damage = 0
        # I'm not sure what this can be used for, a card's validity
        self.active = False
        # Any card can have mechanics. They are strings.
        self.mechanics = []

    def activate(self):
        self.active = True

    def destroy(self):
        """Put in graveyard."""
        self.active = False

class Hero(Card):
    def __init__(self, name, card_id, health=30, attack='0'):
        Card.__init__(self, name, card_id)
        self.attack = attack
        self.health = health
        self.damage = 0

    def __repr__(self):
        return "{} ({}/{}) - (id:{})".format(self.name, self.attack,
                                             self.remaining_health(), self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

class HeroPower(Card):
    def __init__(self, name, card_id, cost):
        Card.__init__(self, name, card_id, cost)

    def __repr__(self):
        return "{} - (id:{})".format(self.name, self.id)
    
class Minion(Card):
    def __init__(self, name, card_id, cost, attack, health):
        Card.__init__(self, name, card_id, cost)
        self.attack = attack
        self.health = health
        self.damage = 0

    def __repr__(self):
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack,
                                                     self.remaining_health(), self.cost, self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

class Spell(Card):
    def __init__(self, name, card_id, cost):
        Card.__init__(self, name, card_id, cost)

    def __repr__(self):
        return "{} - {} mana (id:{})".format(self.name, self.cost, self.id)

class Weapon(Card):
    def __init__(self, name, card_id, cost, attack, durability):
        Card.__init__(self, name, card_id, cost)
        self.attack = attack
        # For the purposes of scorekeeping, a weapon's durability is basically health
        # (Weapons take damage when they lose durability)
        self.health = durability
        self.damage = 0

    def __repr__(self):
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack,
                                                     self.remaining_health(), self.cost, self.id)

    def remaining_health(self):
        return int(self.health) - int(self.damage)

class Enchantment(Card):
    def __init__(self, name, card_id, cost):
        Card.__init__(self, name, card_id, cost)

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
        card = Minion(data['name'], card_id, data['cost'], data['attack'], data['health'])
    elif data['type'] == 'Weapon':
        card = Weapon(data['name'], card_id, data['cost'], data['attack'], data['durability'])
    elif data['type'] == 'Spell':
        card = Spell(data['name'], card_id, data.get('cost', '0'))
    elif data['type'] == 'Enchantment':
        card = Enchantment(data['name'], card_id, data.get('cost', '0'))
    elif data['type'] == 'Hero':
        card = Hero(data['name'], card_id)
    elif data['type'] == 'Hero Power':
        card = HeroPower(data['name'], card_id, data['cost'])
    else:
        logging.error("No card type found for cardId: "+cardId)

    # Add any mechanics to this card if it has any
    if data.has_key('mechanics'):
        card.mechanics = data['mechanics']

    return card

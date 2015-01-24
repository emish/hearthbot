"""
The game state. 
Cardlogger updates the state.
Bot reads the state.

If a card has no position, it is not considered to be in play and usable
(hero, hero power)
"""

import json
import logging

class GameState(object):
    def __init__(self):
        "Tracks the game state."
        self.cards_in_hand = []
        self.my_minions = []
        self.opp_minions = []
        self.my_health = 30
        self.opp_health = 30

        # id to card object mapping
        self.all_cards = {}
        self.cards_in_play = {}
        self.graveyard = {}

        self.turn = "OURS"      # or "THEIRS"

    def set_our_turn(self):
        self.turn = "OURS"
        logging.info("TINGLE's TURN")

    def set_opponent_turn(self):
        self.turn = "THEIRS"
        logging.info("OPPONENT TURN")

    def set_player_number(self, number):
        self.num = number
        self.opp_num = "1" if self.num == "2" else "2"
        logging.info("TINGLE is player {}".format(self.num))
        logging.info("OPPONENT is player {}".format(self.opp_num))

    def send_to_graveyard(self, id):
        card = self.card_with_id(id)
        if card:
            #self.remove_card_from_game(card)
            self.graveyard[id] = card
            logging.info("{} has been moved to graveyard".format(card))
        else:
            logging.error("Can't find {} to send to graveyard".format(card))
            
    def add_card_to_game(self, card):
        """Add a card to this game's state. Keep track of the card by id.
        """
        if not self.all_cards.has_key(card.id):
            self.all_cards[card.id] = card
            return True
        elif self.graveyard.has_key(card.id):
            logging.warn("Trying to add card to play but its already in the graveyard, so skipping: {}".format(card))
            return False
        else:
            logging.warn("Adding card to play but it already exists and is not in graveyard: {}".format(card))
            return False

    def remove_card_from_game(self, card):
        del self.all_cards[card.id]
        
    def add_card_to_hand(self, cardId, id):
        """Add a card with cardId and id to hand.
        """
        card = card_from_id(cardId, id)
        if card:
            logging.info("DRAW CARD: {}".format(card))
            self.cards_in_hand.append(card)
            self.add_card_to_game(card)
            card.zone = "HAND"
        else:
            logging.error("Trying to add card {} (id={}) to HAND but no card with that name found".\
                          format(cardId, id))
        logging.info("Cards in hand: {}".format(self.cards_in_hand))
        
    def play_minion(self, cardId, id):
        # If the minion was already in our hand, use that one
        card = self.card_with_id(id)
        if card:
            # Just add it to our minions list
            self.my_minions.append(card)
            logging.info("TINGLE plays from hand: {}".format(card))
            return
        # this is a minion we have been 'granted'
        if not card:
            minion = card_from_id(cardId, id)
            if minion:
                # if its a hero or hero power, add it to game but not our play area
                if isinstance(minion, Hero) or isinstance(minion, HeroPower):
                    logging.info("Ignoring moving Hero/Hero Power to play: {}".\
                                 format(minion))
                    self.add_card_to_game(minion)
                    return
                
                logging.info("Playing a minion that was not in our hand!")
                if self.add_card_to_game(minion):
                    self.my_minions.append(minion)
                    logging.info("TINGLE plays: {}".format(minion))
                    minion.zone = "PLAY"
            else:
                logging.error("Trying to add minion {} (id={}) to PLAY but no minion found with that name".\
                             format(cardId, id))

    def opp_play_minion(self, cardId, id):
        minion = card_from_id(cardId, id)
        if minion:
            # if its a hero or hero power, add it to game but not our play area
            if isinstance(minion, Hero) or isinstance(minion, HeroPower):
                logging.info("Ignoring moving Hero/Hero Power to play: {}".\
                             format(minion))
                self.add_card_to_game(minion)
                return
            
            logging.info("OPPONENT plays: {}".format(minion))
            if self.add_card_to_game(minion):
                self.opp_minions.append(minion)
                minion.zone = "PLAY"
        else:
            logging.error("Trying to add opponent minion {} (id={}) to PLAY but no minion found with that name.".\
                         format(cardId, id))

    def hero_power(self, player, id, target_id=None):
        """
        Player with num `player` plays hero power with id `id` against 
        possible target `target_id`
        """
        hpower = self.card_with_id(id)
        if hpower:
            if player == self.num:
                logging.info("TINGLE plays hero power {} -> {}".\
                             format(hpower, target_id))
            else:
                logging.info("OPPONENT plays hero power {} -> {}".\
                             format(hpower, target_id))
        else:
            logging.error("Trying to play a hero power that we don't know exists {}".\
                          format(id))
            
    def opp_play_spell(self, cardId, id):
        spell = card_from_id(cardId, id)
        if spell:
            logging.info("OPPONENT plays: {}".format(spell))
            self.add_card_to_game(spell)
        else:
            logging.error("Trying to add opponent spell {} (id={}) to PLAY but no spell found with that name.".\
                         format(cardId, id))

    def update_zone(self, id, player, zone):
        card = self.card_with_id(id)
        if card:
            logging.info("Update {} to zone {}".format(card, zone))
            if zone == "GRAVEYARD":
                self.send_to_graveyard(id)
            if zone == "DECK":
                if card in self.cards_in_hand:
                    self.cards_in_hand.remove(card)
                    self.remove_card_from_game(card)
            if zone == "PLAY":
                if card in self.cards_in_hand:
                    self.cards_in_hand.remove(card)
            # if zone == "PLAY":
            #     if player == "1":
            #         logging.info("TINGLE puts minion into play: {}".format(card))
            #     else:
            #         logging.info("OPPONENT puts minion into play: {}".format(card))
        else:
            pass
            #logging.debug("update_zone: Unknown card with id {}".format(id))
            
    def add_target_to_card(self, id, target_id):
        card = self.card_with_id(id)
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
        logging.info("TINGLE's minions: {}".format(self.my_minions))
        logging.info("OPPONENT's minions: {}".format(self.opp_minions))

    def set_card_damage(self, id, damage):
        card = self.card_with_id(id)
        if card:
            card.damage = damage
            logging.info("{} has {} damage".format(card, card.damage))
            if int(card.damage) >= int(card.health):
                logging.info("{} has fatal damage".format(card))
        else:
            pass
            #logging.debug("Can't find card {} to give damage to".format(id))

    def set_card_health(self, id, attack):
        card = self.card_with_id(id)
        if card:
            card.attack = attack
            logging.info("{} has {} attack".format(card, card.attack))
        else:
            logging.error("Can't find card id {} to change health".format(id))
            
    def set_card_attack(self, id, attack):
        """Set card's attack.
        """
        card = self.card_with_id(id)
        if card:
            card.attack = attack
            logging.info("{} has {} attack".format(card, card.attack))
        else:
            logging.error("Can't find card id {} to change attack".format(id))

    def set_card_armor(self, id, armor):
        """Set card's armor
        """
        card = self.card_with_id(id)
        if card:
            card.armor = armor
            logging.info("{} has {} armor".format(card, card.armor))
        else:
            logging.error("Can't find card id {} to change armor".format(id))

    def set_card_cost(self, id, cost):
        """Set card's cost
        """
        card = self.card_with_id(id)
        if card:
            card.cost = cost
            logging.info("{} has {} cost".format(card, card.cost))
        else:
            logging.error("Can't find card id {} to change cost".format(id))

    def set_card_controller(self, id, controller):
        """Set card's controller
        """
        card = self.card_with_id(id)
        if card:
            if id == self.num:
                logging.info("{} is now under TINGLE's control".format(card))
                self.opp_minions.remove(card)
                self.my_minions.append(card)
            elif id == self.opp_num:
                logging.info("{} is now under OPPONENT's control".format(card))
                self.my_minions.remove(card)
                self.opp_minions.append(card)
        else:
            logging.error("Can't find card id {} to change controller".format(id))
            
    def card_with_id(self, id):
        return self.all_cards.get(id)

    def update_card_pos(self, id, pos):
        """Update a card's position.
        Card with id gets position pos.
        """
        c = self.card_with_id(id)
        if not c:
            logging.warn("Trying to update ID of a card we haven't seen before.")
            return
        c.pos = pos
        logging.info("Update card {} to position {} in {}".\
                     format(c, pos, c.zone))

    def set_won(self):
        logging.info("TINGLE wins!")
        # end game

    def set_lost(self):
        logging.info("TINGLE lost!")
        # end game
    
class Card(object):
    def __init__(self, name, id, cost=0, health=0):
        self.name = name
        self.cost = cost
        # Every card in the game has a unique id
        self.id = id
        # A card's zone can be PLAY, HAND, GRAVEYARD
        self.zone = "NO_ZONE"
        # A card's position in a zone
        self.pos = None
        # The amount of damage a card has taken
        self.damage = 0

    def activate(self):
        self.active = True

    def destroy(self):
        """Put in graveyard."""
        self.active = False

class Hero(Card):
    def __init__(self, name, id, health=30, attack='0'):
        Card.__init__(self, name, id)
        self.attack = attack
        self.health = health

    def __repr__(self):
        return "{} ({}/{}) - (id:{})".format(self.name, self.attack, self.health, self.id)

class HeroPower(Card):
    def __init__(self, name, id, cost):
        Card.__init__(self, name, id, cost)

    def __repr__(self):
        return "{} - (id:{})".format(self.name, self.id)
    
class Minion(Card):
    def __init__(self, name, id, cost, attack, health):
        Card.__init__(self, name, id, cost)
        self.attack = attack
        self.health = health

    def __repr__(self):
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack, self.health, self.cost, self.id)

class Spell(Card):
    def __init__(self, name, id, cost):
        Card.__init__(self, name, id, cost)

    def __repr__(self):
        return "{} - {} mana (id:{})".format(self.name, self.cost, self.id)

class Weapon(Card):
    def __init__(self, name, id, cost, attack, durability):
        Card.__init__(self, name, id, cost)
        self.attack = attack
        self.durability = durability

    def __repr__(self):
        return "{} ({}/{}) - {} mana (id:{})".format(self.name, self.attack, self.durability, self.cost, self.id)

class Enchantment(Card):
    def __init__(self, name, id, cost):
        Card.__init__(self, name, id, cost)

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

def card_from_id(cardId, id):
    """Given a string that is the name of a card,
    return the entity as an instance of our classes.
    Give the entity an id provided by the game log.
    """
    data = card_data.find_card(cardId)
    if not data:
        return None

    card = None
    
    if data['type'] == 'Minion':
        card = Minion(data['name'], id, data['cost'], data['attack'], data['health'])
    elif data['type'] == 'Weapon':
        card = Weapon(data['name'], id, data['cost'], data['attack'], data['durability'])
    elif data['type'] == 'Spell':
        card = Spell(data['name'], id, data.get('cost', '0'))
    elif data['type'] == 'Enchantment':
        card = Enchantment(data['name'], id, data.get('cost', '0'))
    elif data['type'] == 'Hero':
        card = Hero(data['name'], id)
    elif data['type'] == 'Hero Power':
        card = HeroPower(data['name'], id, data['cost'])
    else:
        logging.error("No card type found for cardId: "+cardId)

    return card

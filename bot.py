"""
This is Tingle's brain.

- Tingle will need to click through the end sequence, especially if there are gold winnings.

- Minions spawned by special abilities aren't used to attack with:
    - Turns out hoggers gnoll wasn't introduced into the logs until after our turn started. 
      which means tingle though it was still inactive. 
- Tingle doesn't know that there's a max minion limit in play
- Minions with divine shield screw up attack calculation. (todo)
"""

import logging, time, os
import itertools
import copy # for deep copies with copy.deepcopy
import pprint

import control, cardlogger, state
import kooloolimpah

from botattack import *

# The file for the hearthstone log
hearthstone_log = os.path.expanduser("~/Library/Logs/Unity/Player.log")

# The global state of the game, used to make decisions about things.
gstate = None

# Since this is where main is, we set up the main logging here
# The root logger (everything) logs to the log file at debug level
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-8s - %(levelname)-8s %(message)s',
                    datefmt='%mm:%dd - %H:%M:%S',
                    filename='tingle_logs/tingle_active.log',
                    filemode='w')
# And logs to the console at info level
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# Simple console format
formatter = logging.Formatter('%(name)-8s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger('BOT')

def attack_them(us, minions, minions_attacked, parser):
    """Attack the list of minions provided.
    The minions are guaranteed to be attacked.
    Returns:
        A list of friendly minions that have not yet attacked.
    """
    logger.info("Focus firing on minions: {}".format(minions))
    us_remain = us[:]
    them = minions[:]
    them.sort(cmp=highest_attack_cmp)
    for enemy in them:
        logger.info("Focus firing on {}".format(enemy))
        # If we can kill this minion, do it
        attackers = can_kill_minion(us_remain, enemy)
        if attackers:
            # Since we are attacking with these, remove them from future calculations
            for m in attackers:
                us_remain.remove(m)
            # Perform the attack
                attack_minion(m, enemy)
                minions_attacked.append(m)
                parser.process_log()
            # Remove the enemy from our temporary calculation
            them.remove(enemy)

    # If we haven't attacked all enemies, and we still have minions able, attack them anyway
    if them and us_remain:
        # Pick the weakest one
        them.sort(cmp=lambda x,y: int(x.remaining_health()) < int(y.remaining_health()))
        for enemy in them:
            for m in us_remain:
                # If we've killed this enemy, stop attacking it
                if enemy.remaining_health() <= 0:
                    break
                us_remain.remove(m)
                attack_minion(m, enemy)
                minions_attacked.append(m)
                parser.process_log()

    assert (not [enemy for enemy in them if enemy.remaining_health() > 0]) or \
        (not us_remain), \
        "Enemies remain that have not been killed despite us having minions available to attack"
    return us_remain

def attack_phase(parser):
    logger.debug("Attack phase")
    # Make shallow copies so we can get updated locations of minions when others die
    us = gstate.tingle.minions[:]
    them = gstate.opponent.minions[:]
    minions_attacked = []

    # Can't attack if we have none
    if not us:
        return

    # These are the potential attackers (they must be active to attack)
    us_remain = [m for m in us if m.active]
    # They must have attack value to attack
    us_remain = [m for m in us_remain if int(m.attack) > 0]

    logger.debug("Minions available to attack:\n{}".\
                 format(pprint.pformat(us_remain)))

    # Attack any minions with taunt first
    taunters = [m for m in them if 'Taunt' in m.mechanics]
    us_remain = attack_them(us_remain, taunters, minions_attacked, parser)

    logger.debug("Minions remaining after taking out taunters:\n{}".\
                 format(pprint.pformat(us_remain)))

    # If we don't have any remaining, continue with attack
    if not us_remain:
        return

    # Recalculate minions after attacking taunters
    them = gstate.opponent.minions[:]

    logger.debug("Enemy minions remaining to take out:\n{}".\
                 format(pprint.pformat(them)))
    
    # Order them by highest attacks
    them.sort(cmp=highest_attack_cmp)
    for enemy in them:
        # If we can kill this minion, do it
        attackers = can_kill_minion(us_remain, enemy)
        if attackers:
            # Since we are attacking with these, remove them from future calculations
            for m in attackers:
                # If the minion got killed, stop trying
                if enemy.remaining_health() <= 0:
                    break
                
                us_remain.remove(m)
                # Perform the attack
                attack_minion(m, enemy)
                minions_attacked.append(m)
                parser.process_log()

    # If we have any minions left over, attack the hero
    for m in us_remain:
        attack_hero(m)
        minions_attacked.append(m)
        parser.process_log()

    # Here lies a bug: we may think we are attacking with a minion, but we click
    # on the wrong one
    time.sleep(1)
    parser.process_log()
    active_minions = [m for m in gstate.tingle.minions[:] if m.active and int(m.attack) > 0]
    assert not active_minions , \
        "Attack phase complete, but some minions did not attack: {}\nThought I attacked with {}".format(active_minions, minions_attacked)

def attack_hero(attacker):
    """Attack the defending hero. Don't wait for animation here
    because no status updates will occur.
    Except for secrets - we want to check if one exists before waiting for it to trigger.
    Store a secret object locally. If we attack, and nothing happens (secret still there), 
    move at full pace. If the secret triggers, wait, then move at full pace anyway.
    """
    my_num_minions = len(gstate.tingle.minions)
    control.my_click_on_minion(my_num_minions, int(attacker.pos))
    control.click_opponent_hero()

def attack_minion(attacker, defender):
    """Use the attacking minion to attack the defending one.
    Wait for kill animation to end, as gstate needs to update minion count.
    """
    logger.info("Attack {} -> {}".format(attacker, defender))
    my_num_minions = len(gstate.tingle.minions)
    their_num_minions = len(gstate.opponent.minions)
    assert my_num_minions
    assert their_num_minions
    assert attacker.zone == "PLAY"
    assert defender.zone == "PLAY"
    control.my_click_on_minion(my_num_minions, int(attacker.pos))
    control.opponent_click_on_minion(their_num_minions, int(defender.pos))
    time.sleep(2)
    
def play_phase(parser):
    """Decide which cards to play and play them.
    When making a decision, incorporate the coin primitively.
    """
    logger.debug("Play phase start")
    (total, cards) = spend_max_mana(gstate.tingle)
    logger.debug("Going to play {} with {} mana".format(cards, total))

    if total == gstate.tingle.mana_available() - 2:
        # We should play the draw ability first and recalculate
        play_hero_ability()
        parser.process_log()
        (total, cards) = spend_max_mana(gstate.tingle)

    num_in_field = len(gstate.tingle.minions)
    if num_in_field == 9:
        # play the most expensive card
        cards.sort(cmp=lambda x,y: int(x.cost) > int(y.cost))
        logger.info("Sorted cards: {}".format(cards))
        card = cards[0]
        num_in_hand = len(gstate.tingle.hand)
        control.play_minion(num_in_hand, int(card.pos))
        time.sleep(2)
        parser.process_log()

    num_in_field = len(gstate.tingle.minions)
    if num_in_field >= 10:
        return
    
    for card in cards:
        num_in_hand = len(gstate.tingle.hand)
        control.play_minion(num_in_hand, int(card.pos))
        # We need this to get the new position of cards
        time.sleep(2)
        parser.process_log()

def play_hero_ability():
    control.use_hero_ability()
    gstate.tingle.spend_mana(2)
    time.sleep(2)
        
def hero_power_phase():
    """Plays our hero power if we have enough mana.
    """
    if gstate.tingle.mana_available() >= 2:
        control.use_hero_ability()
        gstate.tingle.spend_mana(2)

def main():
    global gstate
    # Right now, we just play a game. later, we'll add the ability to keep playing games
    # You must have hearthstone synced with coordinates and at the start game screen
    logger.info("STARTING IN 5 SECONDS")
    time.sleep(5)
    logger.info("Tingle Tingle! Kooloo limpah!")
    kooloolimpah.kooloo_limpah()
    
    parser = cardlogger.Parser(hearthstone_log)
    #parser.reset_log()
    gstate = parser.gstate
    
    control.start_game()

    # Wait for game to load (we have cards in hand)
    while not gstate.game_started:
        logger.info("Waiting for game state to start: {}".format(gstate))
        parser.process_log()
        time.sleep(15)

    # while len(gstate.tingle.hand) < 3:
    #     logger.info("Waiting for cards to be drawn (only {} cards in hand right now)".\
    #                  format(len(gstate.tingle.hand)))
    #     parser.process_log()
    #     time.sleep(2)
    # time.sleep(2)

    parser.process_log()
    
    # Click on confirm button
    
    control.confirm_start_cards()

    # Wait for animation
    time.sleep(7)

    while not gstate.game_ended:
        parser.process_log()
        
        # Wait for our turn
        while not gstate.turn == "OURS":
            logger.info("Waiting for our turn...")
            parser.process_log()
            time.sleep(5)

        # When the logs say it's our turn, animation might still be taking place
        time.sleep(10)
        parser.process_log()
        
        # Play minions
        logger.info("*"*10)
        logger.info("Play Phase")
        logger.info("*"*10)
        logger.info("Tingle's Hand: ")
        logger.info("{}".format(pprint.pformat(gstate.tingle.hand)))
        play_phase(parser)
        parser.process_log()

        # # Play hero power
        # hero_power_phase()
        # time.sleep(5)           # We'll have to adjust this for different animations
        # parser.process_log()

        # # Play minions phase 2
        # play_phase(parser)
        # parser.process_log()

        # If any minions on the board, figure out if we should attack
        logger.info("*"*10)
        logger.info("Attack Phase")
        logger.info("*"*10)
        logger.info("{}".format(pprint.pformat(gstate.tingle.minions)))
        attack_phase(parser)
        parser.process_log()

        # End turn
        control.end_turn()
        # At least 10 seconds to get into the opponent's turn and start waiting.
        time.sleep(10)

    logger.info("BOT: Game done")


if __name__ == '__main__':
    main()

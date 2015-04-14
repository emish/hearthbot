"""
This is Tingle's brain.

- Tingle will need to click through the end sequence, especially if there are gold winnings.

- Minions spawned by special abilities aren't used to attack with:
    - Turns out hoggers gnoll wasn't introduced into the logs until after our turn started. 
      which means tingle thought it was still inactive. 
- Minions with divine shield screw up attack calculation. (todo)
"""

import logging, time, os
#import itertools
#import copy # for deep copies with copy.deepcopy
from pprint import pformat

from hearthbot import control, cardlogger, kooloolimpah, botalgs
from hearthbot import TINGLE_LOGS

# The file for the hearthstone log
hearthstone_log = os.path.expanduser("~/Library/Logs/Unity/Player.log")

# The global state of the game, used to make decisions about things.
gstate = None

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
    them.sort(cmp=botalgs.highest_attack_cmp)
    for enemy in them:
        logger.info("Focus firing on {}".format(enemy))
        # If we can kill this minion, do it
        attackers = botalgs.can_kill_minion(us_remain, enemy)
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
                 format(pformat(us_remain)))

    # Attack any minions with taunt first
    taunters = [m for m in them if 'Taunt' in m.mechanics]
    us_remain = attack_them(us_remain, taunters, minions_attacked, parser)

    logger.debug("Minions remaining after taking out taunters:\n{}".\
                 format(pformat(us_remain)))

    # If we don't have any remaining, continue with attack
    if not us_remain:
        return

    # Recalculate minions after attacking taunters
    them = gstate.opponent.minions[:]

    logger.debug("Enemy minions remaining to take out:\n{}".\
                 format(pformat(them)))
    
    # Order them by highest attacks
    them.sort(cmp=botalgs.highest_attack_cmp)
    for enemy in them:
        # If we can kill this minion, do it
        attackers = botalgs.can_kill_minion(us_remain, enemy)
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
    Don't play anything if there are 7 minions on the field.
    """
    logger.debug("Play phase start")

    (total, cards) = botalgs.cards_to_play(gstate.tingle)
    logger.debug("Going to play {} with {} mana".format(cards, total))

    if total + 2 <= gstate.tingle.mana_available():
        # We should play the draw ability first and recalculate
        logger.info("Avail mana is greater than what we can spend; using hero power and recalculating")
        play_hero_ability()
        parser.process_log()
        (total, cards) = botalgs.cards_to_play(gstate.tingle)
    
    for card in cards:
        num_in_hand = len(gstate.tingle.hand)
        control.play_minion(num_in_hand, int(card.pos))
        # We need this to get the new position of cards
        # TODO: With a built-in cache we could predict the future positions of minions that die
        # (assuming they don't have side-effects)
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

def config_main_logging(game_dir):
    """Set up logging parameters and locations.
    """
    global logger
    os.mkdir(game_dir)
    # The root logger (everything) logs to the log file at debug level
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(name)-8s] - <%(levelname)-5s> %(message)s',
                        datefmt='%mm:%dd-%H:%M:%S',
                        filename=os.path.join(game_dir, 'tingle.log'),
                        filemode='w')
    # And logs to the console at info level
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Simple console format
    formatter = logging.Formatter('%(name)-8s: <%(levelname)-5s> %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logger = logging.getLogger('BOT')
    logger.debug("Logging configured for Tingle")
        
def main():
    # Right now, we just play a game. later, we'll add the ability to keep playing games
    # You must have hearthstone synced with coordinates and at the start game screen
    
    # TODO: Append the name of the heroes after the game is played
    game_dir = os.path.join(TINGLE_LOGS, time.strftime('%Y_%m_%d__%H_%M__'))
    config_main_logging(game_dir)
    hs_log_copy = os.path.join(game_dir, 'hearthstone.log')

    global gstate
    logger.info("STARTING IN 5 SECONDS")
    time.sleep(5)
    logger.info("Tingle Tingle! Kooloo limpah!")
    kooloolimpah.kooloo_limpah()
    
    parser = cardlogger.Parser(hearthstone_log, hs_log_copy)
    parser.reset_log()
    gstate = parser.gstate
    
    control.start_game()

    # Wait for game to load (we have cards in hand)
    while not gstate.game_started:
        logger.info("Waiting for game state to start: {}".format(gstate))
        time.sleep(2)
        parser.process_log()

    logger.info("Game started. Waiting for setup animation to complete (20s)")
    time.sleep(20)
    parser.process_log()
        
    # Click on confirm button
    control.confirm_start_cards()

    # Wait for animation
    logger.info("Waiting for start cards animation...")
    time.sleep(10)

    while not gstate.game_ended:
        parser.process_log()
        
        # Wait for our turn
        while not gstate.turn == "OURS":
            logger.info("Waiting for our turn...")
            parser.process_log()
            time.sleep(5)

        # Wait to draw a card
        while not gstate.drew_card_this_turn:
            logger.info("Waiting to draw a card...")
            time.sleep(4)
            parser.process_log()

        # Animations may still be moving around
        current_log_position = parser.pos
        time.sleep(2)
        parser.process_log()
        while current_log_position != parser.pos:
            logger.info("Log is still printing, waiting for it to queisce...")
            current_log_position = parser.pos
            time.sleep(2)
            parser.process_log()
            
        # Play minions
        logger.info("*"*10)
        logger.info("Play Phase")
        logger.info("*"*10)
        logger.info("Tingle's Hand: ")
        logger.info("{}".format(pformat(gstate.tingle.hand)))
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
        logger.info("{}".format(pformat(gstate.tingle.minions)))
        attack_phase(parser)
        parser.process_log()

        # End turn
        control.end_turn()
        # At least 10 seconds to get into the opponent's turn and start waiting.
        time.sleep(10)

    logger.info("BOT: Game done")


if __name__ == '__main__':
    main()

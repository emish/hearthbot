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

import control, cardlogger, state
import kooloolimpah

# The file for the hearthstone log
hearthstone_log = os.path.expanduser("~/Library/Logs/Unity/Player.log")

# The global state of the game, used to make decisions about things.
gstate = None

# TODO: log to a file later
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger('BOT')
logger.setLevel(logging.DEBUG)

def highest_attack_cmp(min1, min2):
    if int(min1.attack) < int(min2.attack):
        return -1
    elif int(min1.attack) > int(min2.attack):
        return 1
    else:
        return 0

def can_kill_minion(min_list, minion):
    """Returns a subset of minions that can be used to attack the
    minion and kill it. Else, returns None.
    Use as few minions as possible to kill minion.
    Don't worry about keeping as many minions alive as possible yet.
    """
    for i in range(1, len(min_list)+1):
        candidates = itertools.combinations(min_list, i)
        best_candidate = None   # use later
        for c in candidates:
            # Evaluate this candidate list
            minion_health = int(minion.remaining_health())
            # For every minion in this list of candidates
            for m in c:
                minion_health -= int(m.attack)

            # this candidate list kills the minion
            if minion_health <= 0:
                return c
        
    return None

def attack_them(us, minions, parser):
    """Attack the list of minions provided.
    The minions are guaranteed to be attacked.
    Returns:
        A list of friendly minions that have not yet attacked.
    """
    us_remain = us[:]
    them = minions[:]
    them.sort(cmp=highest_attack_cmp)
    for enemy in them:
        # If we can kill this minion, do it
        attackers = can_kill_minion(us_remain, enemy)
        if attackers:
            # Since we are attacking with these, remove them from future calculations
            for m in attackers:
                us_remain.remove(m)
            # Perform the attack
                attack_minion(m, enemy)
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
                parser.process_log()

    return us_remain

def attack_phase(parser):
    logger.debug("Attack phase")
    # Make shallow copies so we can get updated locations of minions
    us = gstate.tingle.minions[:]
    them = gstate.opponent.minions[:]

    # Can't attack if we have none
    if not us:
        return

    # These are the potential attackers (they must be active to attack)
    us_remain = [m for m in us if m.active]
    # They must have attack value to attack
    us_remain = [m for m in us_remain if int(m.attack) > 0]

    logger.debug("Minions available to attack = {}".format(us_remain))

    # Attack any minions with taunt first
    taunters = [m for m in them if 'Taunt' in m.mechanics]
    us_remain = attack_them(us_remain, taunters, parser)

    # If we don't have any remaining, continue with attack
    if not us_remain:
        return

    # Recalculate minions after attacking taunters
    them = gstate.opponent.minions[:]
    
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
                parser.process_log()

    # If we have any minions left over, attack the hero
    for m in us_remain:
        attack_hero(m)
        parser.process_log()

def attack_hero(attacker):
    """Attack the defending hero. Don't wait for animation here
    because no status updates will occur.
    """
    my_num_minions = len(gstate.tingle.minions)
    control.my_click_on_minion(my_num_minions, int(attacker.pos))
    control.click_opponent_hero()

def attack_minion(attacker, defender):
    """Use the attacking minion to attack the defending one.
    Wait for kill animation to end, as gstate needs to update minion count.
    """
    logger.debug("Performing attack {} -> {}".format(attacker, defender))
    my_num_minions = len(gstate.tingle.minions)
    their_num_minions = len(gstate.opponent.minions)
    assert my_num_minions
    assert their_num_minions
    assert attacker.zone == "PLAY"
    assert defender.zone == "PLAY"
    control.my_click_on_minion(my_num_minions, int(attacker.pos))
    control.opponent_click_on_minion(their_num_minions, int(defender.pos))
    time.sleep(1)

def cost_to_play_cards(cards):
    """Given a list of cards, return the cost to play them all.
    """
    total = 0
    for card in cards:
        total += int(card.cost)
    return total
    
def spend_max_mana():
    """Return how much mana would be spent this turn playing cards from hand, 
    and the cards needed to play them.
    Right now, play as many cards as possible.
    
    Returns:
        (mana, cards) - where mana is an int and cards is a tuple of state.Card's
        Returns (0, ()) if no play is possible.
    
    Limitations:
        Only calculates mana spending with minions. Spell support forthcoming -_-
    """
    avail_mana = gstate.tingle.mana_available()
    logger.debug("Spend max mana. Available: {}".format(avail_mana))
    hand = gstate.tingle.hand[:] # shallow copy (so we still get updates to contents)

    # Remove any cards that cost more than the mana we can spend
    hand = [c for c in hand if c.cost <= avail_mana]
    # Remove any cards that are not minions
    hand = [c for c in hand if isinstance(c, state.Minion)]

    logger.debug("Candidates: {}".format(hand))

    # Try to play as many cards as possible, so consider more first
    for i in reversed(range(1, len(hand)+1)):
        # The amount of mana that would be spent by the current candidate play
        pot_mana_spent = 0
        pot_play = None
        # These are all the combinations of cards that can be played of size i
        play_combs = itertools.combinations(hand, i)
        for play in play_combs:
            mana_spent = cost_to_play_cards(play)
            logger.debug("Possible combination with cost {}: {}".format(mana_spent, play))
            # We can't play this hand
            if mana_spent > avail_mana:
                continue
            # This is the new potential candidate
            if mana_spent > pot_mana_spent:
                pot_mana_spent = mana_spent
                pot_play = play
                
        # This is the end of all plays of size i
        # If we have one, play it. Otherwise, keep looking
        if pot_play:
            assert pot_mana_spent
            return (pot_mana_spent, pot_play)

    return (0, ())
    
def play_phase(parser):
    """Decide which cards to play and play them.
    """
    logger.debug("Play phase")
    (total, cards) = spend_max_mana()
    logger.debug("Going to play {} with {} mana".format(cards, total))
    for card in cards:
        num_in_hand = len(gstate.tingle.hand)
        control.play_minion(num_in_hand, int(card.pos))
        #gstate.tingle.spend_mana(int(card.cost))
        # We need this to get the new position of cards
        time.sleep(2)
        parser.process_log()

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
    parser.reset_log()
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
            time.sleep(10)

        # When the logs say it's our turn, animation might still be taking place
        time.sleep(10)
        parser.process_log()
        
        # Play minions
        play_phase(parser)
        parser.process_log()

        # Play hero power
        hero_power_phase()
        time.sleep(5)           # We'll have to adjust this for different animations
        parser.process_log()

        # Play minions phase 2
        play_phase(parser)
        parser.process_log()

        # If any minions on the board, figure out if we should attack
        attack_phase(parser)
        parser.process_log()

        # End turn
        control.end_turn()
        # At least 10 seconds to get into the opponent's turn and start waiting.
        time.sleep(10)

    logger.info("BOT: Game done")


if __name__ == '__main__':
    main()

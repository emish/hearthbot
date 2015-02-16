"""
Strategies and functions for doing attacks and trading minions.

Try to keep this module state and control free.
"""

import logging, time, os
import itertools
import copy # for deep copies with copy.deepcopy

import state

logger = logging.getLogger('ALGS')

###
# Attacking
###

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
        - We'd have to change this to look at combinations that keep as many alive.
    Don't worry about keeping as many minions alive as possible yet.
    
    Args:
        min_list - List of state.Minion
        minion - A state.Minion to kill
    """
    logger.debug("can_kill_minion start")
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

    logger.debug("can_kill_minion end")
    return None

###
# Spending
###

def cost_to_play_cards(cards):
    """Given a list of cards, return the cost to play them all.
    """
    total = 0
    for card in cards:
        total += int(card.cost)
    return total

def spend_max_mana(player):
    """Return how much mana would be spent this turn playing cards from hand, 
    and the cards needed to play them.
    
    Right now, play as many cards as possible.

    Args:
        The player to play with.
    
    Returns:
        (mana, cards) - where mana is an int and cards is a tuple of state.Card's
        Returns (0, []) if no play is possible.
    
    Limitations:
        Only calculates mana spending with minions. Spell support forthcoming...

    Notes:
        This can easily be turned into a dynamic programming solution. Calculate 
        the best play for every subset, then build up the solution.
        best_play(mana, avail_cards) = 
                [play_card(c_i)] + best_play(mana - cost(c_i), avail_cards - c_i)
    """
    avail_mana = player.mana_available()
    coin = player.has_card("The Coin")
    if coin:
        avail_mana += 1
    
    logger.debug("Spend max mana. Available: {}".format(avail_mana))
    hand = player.hand[:] # shallow copy (so we still get updates to contents)

    # Remove any cards that cost more than the mana we can spend
    hand = [c for c in hand if c.cost <= avail_mana]
    # Remove any cards that are not minions
    hand = [c for c in hand if isinstance(c, state.Minion)]

    logger.debug("Candidates: {}".format(hand))

    ultimate_play = (0, [])

    # Try to play as many cards as possible, so consider more first
    for i in reversed(range(1, len(hand)+1)):
        if ultimate_play[0] > 0:       # Already have a play
            break
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
            ultimate_play = (pot_mana_spent, pot_play)
            break

    if coin:
        mana_to_spend = ultimate_play[0]
        if mana_to_spend == avail_mana:
            # play the coin first
            ultimate_play[1].insert(0, coin)
            
    return ultimate_play
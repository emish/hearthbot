"""
Strategies and functions for doing attacks and trading minions.

Try to keep this module state and control free.
"""

import logging
import itertools
#import copy # for deep copies with copy.deepcopy
from pprint import pformat

from hearthbot import state

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
    logger.debug("can_kill_minion start - {}\nTo Kill:{}".format(min_list, minion))
    for i in range(1, len(min_list)+1):
        candidates = itertools.combinations(min_list, i)
        #best_candidate = None   # use later
        for c in candidates:
            # Evaluate this candidate list
            minion_health = int(minion.remaining_health())
            # For every minion in this list of candidates
            for m in c:
                minion_health -= int(m.attack)

            # this candidate list kills the minion
            if minion_health <= 0:
                logger.debug("can_kill_minion end - {}".format(c))
                return c

    logger.debug("can_kill_minion end - no candidates")
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
        (mana, cards) : (Int, [state.Card])
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
    
    logger.info("Spend max mana. Available mana to spend: {}".format(avail_mana))
    hand = player.hand[:] # shallow copy (so we still get updates to contents)

    # Remove any cards that are not minions
    hand = [c for c in hand if isinstance(c, state.Minion)]
    # Remove any cards that cost more than the mana we can spend
    coin_hand = [c for c in hand if c.cost <= (avail_mana + 1)]
    hand = [c for c in hand if c.cost <= avail_mana]

    logger.info("Cards that cost less than {}:\n{}".format(avail_mana, pformat(hand)))
    play = play_with_max_mana(hand, avail_mana)

    logger.info("Potential play is: {} Mana\n{}".format(play[0], pformat(play[1])))
    # If the play found without using the coin does not use the maximum amount of mana
    if coin and (play[0] < avail_mana):
        # Calculate a second play with the coin involved
        logger.info("Coin detected and play is sub-optimal. Looking for better play...")
        play_coin = play_with_max_mana(coin_hand, avail_mana+1)
        play_coin[1].insert(0, coin)
        logger.info("Coin play is: {} Mana\n{}".format(play_coin[0], pformat(play_coin[1])))
        # Judge based on efficiency
        play_eff = avail_mana - play[0]
        logger.debug("Play without coin wastes {} mana.".format(play_eff))
        play_coin_eff = avail_mana+1 - play_coin[0]
        logger.debug("Play with coin wastes {} mana.".format(play_coin_eff))
        if (play_coin_eff < play_eff):
            logger.info("Coin play is chosen due to higher efficiency: {} remaining (vs. {} without coin)".\
                        format(play_eff, play_coin_eff))
            play = play_coin
        else:
            logger.info("Non-coin play is chosen: wasted mana: {} non-coin vs. {} coin".\
                        format(play_eff, play_coin_eff))
            
    return play


def play_with_max_mana(hand, avail_mana):
    """Returns a (mana cost, list of cards) tuple describing the play in this hand
    that costs the most mana under avail_mana.
    """
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
        #END play_combs of size i

        # This is the end of all plays of size i
        # If we have one, play it. Otherwise, keep looking
        if pot_play:
            assert pot_mana_spent
            ultimate_play = (pot_mana_spent, list(pot_play))
            break
    #END for all play combs of size i

    return ultimate_play

def cards_to_play(player):
    """Given a player, decide which cards should be played from the players hand
    incorporating the current minions the player has already played.
    
    Args: 
        A state.Player
    Returns:
        (total_mana, cards): (Int, [carddata.Card]) - The mana required and list of cards to play
    """
    num_in_field = len(player.minions)
    
    if num_in_field >= 7:
        logger.info("Maximum minions on the field, cannot play anymore.")
        (total, cards) = (0, [])
        
    elif num_in_field == 6:
        # play the most expensive card (This is an optimization over spend_max_mana)
        logger.info("I can only play one minion, so I'm going to play the most expensive one.")
        cards = player.hand[:] # Shallow
        cards = [c for c in cards if c.cost <= player.mana_available()]
        logger.info("The cards I can play with {} mana are:\n{}".\
                    format(player.mana_available(), pformat(cards)))
        cards.sort(cmp=lambda x,y: int(x.cost) > int(y.cost))
        logger.info("Sorted cards: {}".format(cards))
        card = cards[0]
        # Rewrite cards with the one expensive card
        (total, cards) = (card.cost, [card])
        
    else:
        (total, cards) = spend_max_mana(player)

    return (total, cards)

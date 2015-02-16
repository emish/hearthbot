"""
All coordinates here are relative to top left of hearthstone game screen (not including
the title bar).
"""

from mouseclick import mouseclick
import time
import logging

logger = logging.getLogger('CONTROL')

# Positions of menu items
coords_init = (0,100)
coords_play_button = (491, 284)
coords_hero_button = (164, 260)
coords_play_final_button = (820, 667)

def click_on_hero():
    """Click the hero we want to use to play"""
    mouseclick(coords_hero_button[0], coords_hero_button[1])

def start_game():
    """Starts a new game with our required hero.
    """
    mouseclick(coords_play_final_button[0], coords_play_final_button[1])

def go_to_play_mode_from_start():
    mouseclick(coords_init[0], coords_init[1])
    time.sleep(1)
    mouseclick(coords_play_button[0], coords_play_button[1])
    time.sleep(5)

def ranked():
    """Click the ranked button in play mode."""
    mouseclick(888, 169)

def game_click(coord):
    """Click on the provided coordinate (A tuple (x,y))
    """
    mouseclick(coord[0], coord[1])
    time.sleep(0.5)

# In-game buttons
confirm_button = (511, 606)
end_turn_button = (933, 342)

def confirm_start_cards():
    game_click(confirm_button)

def end_turn():
    logger.info("Ending turn")
    game_click(end_turn_button)

# Heros and hero abilities
hero_coord = (508, 588)
opp_hero_coord = (510, 139)
hero_power_button = (633, 589)

def use_hero_ability():
    logger.debug("Clicking hero power")
    game_click(hero_power_button)

def click_opponent_hero():
    game_click(opp_hero_coord)

def click_my_hero():
    game_click(hero_coord)

# Hand cards
# A map from number of cards in hand to
# location of cards by coordinate
card_coords = {
    1: [(478, 700)],
    2: [(425, 700), (531, 700)],
    3: [(377, 700), (480, 700), (578, 700)],
    4: [(340, 700),(436, 700),(529, 700),(631, 700)],
    5: [(317, 700), (405, 700), (485, 700), (559, 700), (636, 700)],
    6: [(310, 700), (378, 700), (447, 700), (505, 700), (571, 700), (645, 700)],
    7: [(295, 700), (366, 700), (421, 700), (482, 700), (532, 700), (592, 700), (650, 700)],
    8: [(289, 700), (335, 700), (383, 700), (435, 700), (481, 700), (527, 700), (585, 700), (650, 700)],
    9: [(72, 700), (126, 700), (167, 700), (210, 700), (251, 700), (291, 700), (339, 700), (387, 700), (436, 700)],
    }
    
def click_on_card(num_in_hand, card_idx):
    """Click on a card by index based on the number of cards
    in hand.
    Args:
        num_in_hand: Cards currently in hand
        card_idx: The position of the card in hand (starting at 1)
    """
    card_idx -= 1
    logger.debug("Clicking on hand card index {} with {} cards in hand".\
                 format(card_idx, num_in_hand))
    coords = card_coords[num_in_hand]
    game_click(coords[card_idx])

def play_minion(num_cards_in_hand, card_idx):
    """Clicks in the center of the screen to play a minion.
    Can also be used to play spells without a target.
    """
    click_on_card(num_cards_in_hand, card_idx)
    mouseclick(510, 472)

# Minions
# Map from number of minions on board
# to coord of minion on board by index
my_minion_coords = {
    1: [(505, 420)],
    2: [(458, 420), (559, 420)],
    3: [(412, 420), (509, 420), (609, 420)],
    4: [(361, 420), (457, 420), (559, 420), (654, 420)],
    5: [(307, 420), (406, 420), (506, 420), (603, 420), (704, 420)],
    6: [(263, 420), (356, 420), (457, 420), (557, 420), (656, 420), (752, 420)],
    7: [(212, 420), (312, 420), (405, 420), (508, 420), (607, 420), (707, 420), (805, 420)],
    }

opponent_minion_coords = {
    1: [(505, 300)],
    2: [(459, 300), (555, 300)],
    3: [(408, 300), (508, 300), (605, 300)],
    4: [(362, 300), (460, 300), (555, 300), (654, 300)],
    5: [(310, 300), (412, 300), (507, 300), (602, 300), (703, 300)],
    6: [(261, 300), (359, 300), (458, 300), (555, 300), (655, 300), (755, 300)],
    }

# Subtract one from minion_idx b/c the game tracks position from 1
def my_click_on_minion(my_num_minions, minion_idx):
    logger.debug("Clicking on minion at position {}".format(minion_idx))
    game_click(my_minion_coords[my_num_minions][minion_idx-1])

def opponent_click_on_minion(opp_num_minions, minion_idx):
    logger.debug("Clicking on opponent minion at position {}".format(minion_idx))
    game_click(opponent_minion_coords[opp_num_minions][minion_idx-1])

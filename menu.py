from mouseclick import mouseclick
import time

# Positions of menu items
coords_init = (0,100)
coords_play_button = (491, 284)
coords_hero_button = (164, 260)
coords_play_final_button = (820, 667)

def start_game():
    """Starts a new game with our required hero.
    """
    mouseclick(coords_hero_button[0], coords_hero_button[1])
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

# In-game buttons
confirm_button = (511, 659)
end_turn_button = (908, 390)

def confirm_start_cards():
    game_click(confirm_button)

def end_turn():
    game_click(end_turn_button)

# Heros and hero abilities
hero_coord = (508, 630)
opp_hero_coord = (510, 188)
hero_power_button = (633, 622)

def use_hero_ability():
    game_click(hero_power_button)

def click_opponent_hero():
    game_click(opp_hero_coord)

def click_my_hero():
    game_click(hero_coord)

# Hand cards
# A map from number of cards in hand to
# location of cards by coordinate
card_coords = {
    1: [(478, 758)],
    2: [(425, 753), (531, 752)],
    3: [(377, 760), (480, 754), (578, 761)],
    4: [(340, 798),(436, 770),(529, 773),(631, 761)],
    5: [(317, 760), (405, 765), (485, 769), (559, 775), (636, 777)],
    6: [(310, 762), (378, 764), (447, 765), (505, 767), (571, 769), (645, 769)],
    7: [(295, 766), (366, 764), (421, 763), (482, 765), (532, 766), (592, 766), (650, 763)],
    8: [(289, 764), (335, 762), (383, 761), (435, 765), (481, 764), (527, 764), (585, 762), (650, 762)],
    }
    
def click_on_card(num_in_hand, card_idx):
    """Click on a card by index based on the number of cards
    in hand.
    """
    coords = card_coords[num_in_hand]
    game_click(coords[card_idx])

def play_minion(num_cards_in_hand, card_idx):
    """Clicks in the center of the screen to play a minion.
    """
    click_on_card(num_cards_in_hand, card_idx)
    mouseclick(510, 472)

# Minions
# Map from number of minions on board
# to coord of minion on board by index
my_minion_coords = {
    1: [(505, 465)],
    2: [(458, 466), (559, 461)],
    3: [(412, 463), (509, 463), (609, 466)],
    4: [(361, 463), (457, 462), (559, 465), (654, 465)],
    5: [(307, 465), (406, 467), (506, 467), (603, 465), (704, 462)],
    6: [(263, 461), (356, 463), (457, 458), (557, 459), (656, 459), (752, 460)],
    7: [(212, 464), (312, 466), (405, 462), (508, 461), (607, 466), (707, 464), (805, 462)],
    }

opponent_minion_coords = {
    1: [(505, 326)],
    2: [(459, 335), (555, 331)],
    3: [(408, 330), (508, 331), (605, 330)],
    4: [(362, 335), (460, 327), (555, 332), (654, 332)],
    5: [(310, 336), (412, 334), (507, 329), (602, 328), (703, 333)],
    6: [(261, 337), (359, 336), (458, 335), (555, 334), (655, 333), (755, 331)],
    }

def my_click_on_minion(my_num_minions, minion_idx):
    game_click(my_minion_coords[my_num_minions][minion_idx])

def opponent_click_on_minion(opp_num_minions, minion_idx):
    game_click(opponent_minion_coords[opp_num_minions][minion_idx])

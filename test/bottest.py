import unittest
import os, sys

# Add hearthbot to the path for testing
hearthbot_home = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(hearthbot_home)

from hearthbot import state, botalgs

class TestBot(unittest.TestCase):
    def test_spend_max_mana(self):
        gstate = state.GameState()
        gstate.start_game()
        gstate.set_our_turn()
        gstate.add_card_to_hand('CS2_065', '01')
        voidwalker = gstate.tingle.hand[0]
        self.assertEqual((1, [voidwalker]), botalgs.spend_max_mana(gstate.tingle))

    def test_cards_to_play_empty(self):
        gstate = state.GameState()
        gstate.start_game()
        gstate.set_our_turn()
        self.assertEqual((0, []), botalgs.cards_to_play(gstate.tingle))
        
if __name__ == '__main__':
    unittest.main()

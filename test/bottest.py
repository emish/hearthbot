import unittest
import bot, state

class TestBot(unittest.TestCase):
    def test_spend_max_mana(self):
        gstate = state.GameState()
        gstate.start_game()
        gstate.set_our_turn()
        gstate.add_card_to_hand('CS2_065', '01')
        bot.gstate = gstate
        voidwalker = gstate.tingle.hand[0]
        self.assertEqual((1, (voidwalker,)), bot.spend_max_mana())

if __name__ == '__main__':
    unittest.main()

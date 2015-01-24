"""
This is Tingle's brain.

- Tingle will need to click through the end sequence, especially if there are gold winnings.
"""

from menu import start_game, click_on_card
import logging

# TODO: log to a file later
#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def main():
    logging.info("Tingle Tingle! Kooloo limpah!")
    start_game()
    

"""Run this in the same dir as the json.
"""

import json

filepath = 'AllSets.json'
outfile = file('all_cards_lines.txt', 'w')

cards = json.loads(file(filepath, 'r').read())
for k in cards.keys():
    for card in cards[k]:
        outfile.write(str(card))
        outfile.write("\n")

outfile.close()

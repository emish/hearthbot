import os, sys

# Add hearthbot to the path
hearthbot_home = os.path.dirname(os.path.abspath(__file__))
sys.path.append(hearthbot_home)

# Run Tingle
from hearthbot import bot
bot.main()

"""
A parser for the hearthstone log file.

player=1 is me
player=2 is opponent

Notes:
- The hearthstone log resets on startup.
- target of spells/powers is same as id of card. 
- all entities have an id.
"""

import os, sys
import re
import time
import logging

import state

# The parser's debug file logger
logger = logging.getLogger('parser')

player_name = "tingle"

class Parser(object):
    def __init__(self, hs_filepath, output_filepath):
        """Create a new game parser.
        
        Args:
            - hs_filepath: The source of the Hearthstone logs
            - output_filepath: A destination filepath to store lines that are parsed
        """
        self.hs_filepath = hs_filepath
        self.logfile = file(self.hs_filepath, 'r')
        
        self.output_filepath = output_filepath
        self.outfile = file(self.output_filepath, 'w')

        # Position in the HS log
        self.pos = 0
        # The state of the game
        self.gstate = state.GameState()

    def reset_log(self):
        """Read until the end of the log, not processing any of
        the events to the game state.
        """
        logger.info("Skipping to end of log file")
        self.logfile.seek(self.pos)
        self.logfile.readlines()
        self.pos = self.logfile.tell()
        
    def process_log(self):
        """Process the log, line by line, updating the state as necessary,
        until the log has no more data to provide for the time being.
        The log will close it's file handle, and we'll remember where we were
        for next time.
        """
        self.logfile.seek(self.pos)
        line = self.logfile.readline()
        while line:
            self.parse_next_line(line)
            line = self.logfile.readline()
        self.pos = self.logfile.tell()
        
    def parse_next_line(self, line):
        """Parse the next line of the log and update state as necessary.
        
        Returns:
            True if a line was read and parsed, false otherwise.
        """
        # This is the start of the game
        # [Power] GameState.DebugPrintPower() - CREATE_GAME
        gamestart_re = re.compile(r'.*CREATE_GAME')
        match = gamestart_re.match(line)
        if match:
            self.gstate.start_game()
            return True

        # If the game hasn't started, don't try to decode any lines (we don't care about them)
        if not self.gstate.game_started:
            return True

        # If we get past this line, we have started the game
        self.outfile.write(line)
        
        # Figure out if we are player 1 or 2: we see 'friendly play'
        #    2535:[Zone] ZoneChangeList.ProcessChanges() - TRANSITIONING card [name=Jaina Proudmoore id=4 zone=PLAY zonePos=0 cardId=HERO_08 player=1] to FRIENDLY PLAY (Hero)
        pl_re = re.compile(r'.*TRANSITIONING.*player=(1|2)] to FRIENDLY PLAY \(Hero\)')
        match = pl_re.match(line)
        if match:
            self.gstate.set_player_number(match.group(1))
            return True
        
        # If we win or lose
        # [Power] GameState.DebugPrintPower() - TAG_CHANGE Entity=bish3al tag=PLAYSTATE value=WON
        win_re = re.compile(r'.*TAG_CHANGE Entity='+player_name+' tag=PLAYSTATE value=(.*)')
        match = win_re.match(line)
        if match:
            win_value = match.group(1)
            if win_value == "WON":
                self.gstate.set_won()
            elif win_value == "LOST":
                self.gstate.set_lost()
            else:
                pass
                #logger.error("Unknown tag for win state: {}".format(win_value))

        # Set current player (and as such, the start of their turn)
        # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=bish3al tag=CURRENT_PLAYER value=0
        # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=The Innkeeper tag=CURRENT_PLAYER value=1
        curr_player = re.compile(r'.*TAG_CHANGE Entity='+player_name+r' tag=CURRENT_PLAYER value=([0-9])')
        match = curr_player.match(line)
        if match:
            playing = match.group(1)
            if playing == '0':
                self.gstate.set_opponent_turn()
            elif playing == '1':
                self.gstate.set_our_turn()
            else:
                logger.fatal("UNKNOWN CURRENT_PLAYER VALUE")
                sys.exit(1)
            return True

        # Draw a card
        # [Zone] ZoneChangeList.ProcessChanges() - id=1 local=False [name=Spider Tank id=6 zone=HAND zonePos=2 cardId=GVG_044 player=1] zone from  -> FRIENDLY HAND
        hand_draw = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .*-> FRIENDLY HAND')
        match = hand_draw.match(line)
        if match:
            card_id = match.group(1)
            cardId = match.group(2)
            self.gstate.add_card_to_hand(cardId, card_id)
            return True

        # Opponent plays a hero, hero power, or minion 
        # [Zone] ZoneChangeList.ProcessChanges() - id=75 local=False [name=Lightwarden id=79 zone=PLAY zonePos=2 cardId=EX1_001 player=2] zone from  -> OPPOSING PLAY
        # [Zone] ZoneChangeList.ProcessChanges() - id=1 local=False [name=Anduin Wrynn id=4 zone=PLAY zonePos=0 cardId=HERO_09 player=1] zone from  -> OPPOSING PLAY (Hero)
        opposing_play = re.compile(r'.*id=([0-9]+).*zonePos=([0-9]).*cardId=([a-zA-Z0-9_]+) .* -> OPPOSING PLAY')
        match = opposing_play.match(line)
        if match:
            logger.debug(line)
            card_id = match.group(1)
            pos = match.group(2)
            cardId = match.group(3)
            self.gstate.opp_play_minion(cardId, card_id, pos=pos)
            return True

        # We play a minion
        # Doesn't have to be from hand
        # [Zone] ZoneChangeList.ProcessChanges() - id=2 local=True [name=Twilight Drake id=66 zone=HAND zonePos=2 cardId=EX1_043 player=2] zone from FRIENDLY HAND -> FRIENDLY PLAY
        our_play = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .* -> FRIENDLY PLAY')
        match = our_play.match(line)
        if match:
            logger.debug(line)
            card_id = match.group(1)
            cardId = match.group(2)
            self.gstate.play_minion(cardId, card_id)
            return True

        # Minion goes to graveyard
        # [Zone] ZoneChangeList.ProcessChanges() - id=16 local=False [name=Wolfrider id=47 zone=GRAVEYARD zonePos=1 cardId=CS2_124 player=2] zone from OPPOSING PLAY -> OPPOSING GRAVEYARD
        grave_re = re.compile(r'.*id=([0-9]+).* -> OPPOSING GRAVEYARD')
        match = grave_re.match(line)
        if match:
            logger.debug(line)
            card_id = match.group(1)
            self.gstate.send_to_graveyard(card_id)
            return True
        
        # Update zone of a card
        # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=The Coin id=68 zone=HAND zonePos=4 cardId=GAME_005 player=1] tag=ZONE value=PLAY
        #    9876:[Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Amani Berserker id=13 zone=PLAY zonePos=1 cardId=EX1_393 player=1] tag=ZONE value=GRAVEYARD
        zone_re = re.compile(r'.* TAG_CHANGE .*id=([0-9]+).*player=(1|2)] tag=ZONE value=(.*)')
        match = zone_re.match(line)
        if match:
            #logger.debug(line)
            card_id = match.group(1)
            player = match.group(2)
            zone = match.group(3)
            self.gstate.update_zone(card_id, player, zone)
            return True

        # Update the location of a card/minion
        #   13768:[Zone] ZoneChangeList.ProcessChanges() - id=32 local=False [name=Sludge Belcher id=48 zone=PLAY zonePos=1 cardId=FP1_012 player=2] pos from 2 -> 1
        location = re.compile(r'.*name=(.*)id=([0-9]+).*pos from.*-> ([0-9])')
        match = location.match(line)
        if  match:
            name = match.group(1)
            card_id = match.group(2)
            pos = match.group(3)
            self.gstate.update_card_pos(card_id, pos)
            return True

        # Figure out which card attacked which
        # 
        attacking_play = re.compile(r'.*name=(.*)id=([0-9]+).*zonePos=([0-9]).*ATTACK.*name=(.*)id=([0-9]+).*zonePos=([0-9])')
        match = attacking_play.match(line)
        if match:
            logger.debug(line)
            att_id = match.group(2)
            def_id = match.group(5)
            self.gstate.perform_attack(att_id, def_id)
            return True

        # Numerical value tags
        # [Power] GameState.DebugPrintPower() -         TAG_CHANGE Entity=[name=Garrosh Hellscream id=4 zone=PLAY zonePos=0 cardId=HERO_01 player=1] tag=ARMOR value=2
        # [Power] GameState.DebugPrintPower() - TAG_CHANGE Entity=[name=Flamestrike id=27 zone=HAND zonePos=2 cardId=CS2_032 player=1] tag=COST value=12
        tag_re = re.compile(r'.*TAG_CHANGE.*id=([0-9]+).*tag=([A-Z]+) value=([0-9]+)$')
        match = tag_re.match(line)
        if match:
            logger.debug(line)
            card_id = match.group(1)
            tag = match.group(2)
            value = match.group(3)
            self.gstate.update_card_tag(card_id, tag, value)
            return True

        # Opponent plays a spell
        # [Zone] ZoneChangeList.ProcessChanges() - id=63 local=False [name=Polymorph id=61 zone=PLAY zonePos=5 cardId=CS2_022 player=2] zone from OPPOSING HAND -> 
        opposing_spell = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .* from OPPOSING HAND ->')
        match = opposing_spell.match(line)
        if match:
            card_id = match.group(1)
            cardId = match.group(2)
            self.gstate.opp_play_spell(cardId, card_id)
            return True

        # A spell has a target
        # [Zone] ZoneChangeList.ProcessChanges() - processing index=5 change=powerTask=[power=[type=TAG_CHANGE entity=[id=61 cardId=CS2_022 name=Polymorph] tag=CARD_TARGET value=13] complete=False] entity=[name=Polymorph id=61 zone=PLAY zonePos=0 cardId=CS2_022 player=2] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
        # [Zone] ZoneChangeList.ProcessChanges() - processing index=5 change=powerTask=[power=[type=TAG_CHANGE entity=[id=54 cardId=EX1_334 name=Shadow Madness] tag=CARD_TARGET value=6] complete=False] entity=[name=Shadow Madness id=54 zone=PLAY zonePos=0 cardId=EX1_334 player=2] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
        opposing_spell_target = re.compile(r'[Zone].*TAG_CHANGE.*id=([0-9]+).*CARD_TARGET value=([0-9]+).*')
        match = opposing_spell_target.match(line)
        if match:
            logger.debug(line)
            card_id = match.group(1)
            target = match.group(2)
            self.gstate.add_target_to_card(card_id, target)
            return True

        # Hero power with target
        # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Fireblast id=5 zone=PLAY zonePos=0 cardId=CS2_034 player=1] tag=CARD_TARGET value=59
        # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Lesser Heal id=37 zone=PLAY zonePos=0 cardId=CS1h_001 player=2] tag=CARD_TARGET value=36
        opposing_power = re.compile(r'[Power].*TAG_CHANGE.*id=([0-9]+).*player=(1|2)] tag=CARD_TARGET value=([0-9]+)$')
        match = opposing_power.match(line)
        if match:
            card_id = match.group(1)
            player = match.group(2)
            target_id = match.group(3)
            self.gstate.hero_power(player, card_id, target_id)
            return True

        # Hero power without target
        # [Power] GameState.DebugPrintPower() - ACTION_START Entity=[name=Dagger Mastery id=37 zone=PLAY zonePos=0 cardId=CS2_083b player=2] SubType=PLAY Index=0 Target=0
        # TODO

        # No match...
        return True

# Actual hearthstone log
#filename = os.path.expanduser("~/Library/Logs/Unity/Player.log")

# For testing
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/minion_sample.log")
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/real_game_1.log")
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/jaina_anduin.log")
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/warlock_1.log")
filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/tingle_bug_1.log")

def main():
    """Just read the log and output the state changes. 
    Used for testing.
    """
    parser = Parser(filename, '/tmp/output_hs.log')
    while True:
        parser.process_log()
        time.sleep(2)               # So we don't read the file too often

if __name__ == '__main__':
    main()

"""
player=1 is me
player=2 is opponent

If we draw 4 first turn, we have to include the coin.

target of spells/powers is same as id of card. all entities have an id.

still need a way to know it is our turn

should probably use logs to update state, not our actions. If
our actions fail for some reason, we can fall back.

Truths:
- The hearthstone log resets on startup.

Notes: 
- Garrosh didn't register armor up (Hero powers in general)
- minion buffs didn't register when given by another minion (might not be important because we register atk buffs automatically)
- After a minion takes lethal damage, Tingle continues to register them taking 0 damage. (fixed)
- Tingle doesn't know if a minion has taunt, divine shield, etc... IMPORTANT
- When a minion is destroyed by a spell, the damage taking doesn't account for that.
- Opponent plays a spell
- after opponent takes control of a minion, it might die before we record that the opponent PLAYs it.
- effect of a spell can happen before the spell is played. rely on zone updates.
- We don't register that some cards' value changes (loetheb) (important)
- we don't register health upgrades (fixed)
- I want Tingle to say Kooloo limpah when he wins.
"""

import os, sys
import re
import time
import logging

import state

logging.basicConfig(level=logging.DEBUG)

# Actual hearthstone log
#filename = os.path.expanduser("~/Library/Logs/Unity/Player.log")

# For testing
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/minion_sample.log")
#filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/real_game_1.log")
filename = os.path.expanduser("~/Documents/hearthbot/sample_logs/jaina_anduin.log")

player_name = "bish3al"

# Flag if a spell is played
#spell = False

# The game state
gstate = state.GameState()

pos = 0
while True:
    # global spell_start, spell_ready, location_needed
    time.sleep(2)
    with open(filename, 'r') as fp:
        fp.seek(pos)
        for line in fp:
            # Figure out if we are player 1 or 2
            #    2535:[Zone] ZoneChangeList.ProcessChanges() - TRANSITIONING card [name=Jaina Proudmoore id=4 zone=PLAY zonePos=0 cardId=HERO_08 player=1] to FRIENDLY PLAY (Hero)
            pl_re = re.compile(r'.*TRANSITIONING.*player=(1|2)] to FRIENDLY PLAY \(Hero\)')
            match = pl_re.match(line)
            if match:
                gstate.set_player_number(match.group(1))
                continue
            
            # Set current player (and as such, the start of their turn)
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=bish3al tag=CURRENT_PLAYER value=0
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=The Innkeeper tag=CURRENT_PLAYER value=1
            curr_player = re.compile(r'.*TAG_CHANGE Entity=bish3al tag=CURRENT_PLAYER value=([0-9])')
            match = curr_player.match(line)
            if match:
                playing = match.group(1)
                if playing == '0':
                    gstate.set_opponent_turn()
                elif playing == '1':
                    gstate.set_our_turn()
                else:
                    logging.fatal("UNKNOWN CURRENT_PLAYER VALUE")
                    sys.exit(1)
                continue
            
            # Draw a card
            # [Zone] ZoneChangeList.ProcessChanges() - id=1 local=False [name=Spider Tank id=6 zone=HAND zonePos=2 cardId=GVG_044 player=1] zone from  -> FRIENDLY HAND
            hand_draw = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .*-> FRIENDLY HAND')
            match = hand_draw.match(line)
            if match:
                id = match.group(1)
                cardId = match.group(2)
                gstate.add_card_to_hand(cardId, id)
                continue

            # Opponent plays a minion
            # [Zone] ZoneChangeList.ProcessChanges() - id=75 local=False [name=Lightwarden id=79 zone=PLAY zonePos=2 cardId=EX1_001 player=2] zone from  -> OPPOSING PLAY
            opposing_play = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .* -> OPPOSING PLAY')
            match = opposing_play.match(line)
            if match:
                #logging.debug(line)
                id = match.group(1)
                cardId = match.group(2)
                gstate.opp_play_minion(cardId, id)
                continue

            # We play a minion
            # [Zone] ZoneChangeList.ProcessChanges() - id=2 local=True [name=Twilight Drake id=66 zone=HAND zonePos=2 cardId=EX1_043 player=2] zone from FRIENDLY HAND -> FRIENDLY PLAY
            our_play = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .* -> FRIENDLY PLAY')
            match = our_play.match(line)
            if match:
                logging.debug(line)
                id = match.group(1)
                cardId = match.group(2)
                gstate.play_minion(cardId, id)
                continue

            # Update zone of a card
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=The Coin id=68 zone=HAND zonePos=4 cardId=GAME_005 player=1] tag=ZONE value=PLAY
            #    9876:[Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Amani Berserker id=13 zone=PLAY zonePos=1 cardId=EX1_393 player=1] tag=ZONE value=GRAVEYARD
            zone_re = re.compile(r'.* TAG_CHANGE .*id=([0-9]+).*player=(1|2)] tag=ZONE value=(.*)')
            match = zone_re.match(line)
            if match:
                #logging.debug(line)
                id = match.group(1)
                player = match.group(2)
                zone = match.group(3)
                gstate.update_zone(id, player, zone)
                continue
            
            # Update the location of a card/minion
            #   13768:[Zone] ZoneChangeList.ProcessChanges() - id=32 local=False [name=Sludge Belcher id=48 zone=PLAY zonePos=1 cardId=FP1_012 player=2] pos from 2 -> 1
            location = re.compile(r'.*name=(.*)id=([0-9]+).*pos from.*-> ([0-9])')
            match = location.match(line)
            if  match:
                name = match.group(1)
                id = match.group(2)
                pos = match.group(3)
                gstate.update_card_pos(id, pos)
                continue

            # Figure out which card attacked which
            # 
            attacking_play = re.compile(r'.*name=(.*)id=([0-9]+).*zonePos=([0-9]).*ATTACK.*name=(.*)id=([0-9]+).*zonePos=([0-9])')
            match = attacking_play.match(line)
            if match:
                logging.debug(line)
                att_id = match.group(2)
                def_id = match.group(5)
                gstate.perform_attack(att_id, def_id)
                continue

            # Damage
            # [Power] GameState.DebugPrintPower() -         TAG_CHANGE Entity=[name=Valeera Sanguinar id=36 zone=PLAY zonePos=0 cardId=HERO_03 player=2] tag=DAMAGE value=16
            # damage_re = re.compile(r'.*TAG_CHANGE.*id=([0-9]+).*tag=DAMAGE value=([0-9]+)$')
            # match = damage_re.match(line)
            # if match:
            #     logging.debug(line)
            #     id = match.group(1)
            #     damage = match.group(2)
            #     gstate.give_card_damage(id, damage)
            #     continue

            # Attack value of cards
            # [Power] GameState.DebugPrintPower() - TAG_CHANGE Entity=[name=Amani Berserker id=13 zone=PLAY zonePos=1 cardId=EX1_393 player=1] tag=ATK value=5
            # attack_re = re.compile(r'.*TAG_CHANGE.*id=([0-9]+).*tag=ATK value=([0-9]+)$')
            # match = attack_re.match(line)
            # if match:
            #     logging.debug(line)
            #     id = match.group(1)
            #     attack = match.group(2)
            #     gstate.change_attack_value(id, attack)
            #     continue

            # Health
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Lightspawn id=49 zone=PLAY zonePos=1 cardId=EX1_335 player=2] tag=HEALTH value=20
            # health_re = re.compile(r'.*TAG_CHANGE.*id=([0-9]+).*tag=HEALTH value=([0-9]+)$')
            # match = health_re.match(line)
            # if match:
            #     logging.debug(line)
            #     id = match.group(1)
            #     health = match.group(2)
            #     gstate.change_health_value(id, health)
            #     continue
            
            # Numerical value tags
            # [Power] GameState.DebugPrintPower() -         TAG_CHANGE Entity=[name=Garrosh Hellscream id=4 zone=PLAY zonePos=0 cardId=HERO_01 player=1] tag=ARMOR value=2
            # [Power] GameState.DebugPrintPower() - TAG_CHANGE Entity=[name=Flamestrike id=27 zone=HAND zonePos=2 cardId=CS2_032 player=1] tag=COST value=12
            tag_re = re.compile(r'.*TAG_CHANGE.*id=([0-9]+).*tag=([A-Z]+) value=([0-9]+)$')
            match = tag_re.match(line)
            if match:
                #logging.debug(line)
                id = match.group(1)
                tag = match.group(2)
                value = match.group(3)
                if tag == "ATK":
                    gstate.set_card_attack(id, value)
                elif tag == "DAMAGE":
                    gstate.set_card_damage(id, value)
                elif tag == "HEALTH":
                    gstate.set_card_health(id, value)
                elif tag == "ARMOR":
                    gstate.set_card_armor(id, value)
                elif tag == "COST":
                    gstate.set_card_cost(id, value)
                elif tag == "CONTROLLER":
                    gstate.set_card_controller(id, value)
                else:
                    logging.debug("Unused tag {}".format(tag))
                    
                continue
            
            # If we win or lose
            # [Power] GameState.DebugPrintPower() - TAG_CHANGE Entity=bish3al tag=PLAYSTATE value=WON
            win_re = re.compile(r'.*TAG_CHANGE Entity='+player_name+' tag=PLAYSTATE value=(.*)')
            match = win_re.match(line)
            if match:
                win_value = match.group(1)
                if win_value == "WON":
                    gstate.set_won()
                elif win_value == "LOST":
                    gstate.set_lost()
                else:
                    logging.error("Unknown tag for win state: {}".format(win_value))
            
            # BEGIN SPELL
            # Opponent plays a spell
            # [Zone] ZoneChangeList.ProcessChanges() - id=63 local=False [name=Polymorph id=61 zone=PLAY zonePos=5 cardId=CS2_022 player=2] zone from OPPOSING HAND -> 
            opposing_spell = re.compile(r'.*id=([0-9]+).*cardId=([a-zA-Z0-9_]+) .* from OPPOSING HAND ->')
            match = opposing_spell.match(line)
            if match:
                id = match.group(1)
                cardId = match.group(2)
                gstate.opp_play_spell(cardId, id)
                continue
            
            # [Zone] ZoneChangeList.ProcessChanges() - processing index=5 change=powerTask=[power=[type=TAG_CHANGE entity=[id=61 cardId=CS2_022 name=Polymorph] tag=CARD_TARGET value=13] complete=False] entity=[name=Polymorph id=61 zone=PLAY zonePos=0 cardId=CS2_022 player=2] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
            # [Zone] ZoneChangeList.ProcessChanges() - processing index=5 change=powerTask=[power=[type=TAG_CHANGE entity=[id=54 cardId=EX1_334 name=Shadow Madness] tag=CARD_TARGET value=6] complete=False] entity=[name=Shadow Madness id=54 zone=PLAY zonePos=0 cardId=EX1_334 player=2] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
            opposing_spell_target = re.compile(r'[Zone].*TAG_CHANGE.*id=([0-9]+).*CARD_TARGET value=([0-9]+).*')
            match = opposing_spell_target.match(line)
            if match:
                logging.debug(line)
                id = match.group(1)
                target = match.group(2)
                gstate.add_target_to_card(id, target)
                continue

            # Hero power with target
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Fireblast id=5 zone=PLAY zonePos=0 cardId=CS2_034 player=1] tag=CARD_TARGET value=59
            # [Power] GameState.DebugPrintPower() -     TAG_CHANGE Entity=[name=Lesser Heal id=37 zone=PLAY zonePos=0 cardId=CS1h_001 player=2] tag=CARD_TARGET value=36
            opposing_power = re.compile(r'[Power].*TAG_CHANGE.*id=([0-9]+).*PLAY.*player=(1|2)] tag=CARD_TARGET value=([0-9]+)$')
            match = opposing_power.match(line)
            if match:
                id = match.group(1)
                player = match.group(2)
                target_id = match.group(3)
                gstate.hero_power(player, id, target_id)
                # todo
                continue

            # Hero power without target
            # [Power] GameState.DebugPrintPower() - ACTION_START Entity=[name=Dagger Mastery id=37 zone=PLAY zonePos=0 cardId=CS2_083b player=2] SubType=PLAY Index=0 Target=0
            # TODO
            
        pos = fp.tell()
        

                        # Spell's effect (TAG_CHANGE)
            # [Zone] ZoneChangeList.ProcessChanges() - processing index=2 change=powerTask=[power=[type=TAG_CHANGE entity=[id=75 cardId=CS2_tk1 name=Sheep] tag=341 value=1] complete=False] entity=[name=Sheep id=75 zone=SETASIDE zonePos=0 cardId=CS2_tk1 player=1] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
            # opposing_spell_effect = re.compile(r'.*TAG_CHANGE.*name=(.*)id.*')
            # match = opposing_spell_effect.match(line)
            # if match and spell_ready:
            #     print "Matched: ", line
            #     spell_ready = False
            #     print "SPELL EFFECT is TAG CHANGE: -> {}".format(match.group(1))
            #     continue
            # END SPELL

                        # Wait for spell to 'leave hand'
            # [Zone] ZoneChangeList.OnUpdateLayoutComplete() - m_id=63 END waiting for zone OPPOSING HAND 
            # spell_played = re.compile(r'.*END.*OPPOSING HAND')
            # match = spell_played.match(line)
            # if match and spell_start:
            #     print "Spell left hand"
            #     spell_start = False
            #     spell_ready = True
            #     continue
            
            # Spell has a target
            # [Zone] ZoneChangeList.ProcessChanges() - processing index=0 change=powerTask=[power=[type=META_DATA metaType=META_TARGET data=0 info=1] complete=False] entity=[name=Boulderfist Ogre id=13 zone=PLAY zonePos=1 cardId=CS2_200 player=1] srcZoneTag=INVALID srcPos= dstZoneTag=INVALID dstPos=
            # opposing_spell_target = re.compile(r'.*META_TARGET.*name=(.*)id.*zonePos=([0-9]).*')

#!/usr/bin/python3
import sys, time, os
import engine, botplayer
from view.api import get_game_view

cfg_file = sys.argv[1]
bots = sys.argv[2:]
DEBUG = False
CONTINUE_ON_ERROR = False

config = engine.GameConfig(cfg_file)
game = engine.Game(config, len(bots))
actors = [botplayer.BotPlayer(game, i, cmdline, debug=DEBUG) for i, cmdline in enumerate(bots)]

for actor in actors:
    actor.initialize()

view = get_game_view(game)

round = 0
while True:
    game.pre_round()
    view.update(round)
    for actor in actors:
        try:
            actor.turn()
        except botplayer.CommError as e:
            if not CONTINUE_ON_ERROR:
                raise
            else:
                print("CommError: " + str(e))
                actor.close()
        view.update(round)
    game.post_round()
    s = "########### ROUND %d SCORE: " % round
    for i in range(len(bots)):
        s += "P%d: %d " % (i, game.players[i].score)
    print(s)
    round += 1
    if round >= int(os.getenv('AICONTEST_MAX_ROUNDS', '500')):
        break

view.update(round)

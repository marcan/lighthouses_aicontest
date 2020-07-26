#!/usr/bin/python3

import json, subprocess, time, select, sys, os, fcntl
import engine

class CommError(Exception):
    pass

class BotPlayer(object):
    INIT_TIMEOUT = 2.0
    MOVE_TIMEOUT = 0.1
    MOVE_HARDTIMEOUT = 0.5
    def __init__(self, game, playernum, cmdline, debug=False):
        self.alive = True
        self.p = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
        flag = fcntl.fcntl(self.p.stdout.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(self.p.stdout.fileno(), fcntl.F_SETFL, flag | os.O_NONBLOCK)
        self.game = game
        self.player = game.players[playernum]
        self.debug = debug

    def _send(self, data):
        line = json.dumps(data).encode("ascii")
        assert b"\n" not in line
        if self.debug:
            print(">>P%d: %r" % (self.player.num, line))
        try:
            self.p.stdin.write(line + b"\n")
            self.p.stdin.flush()
        except:
            raise CommError("Error sending data")

    def _recv(self, soft_timeout, hard_timeout):
        st = time.time()
        et = time.time() + soft_timeout
        ht = time.time() + hard_timeout
        line = b""
        try:
            while not line or line[-1] != 10:
                to = max(0, ht - time.time())
                r,w,e = select.select([self.p.stdout],[],[],to)
                if self.p.stdout not in r:
                    raise CommError("Bot %r over hard timeout" % self.player.name)
                c = os.read(self.p.stdout.fileno(), 1)
                if not c:
                    raise CommError("Bot closed stdout")
                line += c
        except Exception as e:
            raise CommError("Unknown error: %r" % e)
        if time.time() > et:
            sys.stderr.write("Bot %r over soft timeout\n" % self.player.name)
        try:
            if self.debug:
                print("<<P%d: %r" % (self.player.num, line))
            return json.loads(line)
        except Exception as e:
            raise CommError("Invalid JSON: %r" % e)

    def initialize(self):
        if not self.alive:
            return
        self._send({
            "player_num": self.player.num,
            "player_count": len(self.game.players),
            "position": self.player.pos,
            "map": self.game.island.map,
            "lighthouses": list(self.game.lighthouses.keys()),
        })
        reply = self._recv(self.INIT_TIMEOUT, self.INIT_TIMEOUT)
        if not (isinstance(reply, dict) and
                "name" in reply and
                isinstance(reply["name"], str)):
            raise CommError("Bot did not greet with name")
        self.player.name = reply["name"]

    def turn(self):
        if not self.alive:
            return
        lighthouses = []
        for lh in self.game.lighthouses.values():
            connections = [next(l for l in c if l is not lh.pos)
                            for c in self.game.conns if lh.pos in c]
            lighthouses.append({
                "position": lh.pos,
                "owner": lh.owner,
                "energy": lh.energy,
                "connections": connections,
                "have_key": lh.pos in self.player.keys,
            })
        self._send({
            "position": self.player.pos,
            "score": self.player.score,
            "energy": self.player.energy,
            "view": self.game.island.get_view(self.player.pos),
            "lighthouses": lighthouses,
        })
        move = self._recv(self.MOVE_TIMEOUT, self.MOVE_HARDTIMEOUT)
        if not isinstance(move, dict) or "command" not in move:
            raise CommError("Invalid command structure")
        try:
            if move["command"] == "pass":
                pass
            elif move["command"] == "move":
                if "x" not in move or "y" not in move:
                    raise engine.MoveError("Move command requires x, y")
                self.player.move((move["x"], move["y"]))
            elif move["command"] == "attack":
                if "energy" not in move or not isinstance(move["energy"], int):
                    raise engine.MoveError("Attack command requires integer energy")
                if self.player.pos not in self.game.lighthouses:
                    raise engine.MoveError("Player must be located at target lighthouse")
                self.game.lighthouses[self.player.pos].attack(self.player, move["energy"])
            elif move["command"] == "connect":
                if "destination" not in move:
                    raise engine.MoveError("Connect command requires destination")
                try:
                    dest = tuple(move["destination"])
                    hash(dest)
                except:
                    raise engine.MoveError("Destination must be a coordinate pair")
                self.game.connect(self.player, dest)
            else:
                raise engine.MoveError("Invalid command %r" % move["command"])
            self._send({"success": True})
        except engine.MoveError as e:
            #sys.stderr.write("Bot %r move error: %s\n" % (self.player.name, e.message))
            self._send({"success": False, "message": str(e)})

    def close(self):
        if self.alive:
            self.p.stdin.close()
            self.p.stdout.close()
            for i in range(100):
                time.sleep(0.01)
                if self.p.poll() is not None:
                    break
            else:
                self.p.terminate()
                for i in range(100):
                    time.sleep(0.01)
                    if self.p.poll() is not None:
                        break
                else:
                    self.p.kill()
            sys.stderr.write("Bot %r exit code: %r\n" % (self.player.name, self.p.wait()))
            self.alive = False

    def __del__(self):
        self.close()

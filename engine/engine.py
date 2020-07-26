#!/usr/bin/python3

import geom, math

class MoveError(Exception):
    pass

class GameError(Exception):
    pass

class Island(object):
    MAX_ENERGY = 100
    HORIZON = 3
    def __init__(self, island_map):
        self._island = island_map
        self.h = len(self._island)
        self.w = len(self._island[0])
        self._energymap = [[0] * self.w for i in range(self.h)]
        self._horizonmap = []
        dist = self.HORIZON
        for y in range(-dist, dist + 1):
            row = []
            for x in range(-dist, dist + 1):
                row.append(geom.dist((0,0), (x,y)) <= self.HORIZON)
            self._horizonmap.append(row)

        class _Energy(object):
            def __getitem__(unused, pos):
                x, y = pos
                if self[pos]:
                    return self._energymap[y][x]
                else:
                    return 0
            def __setitem__(unused, pos, val):
                x, y = pos
                if val > self.MAX_ENERGY:
                    val = self.MAX_ENERGY
                assert val >= 0
                if self[pos]:
                    self._energymap[y][x] = val
        self._energy = _Energy()

    def __getitem__(self, pos):
        x, y = pos
        if 0 <= x < self.w and 0 <= y < self.h:
            return self._island[y][x]
        else:
            return False

    @property
    def energy(self):
        return self._energy

    def get_view(self, pos):
        px, py = pos
        dist = self.HORIZON
        view = []
        for y in range(-dist, dist + 1):
            row = []
            for x in range(-dist, dist + 1):
                if self._horizonmap[y+dist][x+dist]:
                    row.append(self.energy[px+x, py+y])
                else:
                    row.append(-1)
            view.append(row)
        return view

    @property
    def map(self):
        return self._island

class Lighthouse(object):
    def __init__(self, game, pos):
        self.game = game
        self.pos = pos
        self.owner = None
        self.energy = 0

    def attack(self, player, strength):
        if not isinstance(strength, int):
            raise MoveError("Strength must be an int")
        if strength < 0:
            raise MoveError("Strength must be positive")
        if strength > player.energy:
            strength = player.energy
        player.energy -= strength
        if self.owner is not None and self.owner != player.num:
            d = min(self.energy, strength)
            self.decay(d)
            strength -= d
        if strength:
            self.owner = player.num
            self.energy += strength

    def decay(self, by):
        self.energy -= by
        if self.energy <= 0:
            self.energy = 0
            self.owner = None
            self.game.conns = set(i for i in self.game.conns if self.pos not in i)
            self.game.tris = dict(i for i in self.game.tris.items() if self.pos not in i[0])

class Player(object):
    def __init__(self, game, num, init_pos):
        self.num = num
        self.game = game
        self.pos = init_pos
        self.score = 0
        self.energy = 0
        self.keys = set()
        self.name = "Player %d" % num

    def move(self, delta):
        dx, dy = delta
        if dx not in (0, 1, -1) or dy not in (0, 1, -1):
            raise MoveError("Delta must be 1 cell away")
        new_pos = self.pos[0] + dx, self.pos[1] + dy
        if not self.game.island[new_pos]:
            raise MoveError("Target pos is not in island")
        self.pos = new_pos

class GameConfig(object):
    def __init__(self, mapfile):
        with open(mapfile, "r") as fd:
            lines = [l.replace("\n", "") for l in fd.readlines()]
        self.lighthouses = []
        players = []
        self.island = []
        for y, line in enumerate(lines[::-1]):
            row = []
            for x, c in enumerate(line):
                if c == "#":
                    row.append(0)
                elif c == "!":
                    row.append(1)
                    self.lighthouses.append((x,y))
                elif c == " ":
                    row.append(1)
                else:
                    row.append(1)
                    players.append((c, (x,y)))
            self.island.append(row)
        self.players = [pos for c, pos in sorted(players)]
        w = len(self.island[0])
        h = len(self.island)
        if not all(len(l) == w for l in self.island):
            raise GameError("All map rows must have the same width")
        if (not all(not i for i in self.island[0]) or
            not all(not i for i in self.island[-1]) or
            not all(not (i[0] or i[-1]) for i in self.island)):
            raise GameError("Map border must not be part of island")

class Game(object):
    RDIST = 5
    def __init__(self, cfg, numplayers=None):
        if numplayers is None:
            numplayers = len(cfg.players)
        assert numplayers <= len(cfg.players)
        self.island = Island(cfg.island)
        self.lighthouses = dict((x, Lighthouse(self, x)) for x in cfg.lighthouses)
        self.conns = set()
        self.tris = dict()
        self.players = [Player(self, i, pos) for i, pos in enumerate(cfg.players[:numplayers])]

    def connect(self, player, dest_pos):
        if player.pos not in self.lighthouses:
            raise MoveError("Player must be located at the origin lighthouse")
        if dest_pos not in self.lighthouses:
            raise MoveError("Destination must be an existing lighthouse")
        orig = self.lighthouses[player.pos]
        dest = self.lighthouses[dest_pos]
        if orig.owner != player.num or dest.owner != player.num:
            raise MoveError("Both lighthouses must be player-owned")
        if dest.pos not in player.keys:
            raise MoveError("Player does not have the destination key")
        if orig is dest:
            raise MoveError("Cannot connect lighthouse to itself")
        assert orig.energy and dest.energy
        pair = frozenset((orig.pos, dest.pos))
        if pair in self.conns:
            raise MoveError("Connection already exists")
        x0, x1 = sorted((orig.pos[0], dest.pos[0]))
        y0, y1 = sorted((orig.pos[1], dest.pos[1]))
        for lh in self.lighthouses:
            if (x0 <= lh[0] <= x1 and y0 <= lh[1] <= y1 and
                lh not in (orig.pos, dest.pos) and
                geom.colinear(orig.pos, dest.pos, lh)):
                raise MoveError("Connection cannot intersect a lighthouse")
        new_tris = set()
        for c in self.conns:
            if geom.intersect(tuple(c), (orig.pos, dest.pos)):
                raise MoveError("Connection cannot intersect another connection")
            if orig.pos in c:
                third = next(l for l in c if l != orig.pos)
                if frozenset((third, dest.pos)) in self.conns:
                    new_tris.add((orig.pos, dest.pos, third))

        player.keys.remove(dest.pos)
        self.conns.add(pair)
        for i in new_tris:
            self.tris[i] = [j for j in geom.render(i) if self.island[j]]

    def pre_round(self):
        for pos in self.lighthouses:
            for y in range(pos[1]-self.RDIST+1, pos[1]+self.RDIST):
                for x in range(pos[0]-self.RDIST+1, pos[0]+self.RDIST):
                    dist = geom.dist(pos, (x,y))
                    delta = int(math.floor(self.RDIST - dist))
                    if delta > 0:
                        self.island.energy[x,y] += delta
        player_posmap = dict()
        for player in self.players:
            if player.pos in player_posmap:
                player_posmap[player.pos].append(player)
            else:
                player_posmap[player.pos] = [player]
            if player.pos in self.lighthouses:
                player.keys.add(player.pos)
        for pos, players in player_posmap.items():
            energy = self.island.energy[pos] // len(players)
            for player in players:
                player.energy += energy
            self.island.energy[pos] = 0
        for lh in self.lighthouses.values():
            lh.decay(10)

    def post_round(self):
        for lh in self.lighthouses.values():
            if lh.owner is not None:
                self.players[lh.owner].score += 2
        for pair in self.conns:
            self.players[self.lighthouses[next(iter(pair))].owner].score += 2
        for tri, cells in self.tris.items():
            self.players[self.lighthouses[tri[0]].owner].score += len(cells)

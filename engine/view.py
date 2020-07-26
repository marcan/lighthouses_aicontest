#!/usr/bin/python3
import pygame, sys, time, math

CELL = 15

PLAYERC = [
    (255, 0, 0),
    (0, 0, 255),
    (0, 255, 0),
    (255, 255, 0),
    (0, 255, 255),
    (255, 0, 255),
    (255, 127, 0),
    (255, 127, 127),
]

class GameView(object):
    def __init__(self, game):
        self.game = game
        pygame.init()
        size = width, height = 640, 480
        self.screen = pygame.display.set_mode(size)
        self.scale = 1
        self.fw = self.game.island.w * CELL * self.scale
        self.fh = self.game.island.h * CELL * self.scale
        self.arena = pygame.Surface((self.fw, self.fh), 0, self.screen)
        self.nh = self.game.island.h - 1

    def _afill(self, pos, size, c):
        x0, y0 = pos
        w, h = size
        x0 *= self.scale
        y0 *= self.scale
        w *= self.scale
        h *= self.scale
        self.arena.fill(c, (x0, y0, w, h))

    def _aaline(self, pos1, pos2, c):
        x0, y0 = pos1
        x1, y1 = pos2
        x0 *= self.scale
        y0 *= self.scale
        x1 *= self.scale
        y1 *= self.scale
        for dx in range(self.scale):
            for dy in range(self.scale):
                pygame.draw.line(self.arena, c, (x0+dx, y0+dy), (x1+dx, y1+dy))

    def _diamond(self, pos, size, c, width=0):
        cx, cy = pos
        cx *= self.scale
        cy *= self.scale
        size *= self.scale
        points = [
            (cx - size, cy),
            (cx, cy - size),
            (cx + size, cy),
            (cx, cy + size),
        ]
        pygame.draw.polygon(self.arena, c, points, width)

    def cmul(self, col, mul):
        r, g, b = col
        return int(r * mul), int(g * mul), int(b * mul)

    def calpha(self, col1, col2, a):
        r1, g1, b1 = col1
        r2, g2, b2 = col2
        return (int(r2 * a + r1 * (1-a)),
                int(g2 * a + g1 * (1-a)),
                int(b2 * a + b1 * (1-a)))

    def draw_cell(self, pos):
        cx, cy = pos
        py = (self.nh - cy) * CELL
        px = cx * CELL
        c = int(self.game.island.energy[cx, cy] / 100.0 * 25)
        bg = tuple(map(int,(25+c*0.8, 25+c*0.8, 25+c)))

        for vertices, fill in self.game.tris.items():
            if (cx, cy) in fill:
                owner = self.game.lighthouses[vertices[0]].owner
                bg = self.calpha(bg, PLAYERC[owner], 0.15)

        self._afill((px, py), (CELL, CELL), bg)
        self._afill((px + CELL//2, py + CELL//2), (1,1), (255,255,255))

        cplayers = [i for i in self.game.players if i.pos == (cx, cy)]
        if cplayers:
            nx = int(math.ceil(math.sqrt(len(cplayers))))
            wx = (CELL - 4) / nx
            ny = int(math.ceil(len(cplayers)/nx))
            wy = (CELL - 4) / ny
            for i, player in enumerate(cplayers):
                iy = i // nx
                ix = i % nx
                color = self.cmul(PLAYERC[player.num], 0.5)
                sx, sy = int(px + 2 + ix * wx), int(py + 2 + iy * wy)
                ex, ey = int(px + 2 + (ix + 1) * wx), int(py + 2 + (iy + 1) * wy)
                self._afill((sx, sy), (ex - sx, ey - sy), color)

        if (cx, cy) in self.game.lighthouses:
            lh = self.game.lighthouses[cx, cy]
            color = (192, 192, 192)
            if lh.owner is not None:
                color = PLAYERC[lh.owner]
            self._diamond((px + CELL//2, py + CELL//2), 4, color, 0)

    def update(self):
        self.arena.fill((0, 0, 0))
        for cy in range(self.game.island.h):
            for cx in range(self.game.island.w):
                if self.game.island[cx, cy]:
                    self.draw_cell((cx, cy))
        for (x0, y0), (x1, y1) in self.game.conns:
            owner = self.game.lighthouses[x0, y0].owner
            color = PLAYERC[owner]
            y0, y1 = self.nh - y0, self.nh - y1
            self._aaline((x0 * CELL + CELL//2, y0 * CELL + CELL//2),
                        (x1 * CELL + CELL//2, y1 * CELL + CELL//2), color)
        self.screen.blit(self.arena, (0,0))
        pygame.display.flip()

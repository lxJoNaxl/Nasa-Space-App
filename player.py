import pygame
from sprite import Sprite
from input import is_key_pressed

movement_speed = 3
PLAYER_SIZE = 48   # tamaño del personaje en pantalla (px)

class Player(Sprite):
    def __init__(self, image, x, y):
        super().__init__(image, x, y)
        # Escalamos solo la copia de este jugador
        self.image = pygame.transform.scale(self.image, (PLAYER_SIZE, PLAYER_SIZE))

    def rect(self):
        w, h = self.image.get_size()
        # Hitbox pequeña en los pies del personaje
        return pygame.Rect(int(self.x) + 8, int(self.y) + h // 2, w - 16, h // 2)

    def update(self, game_map):
        dx = dy = 0
        if is_key_pressed(pygame.K_w): dy -= movement_speed
        if is_key_pressed(pygame.K_s): dy += movement_speed
        if is_key_pressed(pygame.K_a): dx -= movement_speed
        if is_key_pressed(pygame.K_d): dx += movement_speed

        # Un eje a la vez, para poder deslizarse por las paredes
        self.x += dx
        if game_map.collides(self.rect()):
            self.x -= dx
        self.y += dy
        if game_map.collides(self.rect()):
            self.y -= dy

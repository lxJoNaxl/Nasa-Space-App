import pygame
from sprite import Sprite
from input import is_key_pressed

movement_speed = 3
PLAYER_HEIGHT = 80   # altura del astronauta en el mapa (px). Súbela o bájala a tu gusto.

class Player(Sprite):
    def __init__(self, image, x, y):
        super().__init__(image, x, y)

        # 1) Recortar el espacio transparente alrededor del dibujo
        img = self.image
        caja = img.get_bounding_rect()
        if caja.width > 0 and caja.height > 0:
            img = img.subsurface(caja).copy()

        # 2) Escalar a la altura deseada SIN deformar (mantiene la proporción)
        w, h = img.get_size()
        nuevo_w = max(1, round(w * PLAYER_HEIGHT / h))
        self.image_der = pygame.transform.smoothscale(img, (nuevo_w, PLAYER_HEIGHT))
        self.image_izq = pygame.transform.flip(self.image_der, True, False)
        self.image = self.image_der

    def rect(self):
        w, h = self.image.get_size()
        # Hitbox pequeña solo en los pies, para poder pasar cerca de los muebles
        return pygame.Rect(int(self.x) + w // 4, int(self.y) + h - 18, w // 2, 18)

    def update(self, game_map):
        dx = dy = 0
        if is_key_pressed(pygame.K_w) or is_key_pressed(pygame.K_UP): dy -= movement_speed
        if is_key_pressed(pygame.K_s) or is_key_pressed(pygame.K_DOWN): dy += movement_speed
        if is_key_pressed(pygame.K_a) or is_key_pressed(pygame.K_LEFT):
            dx -= movement_speed
            self.image = self.image_izq      # mira a la izquierda
        if is_key_pressed(pygame.K_d) or is_key_pressed(pygame.K_RIGHT):
            dx += movement_speed
            self.image = self.image_der      # mira a la derecha

        # Un eje a la vez, para poder deslizarse por las paredes
        self.x += dx
        if game_map.collides(self.rect()):
            self.x -= dx
        self.y += dy
        if game_map.collides(self.rect()):
            self.y -= dy

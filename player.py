import os
import pygame
from sprite import Sprite
from input import is_key_pressed

movement_speed = 3
PLAYER_HEIGHT = 80   # altura del astronauta en el mapa (px). Súbela o bájala a tu gusto.
T_PASO = 0.18        # segundos entre cada cambio de sprite al caminar
ARCHIVO_MANO_IZQ = "AstroManoAlzadaIzquierda.png"   # tecla A
ARCHIVO_MANO_DER = "AstroManoAlzadaDerecha.png"     # tecla D


def _recortar(img):
    """Quita el espacio transparente alrededor del dibujo."""
    caja = img.get_bounding_rect()
    if caja.width > 0 and caja.height > 0:
        return img.subsurface(caja).copy()
    return img


def _cargar_variante(ruta, size):
    """PNG recortado y ajustado al tamaño del sprite normal (None si no existe)."""
    try:
        img = _recortar(pygame.image.load(ruta).convert_alpha())
    except (pygame.error, FileNotFoundError, OSError):
        print("No se encontró", ruta)
        return None
    ancho, alto = size
    w, h = img.get_size()
    f = min(ancho / w, alto / h)
    img = pygame.transform.smoothscale(img, (max(1, round(w * f)), max(1, round(h * f))))
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.blit(img, img.get_rect(midbottom=(ancho // 2, alto)))
    return surf


class Player(Sprite):
    def __init__(self, image, x, y):
        super().__init__(image, x, y)

        # 1) Recortar el espacio transparente alrededor del dibujo
        img = _recortar(self.image)

        # 2) Escalar a la altura deseada SIN deformar (mantiene la proporción)
        w, h = img.get_size()
        nuevo_w = max(1, round(w * PLAYER_HEIGHT / h))
        self.image_der = pygame.transform.smoothscale(img, (nuevo_w, PLAYER_HEIGHT))
        self.image_izq = pygame.transform.flip(self.image_der, True, False)
        self.image = self.image_der

        # 3) Variantes con la mano alzada (mismo tamaño que el sprite normal,
        #    se buscan en la misma carpeta que ASTRONAUTA.png)
        carpeta = os.path.dirname(image)
        size = self.image_der.get_size()
        self.mano_izq = _cargar_variante(os.path.join(carpeta, ARCHIVO_MANO_IZQ), size)
        self.mano_der = _cargar_variante(os.path.join(carpeta, ARCHIVO_MANO_DER), size)

        self.mirando = "der"
        self._caminando = False
        self._t_inicio_paso = 0

    def rect(self):
        w, h = self.image.get_size()
        # Hitbox pequeña solo en los pies, para poder pasar cerca de los muebles
        return pygame.Rect(int(self.x) + w // 4, int(self.y) + h - 18, w // 2, 18)

    def reposo(self):
        """Sprite normal mirando hacia donde miraba (pausas, reparar, paneles, etc.)."""
        self._caminando = False
        self.image = self.image_izq if self.mirando == "izq" else self.image_der

    def _elegir_sprite(self, izq, der):
        """A -> alterna normal/mano izquierda.  D -> alterna normal/mano derecha."""
        if izq == der:                  # quieto (o A y D a la vez, que se cancelan)
            self.reposo()
            return
        ahora = pygame.time.get_ticks()
        if not self._caminando:         # acaba de empezar a caminar
            self._caminando = True
            self._t_inicio_paso = ahora
        if self.mirando == "izq":
            base, mano = self.image_izq, self.mano_izq
        else:
            base, mano = self.image_der, self.mano_der
        alterna = int((ahora - self._t_inicio_paso) / 1000.0 / T_PASO) % 2 == 1
        self.image = mano if (alterna and mano is not None) else base

    def update(self, game_map):
        dx = dy = 0
        izq = is_key_pressed(pygame.K_a)
        der = is_key_pressed(pygame.K_d)
        if is_key_pressed(pygame.K_w): dy -= movement_speed
        if is_key_pressed(pygame.K_s): dy += movement_speed
        if izq:
            dx -= movement_speed
            self.mirando = "izq"
        if der:
            dx += movement_speed
            self.mirando = "der"
        self._elegir_sprite(izq, der)

        # Un eje a la vez, para poder deslizarse por las paredes
        self.x += dx
        if game_map.collides(self.rect()):
            self.x -= dx
        self.y += dy
        if game_map.collides(self.rect()):
            self.y -= dy
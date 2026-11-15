import os
import pygame
from sprite import Sprite
from input import is_key_pressed

movement_speed = 3
PLAYER_HEIGHT = 80   # altura del astronauta en el mapa (px). Súbela o bájala a tu gusto.
T_PASO = 0.18        # segundos entre cada cambio de sprite al caminar
ARCHIVO_MANO_IZQ = "AstroManoAlzadaIzquierda.png"   # tecla A / flecha izquierda
ARCHIVO_MANO_DER = "AstroManoAlzadaDerecha.png"     # tecla D / flecha derecha


def _recortar(img):
    """Quita el espacio transparente alrededor del dibujo."""
    caja = img.get_bounding_rect()
    if caja.width > 0 and caja.height > 0:
        return img.subsurface(caja).copy()
    return img


def _leer_variante(ruta):
    """PNG recortado tal como está en disco (None si no existe)."""
    try:
        return _recortar(pygame.image.load(ruta).convert_alpha())
    except (pygame.error, FileNotFoundError, OSError):
        print("No se encontró", ruta)
        return None


def _ajustar_variante(img, size):
    """Ajusta el PNG recortado al tamaño del sprite normal (None si no hay imagen)."""
    if img is None:
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

        # 1) Recortar el espacio transparente alrededor del dibujo (se guarda para poder reescalar)
        self._base = _recortar(self.image)

        # 2) Variantes con la mano alzada (se buscan en la misma carpeta que ASTRONAUTA.png)
        carpeta = os.path.dirname(image)
        self._mano_izq_orig = _leer_variante(os.path.join(carpeta, ARCHIVO_MANO_IZQ))
        self._mano_der_orig = _leer_variante(os.path.join(carpeta, ARCHIVO_MANO_DER))

        self.mirando = "der"
        self._caminando = False
        self._t_inicio_paso = 0
        self.altura = PLAYER_HEIGHT
        self._escalar(PLAYER_HEIGHT)
        self.image = self.image_der

    def _escalar(self, altura):
        """Escala todos los sprites a 'altura' px SIN deformar (mantiene la proporción)."""
        w, h = self._base.get_size()
        nuevo_w = max(1, round(w * altura / h))
        self.image_der = pygame.transform.smoothscale(self._base, (nuevo_w, altura))
        self.image_izq = pygame.transform.flip(self.image_der, True, False)
        size = self.image_der.get_size()
        self.mano_izq = _ajustar_variante(self._mano_izq_orig, size)
        self.mano_der = _ajustar_variante(self._mano_der_orig, size)
        self.altura = altura

    def set_altura(self, altura):
        """Cambia el tamaño del astronauta. Los pies se quedan en el mismo punto del mapa."""
        altura = max(20, int(altura))
        if altura == self.altura:
            return
        w0, h0 = self.image.get_size()
        self._escalar(altura)
        self.reposo()
        w1, h1 = self.image.get_size()
        self.x += (w0 - w1) / 2
        self.y += h0 - h1

    def convertir_pos(self, x, y, altura_vieja):
        """Pasa una posición guardada con otra altura de astronauta al tamaño actual (pies fijos)."""
        w, h = self._base.get_size()
        w0 = max(1, round(w * altura_vieja / h))
        w1 = self.image_der.get_width()
        return x + (w0 - w1) / 2, y + altura_vieja - self.image_der.get_height()

    def rect(self):
        w, h = self.image.get_size()
        # Hitbox pequeña solo en los pies, para poder pasar cerca de los muebles
        return pygame.Rect(int(self.x) + w // 4, int(self.y) + h - 18, w // 2, 18)

    def reposo(self):
        """Sprite normal mirando hacia donde miraba (pausas, reparar, paneles, etc.)."""
        self._caminando = False
        self.image = self.image_izq if self.mirando == "izq" else self.image_der

    def _elegir_sprite(self, izq, der):
        """Izquierda -> alterna normal/mano izquierda.  Derecha -> alterna normal/mano derecha."""
        if izq == der:                  # quieto (o izquierda y derecha a la vez, que se cancelan)
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
        izq = is_key_pressed(pygame.K_a) or is_key_pressed(pygame.K_LEFT)
        der = is_key_pressed(pygame.K_d) or is_key_pressed(pygame.K_RIGHT)
        if is_key_pressed(pygame.K_w) or is_key_pressed(pygame.K_UP): dy -= movement_speed
        if is_key_pressed(pygame.K_s) or is_key_pressed(pygame.K_DOWN): dy += movement_speed
        if izq:
            dx -= movement_speed
            self.mirando = "izq"         # mira a la izquierda
        if der:
            dx += movement_speed
            self.mirando = "der"         # mira a la derecha
        self._elegir_sprite(izq, der)

        # Un eje a la vez, para poder deslizarse por las paredes
        self.x += dx
        if game_map.collides(self.rect()):
            self.x -= dx
        self.y += dy
        if game_map.collides(self.rect()):
            self.y -= dy
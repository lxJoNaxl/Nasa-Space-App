import sys
import os
import pygame

def ruta_recurso(ruta_relativa):
    """Obtiene la ruta correcta si está empaquetado o no."""
    try:
        # PyInstaller crea una carpeta temporal en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, ruta_relativa)

class TileKind:
    def __init__(self, name, image, is_solid):
        self.name = name
        self.image = pygame.image.load(image)
        self.is_solid = is_solid

class Map:
    """Mapa antiguo basado en tiles (ya no se usa, se deja por si lo quieres)."""
    def __init__(self, map_file, tile_kinds, tile_size):
        self.tile_kinds = tile_kinds
        with open(map_file, "r") as file:
            data = file.read()
        self.tiles = []
        for line in data.split('\n'):
            self.tiles.append([int(n) for n in line])
        self.tile_size = tile_size

    def draw(self, screen):
        for y, row in enumerate(self.tiles):
            for x, tile in enumerate(row):
                screen.blit(self.tile_kinds[tile].image,
                            (x * self.tile_size, y * self.tile_size))

class ImageMap:
    """Mapa hecho con una sola imagen grande + rectángulos de colisión."""
    def __init__(self, image_path, solids):
        self.image = pygame.image.load(image_path).convert()
        self.width, self.height = self.image.get_size()
        # Rectángulos (x, y, ancho, alto) donde NO se puede caminar
        self.solids = [pygame.Rect(r) for r in solids]

    def draw(self, screen, camera):
        screen.blit(self.image, (-camera[0], -camera[1]))

    def collides(self, rect):
        # Fuera del mapa también cuenta como choque
        if rect.left < 0 or rect.top < 0 or rect.right > self.width or rect.bottom > self.height:
            return True
        return any(rect.colliderect(s) for s in self.solids)

    def draw_debug(self, screen, camera):
        for s in self.solids:
            pygame.draw.rect(screen, (255, 0, 0), s.move(-camera[0], -camera[1]), 2)

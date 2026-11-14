import pygame

sprites = []
loaded = {}

class Sprite:
    def __init__(self, image, x, y):
        if image in loaded:
            self.image = loaded[image]
        else:
            try:
                self.image = pygame.image.load(image).convert_alpha()
            except (pygame.error, FileNotFoundError):
                # Si no existe la imagen, usamos un cuadrado de color
                self.image = pygame.Surface((32, 32))
                self.image.fill((0, 220, 255))
            loaded[image] = self.image
        self.x = x
        self.y = y
        sprites.append(self)

    def delete(self):
        sprites.remove(self)

    def draw(self, screen, camera=(0, 0)):
        screen.blit(self.image, (self.x - camera[0], self.y - camera[1]))

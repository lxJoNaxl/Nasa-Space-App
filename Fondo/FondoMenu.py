import os
import cv2
import pygame


class FondoMenu:
    def __init__(self, ruta_video, size, fallback_color=(15, 15, 30), loop=True):
        # Permite pasar rutas relativas como "videos/fondo.mp4" igual que ImageMap
        if not os.path.isabs(ruta_video):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ruta_video = os.path.join(base_dir, ruta_video)

        self.size = size
        self.fallback_color = fallback_color
        self.loop = loop
        self.surface = None

        self.cap = cv2.VideoCapture(ruta_video)
        self.activo = self.cap.isOpened()

        # Detecta los FPS reales del video para reproducirlo a velocidad normal
        fps = self.cap.get(cv2.CAP_PROP_FPS) if self.activo else 30.0
        if not fps or fps <= 0:
            fps = 30.0
        self.frame_delay = 1000.0 / fps
        self.last_update = 0

    def _leer_siguiente_frame(self):
        if not self.activo:
            return

        ret, frame = self.cap.read()
        if not ret and self.loop:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_LINEAR)
            surf = pygame.image.frombuffer(frame.tobytes(), self.size, "RGB")
            self.surface = surf.convert()

    def draw(self, screen):
        """Actualiza el fotograma si corresponde y lo dibuja en screen."""
        ahora = pygame.time.get_ticks()
        if self.surface is None or (ahora - self.last_update) >= self.frame_delay:
            self._leer_siguiente_frame()
            self.last_update = ahora

        if self.surface is not None:
            screen.blit(self.surface, (0, 0))
        else:
            screen.fill(self.fallback_color)

    def reset(self):
        """Reinicia el video al primer fotograma."""
        if self.activo:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.surface = None

    def release(self):
        """Libera el archivo de video al cerrar el juego."""
        if self.cap is not None:
            self.cap.release()
import math
import pygame

# ----------------------------------------------------------------------
#  Dron de la misión a Marte
#  Secuencia: sube (se despliega) -> ida (se aleja hacia el fondo)
#             -> explora (barra de progreso) -> vuelta -> baja (aterriza)
# ----------------------------------------------------------------------
HORIZONTE = 0.54       # donde empieza el suelo en Escena_Marte.jpeg (fracción del alto)

# Dónde está posado el dron (fracción del mapa). Punto de interacción = alrededor de él.
PAD_X, PAD_Y = 0.57, 0.80
ALTO_SUELO = 0.11      # alto del dron posado (fracción del alto del mapa)
ALTURA_VUELO = 0.07    # cuánto se eleva sobre el suelo (fracción del alto del mapa)
LEJOS_X, LEJOS_Y = 0.66, 0.585   # punto lejano, cerca del horizonte (fracción del mapa)

T_SUBE = 1.8           # segundos desplegándose y elevándose
T_IDA = 3.5            # segundos alejándose hacia el fondo
T_EXPLORA = 8.0        # segundos que tarda la barra de exploración
T_VUELTA = 3.5         # segundos regresando
T_BAJA = 1.8           # segundos aterrizando


def _ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def _lerp(a, b, p):
    return a + (b - a) * p


class DronMarte:
    def __init__(self, ruta_png, map_w, map_h):
        self.w, self.h = map_w, map_h
        try:
            img = pygame.image.load(ruta_png).convert_alpha()
            caja = img.get_bounding_rect()
            if caja.width > 0 and caja.height > 0:
                img = img.subsurface(caja).copy()
        except (pygame.error, FileNotFoundError, OSError):
            print("No se encontró", ruta_png)
            img = pygame.Surface((80, 70), pygame.SRCALPHA)
            img.fill((200, 200, 200, 255))

        alto = max(8, int(map_h * ALTO_SUELO))
        ancho = max(8, round(img.get_width() * alto / img.get_height()))
        self.base = pygame.transform.smoothscale(img, (ancho, alto))

        self.pad_x, self.pad_y = int(map_w * PAD_X), int(map_h * PAD_Y)
        self.lejos_x, self.lejos_y = map_w * LEJOS_X, map_h * LEJOS_Y
        self.horizonte_y = map_h * HORIZONTE
        self.vuelo_px = map_h * ALTURA_VUELO

        # Rectángulo del dron posado (para colisión, zona de interacción y orden de dibujo)
        self.rect_suelo = pygame.Rect(0, 0, ancho, alto)
        self.rect_suelo.midbottom = (self.pad_x, self.pad_y)

        self.fase = "pad"      # pad | sube | ida | explora | vuelta | baja | hecho
        self.t0 = 0

    # ------------------------------------------------------------------
    #  Control
    # ------------------------------------------------------------------
    def iniciar(self):
        if self.fase == "pad":
            self._ir("sube")

    @property
    def ocupado(self):
        return self.fase in ("sube", "ida", "explora", "vuelta", "baja")

    @property
    def hecho(self):
        return self.fase == "hecho"

    def _ir(self, fase):
        self.fase = fase
        self.t0 = pygame.time.get_ticks()

    def _t(self):
        return (pygame.time.get_ticks() - self.t0) / 1000.0

    def update(self):
        t = self._t()
        if self.fase == "sube" and t >= T_SUBE:
            self._ir("ida")
        elif self.fase == "ida" and t >= T_IDA:
            self._ir("explora")
        elif self.fase == "explora" and t >= T_EXPLORA:
            self._ir("vuelta")
        elif self.fase == "vuelta" and t >= T_VUELTA:
            self._ir("baja")
        elif self.fase == "baja" and t >= T_BAJA:
            self.fase = "hecho"

    # ------------------------------------------------------------------
    #  Posición: (x suelo, y suelo, altura 0..1, volando)
    # ------------------------------------------------------------------
    def _estado(self):
        t = self._t()
        f = self.fase
        if f in ("pad", "hecho"):
            return self.pad_x, self.pad_y, 0.0, False
        if f == "sube":
            return self.pad_x, self.pad_y, _ease(t / T_SUBE), True
        if f == "ida":
            p = _ease(t / T_IDA)
            return (_lerp(self.pad_x, self.lejos_x, p),
                    _lerp(self.pad_y, self.lejos_y, p), 1.0, True)
        if f == "explora":
            # Se queda al fondo, moviéndose un poco como si explorara
            env = math.sin(math.pi * min(1.0, t / T_EXPLORA))  # 0 al empezar y al terminar (sin saltos)
            return (self.lejos_x + math.sin(t * 1.3) * self.w * 0.025 * env,
                    self.lejos_y + math.sin(t * 0.9) * self.h * 0.004 * env, 1.0, True)
        if f == "vuelta":
            p = _ease(t / T_VUELTA)
            return (_lerp(self.lejos_x, self.pad_x, p),
                    _lerp(self.lejos_y, self.pad_y, p), 1.0, True)
        # baja
        return self.pad_x, self.pad_y, 1.0 - _ease(t / T_BAJA), True

    @property
    def progreso(self):
        """0..1 de la barra de exploración."""
        if self.fase == "explora":
            return min(1.0, self._t() / T_EXPLORA)
        if self.fase in ("vuelta", "baja", "hecho"):
            return 1.0
        return 0.0

    # ------------------------------------------------------------------
    #  Dibujo en el mapa (coordenadas del mapa menos la cámara)
    # ------------------------------------------------------------------
    def draw(self, surf, camera):
        gx, gy, alt, vuela = self._estado()
        ahora = pygame.time.get_ticks() / 1000.0

        # Perspectiva: cuanto más cerca del horizonte, más pequeño
        den = max(1.0, self.pad_y - self.horizonte_y)
        esc = max(0.12, min(1.0, (gy - self.horizonte_y) / den))
        bw, bh = self.base.get_size()
        iw, ih = max(2, int(bw * esc)), max(2, int(bh * esc))
        img = pygame.transform.scale(self.base, (iw, ih))

        altura = alt * self.vuelo_px * esc
        if vuela:
            altura += math.sin(ahora * 9.0) * 2.0 * esc   # vibración de vuelo

        sx, sy = int(gx - camera[0]), int(gy - camera[1])

        # Sombra en el suelo (se achica y se aclara al elevarse)
        sw = max(4, int(iw * (0.85 - 0.25 * alt)))
        sh = max(2, int(sw * 0.22))
        sombra = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (60, 20, 15, int(120 - 50 * alt)), sombra.get_rect())
        surf.blit(sombra, sombra.get_rect(center=(sx, sy - sh // 4)))

        # Polvo al despegar y al aterrizar
        if self.fase in ("sube", "baja") and alt < 0.85:
            self._polvo(surf, sx, sy, iw, 1.0 - alt, ahora)

        # Dron
        dest = img.get_rect(midbottom=(sx, int(sy - altura)))
        surf.blit(img, dest)

        # Efecto de rotor girando (disco translúcido sobre las aspas)
        if vuela and alt > 0.15:
            ancho = int(iw * 0.95)
            alto = max(2, int(ih * (0.20 + 0.04 * math.sin(ahora * 40.0))))
            disco = pygame.Surface((ancho, alto), pygame.SRCALPHA)
            pygame.draw.ellipse(disco, (40, 40, 55, 85), disco.get_rect())
            surf.blit(disco, disco.get_rect(center=(dest.centerx, dest.y + int(ih * 0.31))))

    def _polvo(self, surf, sx, sy, iw, fuerza, ahora):
        n = 7
        capa = pygame.Surface((iw * 2, max(8, iw // 2)), pygame.SRCALPHA)
        cx, cy = capa.get_width() // 2, capa.get_height() // 2
        for k in range(n):
            ang = k / n * math.tau + ahora * 3.0
            r = iw * (0.35 + 0.25 * ((k * 37) % 10) / 10.0) * (0.6 + 0.4 * fuerza)
            x = cx + math.cos(ang) * r
            y = cy + math.sin(ang) * r * 0.25
            rad = max(2, int(iw * 0.07 * (0.5 + fuerza)))
            pygame.draw.circle(capa, (225, 150, 120, int(90 * fuerza)), (int(x), int(y)), rad)
        surf.blit(capa, capa.get_rect(center=(sx, sy)))

    # ------------------------------------------------------------------
    #  Mensaje + barra de progreso en pantalla (como la de reparar el robot)
    # ------------------------------------------------------------------
    def dibujar_hud(self, screen, font, screen_w, screen_h):
        textos = {
            "sube": "Desplegando el dron...",
            "ida": "El dron se dirige a la zona de exploración...",
            "explora": "Explorando el terreno marciano...",
            "vuelta": "El dron regresa a la base...",
            "baja": "Aterrizando...",
        }
        if self.fase not in textos:
            return
        prog = self.progreso
        msg = textos[self.fase]
        if self.fase == "explora":
            msg += f"  {int(prog * 100)}%"
        color = (255, 255, 0)

        bw = 420
        box = pygame.Rect(0, 0, bw + 40, 74)
        box.midbottom = (screen_w // 2, screen_h - 40)
        pygame.draw.rect(screen, (0, 0, 0), box, border_radius=8)
        pygame.draw.rect(screen, color, box, 2, border_radius=8)
        img = font.render(msg, True, color)
        screen.blit(img, img.get_rect(midtop=(box.centerx, box.y + 10)))
        pygame.draw.rect(screen, (40, 45, 70), (box.x + 20, box.y + 44, bw, 16), border_radius=6)
        if prog > 0:
            pygame.draw.rect(screen, (90, 230, 120),
                             (box.x + 20, box.y + 44, int(bw * prog), 16), border_radius=6)

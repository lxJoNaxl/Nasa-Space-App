"""
Animación de despegue del cohete.

Se usa desde main.py así:
    anim = Despegue(screen, carpeta_images, idx_cohete, idx_orbita,
                    nombre_destino, nombre_mision, nombre_cohete, puntos)
    anim.update(); anim.draw()          # una vez por frame
    anim.terminado                      # True cuando aparece el cartel final
    anim.saltar()                       # salta directo al final

Cada cohete tiene su propia secuencia:
  - Electron      : ascenso directo a órbita.
  - Falcon 9      : separación de etapa (destello + corte breve de motores).
  - Falcon Heavy  : los 2 boosters laterales se sueltan y caen, luego separa etapa.
Al final aparece el destino (Tierra, Luna o Marte) según la órbita elegida.
"""
import math
import os
import random

import pygame

# ----------------------------------------------------------------------
#  DATOS POR COHETE  (coordenadas del PNG original de 1000x1000)
#    crop     : zona del PNG que se usa SIN las llamas dibujadas
#    borrar   : zonas a borrar (llamas dibujadas de los boosters)
#    motores  : (x, y, ancho, indice_booster | None) donde sale la llama
#    boosters : rectángulos que se separan del cuerpo central
#    t_fin    : segundos de vuelo (desde el despegue) hasta llegar a destino
# ----------------------------------------------------------------------
COHETES = [
    {   # Electron
        "img": "COHETE__NIVEL1.png", "crop": (240, 20, 400, 370), "borrar": [],
        "motores": [(320, 370, 90, None)], "boosters": [], "t_fin": 8.0,
        "eventos": [(3.0, "texto", "MAX-Q: MÁXIMA PRESIÓN")],
    },
    {   # Falcon 9
        "img": "COHETE_NIVEL2.png", "crop": (250, 180, 490, 760), "borrar": [],
        "motores": [(300, 760, 60, None), (440, 760, 60, None)], "boosters": [], "t_fin": 9.0,
        "eventos": [(3.0, "texto", "MAX-Q: MÁXIMA PRESIÓN"),
                    (5.0, "etapa", "SEPARACIÓN DE ETAPA")],
    },
    {   # Falcon Heavy
        "img": "COHETE_NIVEL3.png", "crop": (170, 170, 570, 760),
        "borrar": [(170, 688, 80, 72), (490, 688, 90, 72)],
        "motores": [(300, 760, 60, None), (440, 760, 60, None), (215, 688, 40, 0), (525, 688, 40, 1)],
        "boosters": [(170, 455, 80, 290), (490, 455, 90, 290)], "t_fin": 10.0,
        "eventos": [(3.0, "texto", "MAX-Q: MÁXIMA PRESIÓN"),
                    (4.5, "boosters", "SEPARACIÓN DE BOOSTERS"),
                    (6.8, "etapa", "SEPARACIÓN DE ETAPA")],
    },
]

# Destino según la órbita (índice de ORBITAS en main.py)
#   R = radio (fracción del alto de pantalla), tgt = posición final (fracciones), off = de dónde entra
DESTINOS = {
    0: {"tipo": "tierra", "R": 0.55, "tgt": (0.5, 1.27), "off": (0.0, 0.5), "km": 400},
    1: {"tipo": "tierra", "R": 0.55, "tgt": (0.5, 1.27), "off": (0.0, 0.5), "km": 800},
    2: {"tipo": "tierra", "R": 0.30, "tgt": (0.80, 0.80), "off": (0.2, 0.4), "km": 35786},
    3: {"tipo": "luna", "R": 0.20, "tgt": (0.82, 0.30), "off": (0.3, 0.0), "km": 384400},
    4: {"tipo": "marte", "R": 0.25, "tgt": (0.82, 0.30), "off": (0.3, 0.0), "km": 225000000},
}

T_IGN = 3.0     # segundo de la ignición
T_LIFT = 4.2    # segundo en que se suelta el cohete
T_FALLA = 3.0   # segundos de vuelo (tras soltarse) a los que se daña el cohete si despegaste con errores
T_FALLA_CARD = 3.4  # segundos desde la falla hasta el cartel de "MISIÓN FALLIDA"

CIELO_DIA = ((40, 90, 190), (170, 215, 245))
CIELO_ESPACIO = ((3, 3, 12), (8, 10, 30))

# capas de la llama: (ratio ancho, fracción de largo, color)
CAPAS_LLAMA = [
    (1.00, 1.00, (237, 28, 36)),
    (0.78, 0.78, (255, 106, 0)),
    (0.52, 0.58, (255, 196, 32)),
    (0.26, 0.36, (255, 244, 190)),
]


def _clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_col(c1, c2, t):
    return (int(_lerp(c1[0], c2[0], t)), int(_lerp(c1[1], c2[1], t)), int(_lerp(c1[2], c2[2], t)))


def _ease(t):
    t = _clamp(t)
    return t * t * (3 - 2 * t)


def _miles(n):
    return f"{int(n):,}".replace(",", ".")


def _esfera(R, tipo, seed):
    """Dibuja un planeta/luna como superficie circular con sombra."""
    rng = random.Random(seed)
    d = 2 * R
    tmp = pygame.Surface((d, d))
    if tipo == "tierra":
        tmp.fill((30, 90, 200))
        for _ in range(14):
            x, y = rng.randint(0, d), rng.randint(0, d)
            w, h = rng.randint(R // 5, R // 2), rng.randint(R // 8, R // 3)
            pygame.draw.ellipse(tmp, (50, 140, 70) if rng.random() < 0.75 else (150, 130, 80), (x - w // 2, y - h // 2, w, h))
        for _ in range(16):
            x, y = rng.randint(0, d), rng.randint(0, d)
            pygame.draw.ellipse(tmp, (225, 235, 245), (x - R // 3, y, R // 2, max(4, R // 14)))
    elif tipo == "luna":
        tmp.fill((170, 170, 176))
        for _ in range(22):
            x, y, r = rng.randint(0, d), rng.randint(0, d), rng.randint(max(3, R // 14), max(4, R // 5))
            pygame.draw.circle(tmp, (125, 125, 132), (x, y), r)
            pygame.draw.circle(tmp, (190, 190, 196), (x - r // 4, y - r // 4), max(2, r - r // 4))
    else:  # marte
        tmp.fill((190, 90, 50))
        for _ in range(16):
            x, y = rng.randint(0, d), rng.randint(0, d)
            w, h = rng.randint(R // 4, R // 2), rng.randint(R // 8, R // 3)
            pygame.draw.ellipse(tmp, (150, 65, 40) if rng.random() < 0.6 else (215, 130, 80), (x - w // 2, y - h // 2, w, h))
        pygame.draw.ellipse(tmp, (240, 240, 245), (R - R // 3, 0, R * 2 // 3, R // 6))
    s = tmp.convert_alpha()
    mask = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (R, R), R)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    # sombra: zona iluminada arriba a la izquierda
    sombra = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(sombra, (0, 0, 0, 150), (R, R), R)
    pygame.draw.circle(sombra, (0, 0, 0, 0), (int(R * 0.7), int(R * 0.7)), int(R * 1.05))
    s.blit(sombra, (0, 0))
    return s


class Despegue:
    def __init__(self, screen, carpeta_img, idx_cohete, idx_orbita,
                 destino, mision, cohete, puntos, falla=None, perdida=0):
        # falla = lista de causas (texto) si se despegó con la revisión en rojo; None = vuelo normal
        self.screen = screen
        self.SW, self.SH = screen.get_size()
        self.u = self.SH / 1000.0
        self.cfg = COHETES[max(0, min(idx_cohete, len(COHETES) - 1))]
        self.dest = DESTINOS.get(idx_orbita, DESTINOS[0])
        self.destino, self.mision, self.cohete, self.puntos = destino, mision, cohete, puntos
        self.t_fin = self.cfg["t_fin"]
        self.falla = list(falla) if falla else None
        self.fallida = bool(self.falla)
        self.perdida = perdida
        self.fallo_ocurrido = False
        self.flash_col = (255, 255, 255)
        self.eventos = [e for e in self.cfg["eventos"] if not self.fallida or e[0] < T_FALLA]
        if self.fallida:
            self.t_fin = T_FALLA + T_FALLA_CARD

        self.t = 0.0
        self._last = pygame.time.get_ticks()
        self.tl = 0.0
        self.alt = 0.0
        self.cam = 0.0
        self.s = 0.0                    # 0 = cielo de día, 1 = espacio
        self.G = self.SH * 0.80         # línea del suelo en pantalla
        self.A_stop = self.SH * 0.20    # cuánto sube el cohete antes de que la cámara lo siga
        self.thrust = 0.0
        self.corte_fin = 0.0
        self.flash = 0.0
        self.sep = False
        self.etapa = 1
        self.ev_idx = 0
        self.banner = None
        self.llegada = False
        self.terminado = False
        self.humo = []
        self.vuelan = []

        # fuentes
        self.f_big = pygame.font.SysFont(None, int(self.SH * 0.28))
        self.f_tit = pygame.font.SysFont(None, int(self.SH * 0.075))
        self.f_mid = pygame.font.SysFont(None, int(self.SH * 0.042))
        self.f_peq = pygame.font.SysFont(None, int(self.SH * 0.032))

        self._cargar_cohete(carpeta_img)

        # decorado fijo
        rng = random.Random(7)
        self.estrellas = [(rng.random() * self.SW, rng.random() * self.SH, rng.choice((1, 1, 2, 3)), 0.3 + rng.random() * 0.7)
                          for _ in range(160)]
        self.nubes = [(rng.random() * self.SW, (0.25 + rng.random() * 6.0) * self.SH, 0.7 + rng.random() * 1.2)
                      for _ in range(18)]
        self.lineas = [(rng.random() * self.SW, rng.random() * self.SH, (40 + rng.random() * 90) * self.u, 0.5 + rng.random() * 0.8)
                       for _ in range(46)]
        self.montes = [rng.random() * 0.12 * self.SH + 0.03 * self.SH for _ in range(9)]

        # planeta de destino
        R = int(self.dest["R"] * self.SH)
        self.R = R
        self.planeta = _esfera(R, self.dest["tipo"], 3)
        self.overlay = pygame.Surface((self.SW, self.SH), pygame.SRCALPHA)
        self.velo = pygame.Surface((self.SW, self.SH))

    # ------------------------------------------------------------------
    def _cargar_cohete(self, carpeta):
        cfg = self.cfg
        x0, y0, x1, y1 = cfg["crop"]
        try:
            img = pygame.image.load(os.path.join(carpeta, cfg["img"])).convert_alpha()
        except (pygame.error, FileNotFoundError):
            img = pygame.Surface((1000, 1000), pygame.SRCALPHA)
            pygame.draw.rect(img, (200, 200, 205), (x0 + 30, y0, x1 - x0 - 60, y1 - y0))
        for r in cfg["borrar"]:
            img.fill((0, 0, 0, 0), pygame.Rect(r))
        crop = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
        base = img.subsurface(crop).copy()
        sin_boosters = base.copy()
        fuentes = []
        for r in cfg["boosters"]:
            rr = pygame.Rect(r)
            fuentes.append((img.subsurface(rr).copy(), rr))
            sin_boosters.fill((0, 0, 0, 0), rr.move(-x0, -y0))

        self.esc = self.SH * 0.48 / 580.0          # misma escala para los 3 cohetes
        self.pb = max(2, int(10 * self.esc))       # tamaño de "pixel" de las llamas
        self.crop = crop
        self.corpo = self._escalar(base)
        self.corpo_sin = self._escalar(sin_boosters)
        self.boosters_src = [(self._escalar(s), rr) for s, rr in fuentes]
        self.cw, self.ch = self.corpo.get_size()
        self.rx = self.SW // 2 - self.cw // 2
        self.ry = self.G - self.ch

    def _escalar(self, surf):
        w, h = surf.get_size()
        return pygame.transform.scale(surf, (max(1, round(w * self.esc)), max(1, round(h * self.esc))))

    # ------------------------------------------------------------------
    #  CONTROL
    # ------------------------------------------------------------------
    def saltar(self):
        """Salta directo al final (cartel de misión cumplida)."""
        for i in range(self.ev_idx, len(self.eventos)):
            _, kind, _ = self.eventos[i]
            if kind == "boosters":
                self._separar(volar=False)
            if kind in ("etapa", "boosters"):
                self.etapa += 1
        self.ev_idx = len(self.eventos)
        self.llegada = True
        self.banner = None
        self.t = T_LIFT + self.t_fin
        self.vuelan.clear()

    def _evento(self, kind, texto):
        self.banner = (texto, self.t)
        if kind == "boosters":
            self._separar(volar=True)
            self.flash = 0.8
        if kind in ("etapa", "boosters"):
            self.etapa += 1
        if kind == "etapa":
            self.corte_fin = self.t + 0.6
            self.flash = 1.0

    def _separar(self, volar):
        self.sep = True
        if not volar:
            return
        x0, y0 = self.crop.x, self.crop.y
        for (im, rr), cfg_m in zip(self.boosters_src, [m for m in self.cfg["motores"] if m[3] is not None]):
            w, h = im.get_size()
            bx = self.rx + (rr.x - x0) * self.esc
            by = self.ry + (rr.y - y0) * self.esc
            lado = -1 if rr.centerx < self.crop.centerx else 1
            self.vuelan.append({
                "img": im, "x": bx + w / 2, "y": by + h / 2,
                "vx": lado * 110 * self.u, "vy": 40 * self.u,
                "ang": 0.0, "vang": -lado * 28.0, "fuego": 0.5,
                "mot": ((cfg_m[0] - rr.centerx) * self.esc, (cfg_m[1] - rr.centery) * self.esc, cfg_m[2] * self.esc),
            })

    # ------------------------------------------------------------------
    #  ACTUALIZAR
    # ------------------------------------------------------------------
    def update(self):
        now = pygame.time.get_ticks()
        dt = min(0.05, (now - self._last) / 1000.0)
        self._last = now
        self.t += dt
        u = self.u

        self.tl = max(0.0, self.t - T_LIFT)
        tl = self.tl
        self.alt = self._altura(tl)
        self.cam = max(0.0, self.alt - self.A_stop)
        self.s = _clamp(self.alt / (6500 * u)) ** 0.8
        self.terminado = tl >= self.t_fin

        # eventos de la secuencia
        evs = self.eventos
        while self.ev_idx < len(evs) and tl >= evs[self.ev_idx][0]:
            _, kind, texto = evs[self.ev_idx]
            self._evento(kind, texto)
            self.ev_idx += 1
        if self.fallida and not self.fallo_ocurrido and tl >= T_FALLA:
            self.fallo_ocurrido = True
            self.banner = ("¡FALLA CRÍTICA EN EL COHETE!", self.t)
            self.flash = 1.0
            self.flash_col = (255, 110, 60)
        if not self.fallida and not self.llegada and not self.terminado and tl >= self.t_fin - 3.0:
            self.llegada = True
            self.banner = ("ACERCÁNDOSE A " + self.destino.upper(), self.t)

        # empuje de los motores
        th = 0.0 if self.t < T_IGN else _clamp((self.t - T_IGN) / 1.2)
        if self.t < self.corte_fin:
            th *= 0.1
        if self.fallo_ocurrido:
            th = 0.0  # motores apagados
        self.thrust = th
        self.flash = max(0.0, self.flash - dt * 2.5)

        # posición del cohete en pantalla
        base_y = self.G - min(self.alt, self.A_stop)
        self.ry = base_y - self.ch
        self.rx = self.SW // 2 - self.cw // 2

        # humo
        if th > 0.05 and self.s < 0.7:
            gy = self.G + self.cam
            for sx, sy, ancho in self._motores():
                if self.alt < self.A_stop:
                    for lado in (-1, 1):
                        self.humo.append([sx, 6 * u, lado * random.uniform(120, 420) * u, 15 * u,
                                          1.8, 1.8, random.uniform(14, 26) * u, 1.6])
                for _ in range(2):
                    self.humo.append([sx + random.uniform(-0.4, 0.4) * ancho, gy - sy,
                                      random.uniform(-30, 30) * u, -random.uniform(0, 40) * u,
                                      1.2, 1.2, random.uniform(8, 14) * u, 2.0])
            if len(self.humo) > 900:
                del self.humo[:len(self.humo) - 900]
        if self.fallo_ocurrido and not self.terminado and tl - T_FALLA < T_FALLA_CARD - 0.5:
            gy = self.G + self.cam
            for sx, sy, ancho in self._motores():
                for _ in range(2):
                    self.humo.append([sx + random.uniform(-0.5, 0.5) * ancho, gy - sy,
                                      random.uniform(-40, 40) * u, -random.uniform(0, 60) * u,
                                      1.8, 1.8, random.uniform(10, 18) * u, 2.2, (55, 55, 60)])
            if len(self.humo) > 900:
                del self.humo[:len(self.humo) - 900]
        for p in self.humo:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.985
            p[4] -= dt
        self.humo = [p for p in self.humo if p[4] > 0]

        # boosters que caen
        for b in self.vuelan:
            b["vy"] += 700 * u * dt
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["ang"] += b["vang"] * dt
            b["fuego"] -= dt
        self.vuelan = [b for b in self.vuelan if b["y"] < self.SH + 300]

    def _altura(self, tl):
        """Altura según el tiempo de vuelo. Si el cohete falla, pierde empuje: sube un poco más y vuelve a bajar."""
        u = self.u
        base = (50 * tl ** 2 + 22 * tl ** 3) * u
        if not self.fallida or tl <= T_FALLA:
            return base
        d = tl - T_FALLA
        v0 = (100 * T_FALLA + 66 * T_FALLA ** 2) * u
        alt_f = (50 * T_FALLA ** 2 + 22 * T_FALLA ** 3) * u
        return max(0.0, alt_f + v0 * d - 0.5 * 600 * u * d * d)

    def _motores(self):
        """Posiciones en pantalla (x, y, ancho) de los motores encendidos."""
        res = []
        for mx, my, w, bi in self.cfg["motores"]:
            if bi is not None and self.sep:
                continue
            res.append((self.rx + (mx - self.crop.x) * self.esc + 0.0,
                        self.ry + (my - self.crop.y) * self.esc + 0.0,
                        w * self.esc))
        return res

    # ------------------------------------------------------------------
    #  DIBUJAR
    # ------------------------------------------------------------------
    def draw(self):
        scr = self.screen
        self._cielo(scr)
        self._estrellas(scr)
        gy = self.G + self.cam
        if gy < self.SH + 10:
            self._suelo(scr, gy)
        self._nubes(scr, gy)
        self._planeta(scr)
        self._lineas_velocidad(scr)
        self._humo(scr, gy)
        self._boosters_cayendo(scr)
        self._cohete(scr)
        if self.flash > 0:
            self.velo.fill(self.flash_col)
            self.velo.set_alpha(int(170 * self.flash))
            scr.blit(self.velo, (0, 0))
        if self.fallo_ocurrido:
            if self.terminado:
                self.velo.fill((20, 0, 0))
                self.velo.set_alpha(150)
            else:
                self.velo.fill((170, 0, 0))
                self.velo.set_alpha(int(45 + 30 * math.sin(self.t * 8)))
            scr.blit(self.velo, (0, 0))
        self._hud(scr)

    # --- fondo ---------------------------------------------------------
    def _cielo(self, scr):
        n = 40
        bh = self.SH // n + 1
        top = _lerp_col(CIELO_DIA[0], CIELO_ESPACIO[0], self.s)
        bot = _lerp_col(CIELO_DIA[1], CIELO_ESPACIO[1], self.s)
        for i in range(n):
            pygame.draw.rect(scr, _lerp_col(top, bot, i / (n - 1)), (0, i * bh, self.SW, bh))

    def _estrellas(self, scr):
        if self.s < 0.3:
            return
        b = int(255 * _clamp((self.s - 0.3) / 0.7))
        for x, y, tam, k in self.estrellas:
            yy = (y + self.alt * k * 0.015) % self.SH
            c = int(b * (0.5 + 0.5 * k))
            pygame.draw.rect(scr, (c, c, min(255, c + 15)), (int(x), int(yy), tam, tam))

    def _suelo(self, scr, gy):
        u, SW, SH = self.u, self.SW, self.SH
        gy = int(gy)
        # montañas lejanas
        pts = [(0, gy)]
        paso = SW / (len(self.montes) - 1)
        for i, h in enumerate(self.montes):
            pts.append((int(i * paso), int(gy - h)))
        pts.append((SW, gy))
        pygame.draw.polygon(scr, (70, 90, 125), pts)
        pygame.draw.rect(scr, (38, 70, 48), (0, gy, SW, SH - gy + 2))
        pygame.draw.rect(scr, (28, 52, 36), (0, gy, SW, max(2, int(6 * u))))
        # plataforma
        cx = SW // 2
        pw = int(self.cw * 1.9)
        pygame.draw.rect(scr, (135, 135, 142), (cx - pw // 2, gy, pw, int(14 * u)))
        pygame.draw.rect(scr, (95, 95, 105), (cx - pw // 2, gy + int(14 * u), pw, int(8 * u)))
        # torre de lanzamiento
        w, h = int(46 * u), int(SH * 0.58)
        x = int(cx - self.cw / 2 - 120 * u)
        col, p = (105, 110, 122), max(2, int(6 * u))
        pygame.draw.rect(scr, col, (x, gy - h, p, h))
        pygame.draw.rect(scr, col, (x + w - p, gy - h, p, h))
        paso_t = max(8, int(40 * u))
        for k in range(0, h, paso_t):
            yy = gy - k
            pygame.draw.rect(scr, col, (x, yy - p // 2, w, max(2, p // 2)))
            pygame.draw.line(scr, col, (x, yy), (x + w, yy - paso_t), max(1, p // 3))
        # brazo que se retira antes del despegue
        ret = _ease((self.t - 2.2) / 0.9)
        largo = int((120 * u + w) * (1 - ret))
        if largo > 2:
            pygame.draw.rect(scr, (150, 150, 160), (x + w, int(gy - h * 0.55), largo, max(3, int(9 * u))))

    def _nubes(self, scr, gy):
        if self.s > 0.8:
            return
        col = _lerp_col((245, 248, 255), (120, 140, 190), self.s)
        for x, wy, esc in self.nubes:
            y = gy - wy
            if -120 < y < self.SH + 120:
                r = int(60 * esc * self.u)
                for dx, dy, w in ((0, 0, 2.6), (-1.1, 0.25, 1.8), (1.2, 0.2, 1.9), (0.2, -0.35, 1.7)):
                    pygame.draw.ellipse(scr, col, (int(x + dx * r), int(y + dy * r), int(w * r), int(r * 0.9)))

    def _planeta(self, scr):
        if self.fallida:
            return  # si el cohete falla en pleno vuelo nunca llega a ningún destino: no se dibuja Luna, Marte ni Tierra
        pp = _clamp((self.tl - (self.t_fin - 3.0)) / 3.0)
        if pp <= 0:
            return
        e = _ease(pp)
        d = self.dest
        cx = (d["tgt"][0] + d["off"][0] * (1 - e)) * self.SW
        cy = (d["tgt"][1] + d["off"][1] * (1 - e)) * self.SH
        R = self.R
        if d["tipo"] == "tierra":
            pygame.draw.circle(scr, (30, 70, 150), (int(cx), int(cy)), R + int(10 * self.u))
            pygame.draw.circle(scr, (70, 140, 235), (int(cx), int(cy)), R + int(4 * self.u))
        scr.blit(self.planeta, (int(cx) - R, int(cy) - R))

    def _lineas_velocidad(self, scr):
        a = _clamp((self.tl - 0.8) / 3.0)
        if a <= 0:
            return
        c = int(120 + 100 * a)
        for x, y0, largo, k in self.lineas:
            yy = (y0 + self.alt * k * 0.9) % (self.SH + largo) - largo
            pygame.draw.rect(scr, (c, c, min(255, c + 20)), (int(x), int(yy), max(1, int(2 * self.u)), int(largo * a)))

    def _humo(self, scr, gy):
        if not self.humo:
            return
        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        for p in self.humo:
            x, wy, vx, vy, vida, vmax, tam, grow = p[:8]
            col = p[8] if len(p) > 8 else (228, 228, 234)
            sy = gy - wy
            if -60 < sy < self.SH + 60:
                f = vida / vmax
                r = int(tam * (1 + grow * (1 - f)))
                pygame.draw.circle(ov, (col[0], col[1], col[2], int(170 * f)), (int(x), int(sy)), max(1, r))
        scr.blit(ov, (0, 0))

    # --- cohete --------------------------------------------------------
    def _llama(self, scr, sx, sy, ancho, largo):
        pb = self.pb
        n = int(largo // pb)
        if n < 1:
            return
        for ratio, lf, col in CAPAS_LLAMA:
            m = max(1, int(n * lf))
            j = random.choice((-pb, 0, pb))
            for i in range(m):
                loc = i / m
                w = max(pb, int(round(ancho * ratio * (1 - 0.8 * loc) / pb)) * pb)
                pygame.draw.rect(scr, col, (int(sx - w / 2) + j, int(sy + i * pb), w, pb))

    def _cohete(self, scr):
        # sacudida mientras los motores rugen
        amp = 0.0
        if self.t >= T_IGN:
            amp = self.thrust * (2.0 if self.tl < 7 else 0.6) * self.u
        if self.fallo_ocurrido:
            amp = 2.5 * self.u  # vibra sin control
        jx = int(random.uniform(-amp, amp))
        jy = int(random.uniform(-amp, amp))

        # llamas
        if self.thrust > 0.02:
            vac = 1 + 0.5 * _clamp(self.tl / 3.0)
            for sx, sy, ancho in self._motores():
                largo = ancho * 2.6 * self.thrust * vac * random.uniform(0.85, 1.15)
                self._llama(scr, sx + jx, sy + jy, ancho, largo)

        # llamas de los boosters ya separados (un instante)
        for b in self.vuelan:
            if b["fuego"] > 0:
                mx, my, ancho = b["mot"]
                bw, bh = b["img"].get_size()
                self._llama(scr, b["x"] + mx, b["y"] + my, ancho, ancho * 2.2 * _clamp(b["fuego"] * 2))

        im = self.corpo_sin if self.sep else self.corpo
        if self.fallo_ocurrido:
            d = _clamp((self.tl - T_FALLA) / T_FALLA_CARD)
            rot = pygame.transform.rotate(im, -38 * _ease(d))
            cx = self.rx + jx + im.get_width() // 2
            cy = int(self.ry) + jy + im.get_height() // 2
            scr.blit(rot, rot.get_rect(center=(cx, cy)))
        else:
            scr.blit(im, (self.rx + jx, int(self.ry) + jy))

    def _boosters_cayendo(self, scr):
        for b in self.vuelan:
            rot = pygame.transform.rotate(b["img"], b["ang"])
            scr.blit(rot, rot.get_rect(center=(int(b["x"]), int(b["y"]))))

    # --- interfaz ------------------------------------------------------
    def _texto(self, scr, s, fuente, color, centro=None, topleft=None, alpha=255):
        img = fuente.render(s, True, color)
        sombra = fuente.render(s, True, (0, 0, 0))
        if alpha < 255:
            img.set_alpha(alpha)
            sombra.set_alpha(alpha)
        r = img.get_rect(center=centro) if centro else img.get_rect(topleft=topleft)
        o = max(2, int(self.u * 3))
        scr.blit(sombra, r.move(o, o))
        scr.blit(img, r)
        return r

    def _hud(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        t, tl = self.t, self.tl

        # cuenta regresiva grande
        if t < T_IGN:
            n = 3 - int(t)
            f = t - int(t)
            img = self.f_big.render(str(n), True, (255, 255, 255))
            borde = self.f_big.render(str(n), True, (0, 0, 0))
            esc = 1.25 - 0.25 * f
            img = pygame.transform.rotozoom(img, 0, esc)
            borde = pygame.transform.rotozoom(borde, 0, esc)
            img.set_alpha(int(255 * (1 - f ** 3)))
            borde.set_alpha(int(255 * (1 - f ** 3)))
            r = img.get_rect(center=(SW // 2, int(SH * 0.22)))
            scr.blit(borde, r.move(int(4 * u), int(4 * u)))
            scr.blit(img, r)
        elif t < T_LIFT:
            self._texto(scr, "¡IGNICIÓN!", self.f_tit, (255, 200, 60), centro=(SW // 2, int(SH * 0.12)))
        elif tl < 2.0:
            self._texto(scr, "¡DESPEGUE!", self.f_tit, (120, 255, 140), centro=(SW // 2, int(SH * 0.12)))

        # reloj y telemetría
        reloj = f"T-{max(0.0, T_LIFT - t):4.1f} s" if t < T_LIFT else f"T+{tl:5.1f} s"
        caja = pygame.Rect(int(14 * u), int(14 * u), int(330 * u), int(120 * u))
        pygame.draw.rect(scr, (0, 0, 0), caja, border_radius=6)
        pygame.draw.rect(scr, (0, 200, 255), caja, 2, border_radius=6)
        self._texto(scr, reloj, self.f_mid, (255, 255, 0), topleft=(caja.x + 12, caja.y + 8))
        if self.fallida:
            km = self.alt / self.u * 0.03
        else:
            km = self.dest["km"] * _clamp(tl / self.t_fin) ** 3
        self._texto(scr, f"Altitud: {_miles(km)} km", self.f_peq, (255, 255, 255), topleft=(caja.x + 12, caja.y + int(48 * u)))
        if self.fallo_ocurrido:
            self._texto(scr, "ESTADO: FALLA - MOTORES APAGADOS", self.f_peq, (255, 110, 100), topleft=(caja.x + 12, caja.y + int(82 * u)))
        else:
            self._texto(scr, f"Etapa: {self.etapa}   |   {self.cohete}", self.f_peq, (200, 220, 255), topleft=(caja.x + 12, caja.y + int(82 * u)))

        # avisos de eventos
        if self.banner and not self.terminado:
            texto, t0 = self.banner
            edad = t - t0
            if edad < 2.4:
                a = int(255 * _clamp(min(edad / 0.2, (2.4 - edad) / 0.5)))
                self._texto(scr, texto, self.f_tit, (255, 255, 255), centro=(SW // 2, int(SH * 0.12)), alpha=a)

        if not self.terminado:
            self._texto(scr, "ESPACIO: saltar", self.f_peq, (200, 200, 210), topleft=(int(16 * u), SH - int(40 * u)))
            return

        if self.fallida:
            self._cartel_falla(scr)
            return

        # cartel final
        caja = pygame.Rect(int(SW * 0.04), int(SH * 0.28), int(SW * 0.36), int(SH * 0.44))
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        pygame.draw.rect(fondo, (10, 18, 50, 215), fondo.get_rect(), border_radius=12)
        scr.blit(fondo, caja.topleft)
        pygame.draw.rect(scr, (0, 200, 255), caja, 3, border_radius=12)
        cx = caja.centerx
        self._texto(scr, "¡MISIÓN CUMPLIDA!", self.f_tit, (90, 230, 120), centro=(cx, caja.y + int(caja.h * 0.14)))
        self._texto(scr, self.mision, self.f_mid, (255, 255, 0), centro=(cx, caja.y + int(caja.h * 0.31)))
        self._texto(scr, f"Cohete: {self.cohete}", self.f_peq, (200, 220, 255), centro=(cx, caja.y + int(caja.h * 0.44)))
        self._texto(scr, f"Destino alcanzado: {self.destino}", self.f_peq, (200, 220, 255), centro=(cx, caja.y + int(caja.h * 0.55)))
        self._texto(scr, f"Puntuación: {self.puntos} puntos", self.f_mid, (255, 255, 255), centro=(cx, caja.y + int(caja.h * 0.70)))
        if int(t * 2) % 2 == 0:
            self._texto(scr, "ESPACIO o clic: volver a la estación", self.f_peq, (170, 200, 230), centro=(cx, caja.y + int(caja.h * 0.89)))

    # --- cartel de misión fallida -------------------------------------
    def _wrap(self, s, fuente, ancho):
        lineas, cur = [], ""
        for w in s.split():
            if fuente.size(cur + " " + w)[0] > ancho and cur:
                lineas.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lineas.append(cur)
        return lineas

    def _cartel_falla(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        caja = pygame.Rect(int(SW * 0.04), int(SH * 0.14), int(SW * 0.46), int(SH * 0.72))
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        pygame.draw.rect(fondo, (35, 8, 12, 230), fondo.get_rect(), border_radius=12)
        scr.blit(fondo, caja.topleft)
        pygame.draw.rect(scr, (255, 90, 80), caja, 3, border_radius=12)
        cx = caja.centerx
        y = caja.y + int(caja.h * 0.09)
        self._texto(scr, "MISIÓN FALLIDA", self.f_tit, (255, 90, 80), centro=(cx, y))
        y += int(caja.h * 0.10)
        self._texto(scr, self.mision, self.f_mid, (255, 255, 0), centro=(cx, y))
        y += int(caja.h * 0.09)
        self._texto(scr, "Despegaste con la revisión en rojo. Qué falló:", self.f_peq, (255, 200, 170), centro=(cx, y))
        y += int(caja.h * 0.08)
        ancho = caja.w - int(60 * u)
        lineas_max = 7
        usadas = 0
        for causa in self.falla[:4]:
            for k, l in enumerate(self._wrap(causa, self.f_peq, ancho)):
                if usadas >= lineas_max:
                    break
                self._texto(scr, ("- " if k == 0 else "  ") + l, self.f_peq, (255, 225, 210), topleft=(caja.x + int(30 * u), y))
                y += int(self.SH * 0.036)
                usadas += 1
        y = caja.y + int(caja.h * 0.80)
        if self.perdida > 0:
            self._texto(scr, f"Pérdidas por el accidente: -${self.perdida}M", self.f_mid, (255, 150, 120), centro=(cx, y))
        else:
            self._texto(scr, "No tenías fondos que perder, pero tus piezas siguen a salvo.", self.f_peq, (200, 220, 255), centro=(cx, y))
        if int(self.t * 2) % 2 == 0:
            self._texto(scr, "ESPACIO o clic: volver a la estación", self.f_peq, (170, 200, 230),
                        centro=(cx, caja.y + int(caja.h * 0.93)))

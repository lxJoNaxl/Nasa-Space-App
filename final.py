"""
Final cinematográfico del juego (se muestra al completar la ÚLTIMA misión).

Se usa desde main.py así:
    fin = FinalEpico(screen, carpeta_images, idx_cohete, nombre_cohete,
                     nombre_mision, [nombres de misiones], jugador)
    fin.tecla(event)      # por cada KEYDOWN
    fin.click()           # por cada clic izquierdo
    fin.update(); fin.draw()   # una vez por frame
    fin.terminado         # True cuando el jugador cierra los créditos
    fin.jugador           # nombre del jugador (se pide en la escena si estaba vacío)

Secuencia:
  1. Fundido a negro desde la escena de Marte.
  2. (Solo la primera vez) Pantalla para escribir el nombre del ingeniero.
  3. Viaje de regreso: el cohete cruza el espacio, las estrellas pasan a toda velocidad.
  4. Llegada: aparece la Tierra y el cohete entra en la atmósfera con una estela de fuego.
  5. Informe de misión en forma de periódico.
  6. Créditos.
"""
import datetime
import math
import os
import random

import pygame

from despegue import COHETES, CAPAS_LLAMA, _esfera, _clamp, _lerp, _ease

# ----------------------------------------------------------------------
#  TEXTOS (cámbialos a tu gusto)
# ----------------------------------------------------------------------
TITULO_JUEGO = "SIMULADOR ESPACIAL"
SUBTITULO_JUEGO = "Construye tu Cohete"
CREADOR = "Tec totodile's"
NOMBRE_PERIODICO = "LA GACETA ESPACIAL"
TITULAR = "¡ÉXITO ROTUNDO!"
SUBTITULAR = "La sonda espacial envía las primeras imágenes de Marte"
PIE_FOTO = "Primera imagen de la superficie marciana enviada por la sonda."
NOTICIA = ("Tras un viaje de más de 225 millones de kilómetros, la nave llegó a Marte, desplegó su dron "
           "de exploración y analizó el suelo del planeta rojo. Las primeras imágenes ya viajan hacia la "
           "Tierra y el centro de control celebra el éxito de toda la misión.")
MENSAJE_NASA = [
    "Cada misión empieza con una idea y con personas que se atreven a resolver lo que nadie ha resuelto.",
    "Las naves que llegan a la Luna y a Marte nacen de miles de cálculos, pruebas y errores corregidos a tiempo.",
    "La ingeniería espacial nos ha dado satélites que cuidan el clima, comunicaciones que conectan al mundo "
    "y descubrimientos que cambian cómo vemos el universo.",
    "Gracias por demostrar que con curiosidad, trabajo en equipo y perseverancia se llega muy lejos. "
    "El próximo gran paso lo darás tú.",
]

# ----------------------------------------------------------------------
#  TIEMPOS (segundos)
# ----------------------------------------------------------------------
T_FADE = 1.6
T_VIAJE = 7.0
T_LLEGADA = 7.5
T_PAPEL = 1.3          # lo que tarda el periódico en girar hasta quedar quieto
KM_MARTE = 225_000_000
MAX_NOMBRE = 20
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
SERIF = "georgia,timesnewroman,times,dejavuserif,serif"


def _miles(n):
    return f"{int(n):,}".replace(",", ".")


class FinalEpico:
    def __init__(self, screen, carpeta_img, idx_cohete, cohete, mision, misiones, jugador=""):
        self.screen = screen
        self.SW, self.SH = screen.get_size()
        self.u = self.SH / 1000.0
        self.cohete_nombre, self.mision = cohete, mision
        self.misiones = list(misiones)
        self.jugador = (jugador or "").strip()[:MAX_NOMBRE]
        self.nombre_txt = ""
        self.terminado = False

        self.fase = "fade"
        self.tf = 0.0
        self._last = pygame.time.get_ticks()
        self.scroll = 0.0
        self.vel = 0.0
        self.particulas = []

        self.prev = screen.copy()                       # último cuadro de la escena anterior
        self.negro = pygame.Surface((self.SW, self.SH))
        self.negro.fill((0, 0, 0))
        self.blanco = pygame.Surface((self.SW, self.SH))
        self.blanco.fill((255, 255, 255))
        self.overlay = pygame.Surface((self.SW, self.SH), pygame.SRCALPHA)

        u = self.u
        self.f_big = pygame.font.SysFont(None, int(self.SH * 0.085))
        self.f_tit = pygame.font.SysFont(None, int(self.SH * 0.065))
        self.f_mid = pygame.font.SysFont(None, int(self.SH * 0.042))
        self.f_peq = pygame.font.SysFont(None, int(self.SH * 0.032))

        rng = random.Random(11)
        self.estrellas = [(rng.random() * self.SW, rng.random() * self.SH, 0.3 + rng.random() * 0.9,
                           rng.choice((1, 1, 2, 3))) for _ in range(170)]

        self._cargar_cohete(carpeta_img, idx_cohete)
        self.marte = _esfera(int(0.28 * self.SH), "marte", 5)
        self.tierra = _esfera(int(0.75 * self.SH), "tierra", 3)
        self.periodico = None
        self.creditos = None
        self.cred_off_min = 0.0
        self.cred_speed = 85 * u
        self.scroll_fin = False

    # ------------------------------------------------------------------
    def _cargar_cohete(self, carpeta, idx):
        cfg = COHETES[max(0, min(idx, len(COHETES) - 1))]
        x0, y0, x1, y1 = cfg["crop"]
        try:
            img = pygame.image.load(os.path.join(carpeta, cfg["img"])).convert_alpha()
        except (pygame.error, FileNotFoundError, OSError):
            img = pygame.Surface((1000, 1000), pygame.SRCALPHA)
            pygame.draw.rect(img, (200, 200, 205), (x0 + 30, y0, x1 - x0 - 60, y1 - y0))
        for r in cfg["borrar"]:
            img.fill((0, 0, 0, 0), pygame.Rect(r))
        base = img.subsurface(pygame.Rect(x0, y0, x1 - x0, y1 - y0)).copy()
        caja = base.get_bounding_rect()
        if caja.width > 0 and caja.height > 0:
            base = base.subsurface(caja).copy()
        self.L = int(self.SH * 0.30)                     # largo del cohete en pantalla
        f = self.L / base.get_height()
        base = pygame.transform.smoothscale(base, (max(1, round(base.get_width() * f)), self.L))
        self.cohete_h = pygame.transform.rotate(base, -90)   # nariz hacia la derecha
        self.grosor = self.cohete_h.get_height()

    # ------------------------------------------------------------------
    #  CONTROL
    # ------------------------------------------------------------------
    def _ir(self, fase):
        self.fase = fase
        self.tf = 0.0
        self.particulas.clear()
        if fase == "informe":
            self._armar_periodico()
        elif fase == "creditos":
            self._armar_creditos()

    def tecla(self, event):
        k = event.key
        if self.fase == "nombre":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.nombre_txt.strip():
                    self.jugador = self.nombre_txt.strip()
                    self._ir("viaje")
            elif k == pygame.K_BACKSPACE:
                self.nombre_txt = self.nombre_txt[:-1]
            elif k != pygame.K_ESCAPE and event.unicode and event.unicode.isprintable() \
                    and len(self.nombre_txt) < MAX_NOMBRE:
                self.nombre_txt += event.unicode
            return
        if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            self._avanzar()

    def click(self):
        if self.fase != "nombre":
            self._avanzar()

    def _avanzar(self):
        f = self.fase
        if f == "fade":
            self._ir("viaje" if self.jugador else "nombre")
        elif f in ("viaje", "llegada"):
            self._ir("informe")
        elif f == "informe":
            if self.tf >= T_PAPEL + 0.2:
                self._ir("creditos")
        elif f == "creditos":
            if self.scroll_fin:
                self.terminado = True
            else:
                self.tf = (self.SH - self.cred_off_min) / self.cred_speed   # salta al final

    # ------------------------------------------------------------------
    #  ACTUALIZAR
    # ------------------------------------------------------------------
    def update(self):
        now = pygame.time.get_ticks()
        dt = min(0.05, (now - self._last) / 1000.0)
        self._last = now
        self.tf += dt
        u = self.u

        if self.fase == "fade" and self.tf >= T_FADE:
            self._ir("viaje" if self.jugador else "nombre")
        elif self.fase == "viaje" and self.tf >= T_VIAJE:
            self._ir("llegada")
        elif self.fase == "llegada" and self.tf >= T_LLEGADA:
            self._ir("informe")

        # velocidad de las estrellas
        if self.fase == "viaje":
            self.vel = _lerp(250, 2000, _ease(self.tf / 3.0)) * u
        elif self.fase == "llegada":
            self.vel = _lerp(2000, 500, _ease(self.tf / T_LLEGADA)) * u
        else:
            self.vel = 60 * u
        self.scroll += self.vel * dt

        if self.fase == "llegada":
            p = self.tf / T_LLEGADA
            inten = _clamp((p - 0.42) / 0.5)
            if inten > 0:
                x, y, ang, esc = self._pos_llegada(p)
                a = math.radians(ang)
                dx, dy = math.cos(a), math.sin(a)
                tx, ty = x - dx * self.L * 0.5 * esc, y - dy * self.L * 0.5 * esc
                for _ in range(int(3 + 6 * inten)):
                    v = random.uniform(120, 420) * u
                    vida = random.uniform(0.5, 1.1)
                    col = random.choice(((255, 120, 30), (255, 190, 60), (255, 245, 200), (255, 90, 20), (95, 95, 105)))
                    self.particulas.append([tx + random.uniform(-1, 1) * self.grosor * 0.3 * esc,
                                            ty + random.uniform(-1, 1) * self.grosor * 0.3 * esc,
                                            -dx * v + random.uniform(-60, 60) * u,
                                            -dy * v + random.uniform(-60, 60) * u,
                                            vida, vida, random.uniform(8, 20) * u * (0.4 + esc), col])
            if len(self.particulas) > 900:
                del self.particulas[:len(self.particulas) - 900]
        for q in self.particulas:
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[4] -= dt
        self.particulas = [q for q in self.particulas if q[4] > 0]

        if self.fase == "creditos":
            self.scroll_fin = self._cred_off() <= self.cred_off_min

    # ------------------------------------------------------------------
    #  DIBUJAR
    # ------------------------------------------------------------------
    def draw(self):
        scr = self.screen
        f = self.fase
        if f == "fade":
            scr.blit(self.prev, (0, 0))
            self.negro.set_alpha(int(255 * _ease(self.tf / T_FADE)))
            scr.blit(self.negro, (0, 0))
            return
        scr.fill((3, 3, 12))
        if f == "nombre":
            self._estrellas(scr)
            self._draw_nombre(scr)
        elif f == "viaje":
            self._draw_viaje(scr)
        elif f == "llegada":
            self._draw_llegada(scr)
        elif f == "informe":
            self._estrellas(scr)
            self._draw_informe(scr)
        elif f == "creditos":
            self._estrellas(scr)
            self._draw_creditos(scr)

    # --- utilidades ----------------------------------------------------
    def _t(self, scr, s, fuente, color, center=None, topleft=None, alpha=255):
        img = fuente.render(s, True, color)
        sombra = fuente.render(s, True, (0, 0, 0))
        if alpha < 255:
            img.set_alpha(alpha)
            sombra.set_alpha(alpha)
        r = img.get_rect(center=center) if center else img.get_rect(topleft=topleft)
        o = max(2, int(self.u * 3))
        scr.blit(sombra, r.move(o, o))
        scr.blit(img, r)
        return r

    def _wrap(self, s, fuente, ancho):
        lineas, cur = [], ""
        for w in s.split():
            if fuente.size((cur + " " + w).strip())[0] > ancho and cur:
                lineas.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lineas.append(cur)
        return lineas

    def _estrellas(self, scr):
        for x, y, k, tam in self.estrellas:
            largo = max(tam, int(self.vel * k * 0.045)) if self.vel > 300 * self.u else tam
            xx = (x - self.scroll * k) % (self.SW + largo) - largo
            c = int(120 + 135 * min(1.0, k))
            pygame.draw.rect(scr, (c, c, min(255, c + 20)), (int(xx), int(y), largo, tam))

    def _llama(self, scr, tx, ty, ang, largo, ancho):
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        for ratio, lf, col in CAPAS_LLAMA:
            largo_c = largo * lf * random.uniform(0.85, 1.12)
            w = ancho * ratio
            pts = [(tx + px * w / 2, ty + py * w / 2),
                   (tx - dx * largo_c, ty - dy * largo_c),
                   (tx - px * w / 2, ty - py * w / 2)]
            pygame.draw.polygon(scr, col, pts)

    def _cohete(self, scr, x, y, ang, esc, llama):
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        mitad = self.L / 2 * esc
        if llama > 0:
            self._llama(scr, x - dx * mitad * 0.97, y - dy * mitad * 0.97, ang, llama * esc, self.grosor * 0.5 * esc)
        img = pygame.transform.rotozoom(self.cohete_h, -ang, esc)
        scr.blit(img, img.get_rect(center=(int(x), int(y))))

    # --- escena: nombre --------------------------------------------------
    def _draw_nombre(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        caja = pygame.Rect(0, 0, int(SW * 0.5), int(SH * 0.42))
        caja.center = (SW // 2, SH // 2)
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        pygame.draw.rect(fondo, (10, 18, 50, 225), fondo.get_rect(), border_radius=12)
        scr.blit(fondo, caja.topleft)
        pygame.draw.rect(scr, (0, 200, 255), caja, 3, border_radius=12)
        cx = caja.centerx
        self._t(scr, "NOMBRE DEL INGENIERO", self.f_tit, (255, 255, 0), center=(cx, caja.y + int(caja.h * 0.17)))
        self._t(scr, "Escribe tu nombre para el informe de la misión:", self.f_peq, (200, 220, 255),
                center=(cx, caja.y + int(caja.h * 0.38)))
        campo = pygame.Rect(0, 0, int(caja.w * 0.8), int(SH * 0.07))
        campo.center = (cx, caja.y + int(caja.h * 0.58))
        pygame.draw.rect(scr, (0, 0, 0), campo, border_radius=8)
        pygame.draw.rect(scr, (90, 230, 120), campo, 2, border_radius=8)
        cursor = "|" if int(self.tf * 2) % 2 == 0 else ""
        self._t(scr, self.nombre_txt + cursor, self.f_mid, (255, 255, 255), center=campo.center)
        if self.nombre_txt.strip():
            self._t(scr, "ENTER: continuar", self.f_peq, (170, 200, 230), center=(cx, caja.y + int(caja.h * 0.83)))

    # --- escena: viaje de regreso ------------------------------------------
    def _distancia(self, g):
        return KM_MARTE * (1 - _clamp(g)) ** 2

    def _draw_viaje(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        p = _clamp(self.tf / T_VIAJE)
        e = _ease(p)
        self._estrellas(scr)

        # Marte se queda atrás
        esc = _lerp(1.0, 0.08, e ** 0.7)
        d = max(4, int(self.marte.get_width() * esc))
        img = pygame.transform.smoothscale(self.marte, (d, d))
        cx = _lerp(0.18 * SW, 0.02 * SW, e)
        scr.blit(img, img.get_rect(center=(int(cx), int(SH * 0.5))))

        # cohete (con vibración)
        sh = 2.5 * u
        x = 0.56 * SW + math.sin(self.tf * 1.7) * 14 * u + random.uniform(-sh, sh)
        y = 0.5 * SH + math.sin(self.tf * 2.3) * 9 * u + random.uniform(-sh, sh)
        self._cohete(scr, x, y, 0.0, 1.0, self.L * 0.55)

        self._t(scr, "RUMBO A LA TIERRA", self.f_big, (0, 255, 255), center=(SW // 2, int(SH * 0.11)))
        self._t(scr, f"{self.mision}: misión completada", self.f_mid, (255, 255, 0), center=(SW // 2, int(SH * 0.19)))
        g = self.tf / (T_VIAJE + T_LLEGADA)
        self._t(scr, f"Distancia a la Tierra: {_miles(self._distancia(g))} km", self.f_mid, (255, 255, 255),
                center=(SW // 2, int(SH * 0.88)))
        self._t(scr, "ESPACIO: saltar", self.f_peq, (200, 200, 210), topleft=(int(16 * u), SH - int(40 * u)))
        if self.tf < 0.6:
            self.negro.set_alpha(int(255 * (1 - self.tf / 0.6)))
            scr.blit(self.negro, (0, 0))

    # --- escena: llegada a la Tierra --------------------------------------
    def _pos_llegada(self, p):
        e = _ease(p)
        x = _lerp(0.30, 0.60, e) * self.SW
        y = _lerp(0.34, 0.50, e) * self.SH
        ang = _lerp(0.0, 62.0, _ease((p - 0.15) / 0.7))
        esc = _lerp(1.0, 0.45, e)
        return x, y, ang, esc

    def _draw_llegada(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        p = _clamp(self.tf / T_LLEGADA)
        e = _ease(p)
        self._estrellas(scr)

        # la Tierra crece
        R = int(_lerp(0.07, 0.75, e ** 1.4) * SH)
        R = max(8, R)
        cx = int(_lerp(0.80, 0.52, e) * SW)
        cy = int(_lerp(0.28, 1.12, e) * SH)
        pygame.draw.circle(scr, (30, 70, 150), (cx, cy), R + int(12 * u))
        pygame.draw.circle(scr, (70, 140, 235), (cx, cy), R + int(5 * u))
        scr.blit(pygame.transform.scale(self.tierra, (2 * R, 2 * R)), (cx - R, cy - R))

        # cohete + estela de fuego
        x, y, ang, esc = self._pos_llegada(p)
        inten = _clamp((p - 0.42) / 0.5)
        amp = (2 + 7 * inten) * u
        x += random.uniform(-amp, amp)
        y += random.uniform(-amp, amp)

        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        for px, py, vx, vy, vida, vmax, tam, col in self.particulas:
            f = vida / vmax
            pygame.draw.circle(ov, (col[0], col[1], col[2], int(200 * f)), (int(px), int(py)), max(1, int(tam * (0.5 + f))))
        if inten > 0:
            a = math.radians(ang)
            nx, ny = x + math.cos(a) * self.L * 0.5 * esc, y + math.sin(a) * self.L * 0.5 * esc
            for k, (rad, al) in enumerate(((1.1, 40), (0.8, 70), (0.5, 110))):
                pygame.draw.circle(ov, (255, 140 + 30 * k, 40 + 20 * k, int(al * inten)), (int(nx), int(ny)),
                                   int(self.L * 0.35 * esc * rad * (0.6 + inten)))
        scr.blit(ov, (0, 0))
        self._cohete(scr, x, y, ang, esc, self.L * (0.35 + 0.35 * inten))

        titulo = "LLEGANDO A CASA" if p < 0.4 else "ENTRADA EN LA ATMÓSFERA"
        self._t(scr, titulo, self.f_big, (255, 200, 60) if p >= 0.4 else (0, 255, 255), center=(SW // 2, int(SH * 0.11)))
        if p >= 0.4:
            self._t(scr, "Temperatura exterior: " + _miles(1500 + 1200 * inten) + " °C", self.f_mid, (255, 160, 100),
                    center=(SW // 2, int(SH * 0.19)))
        g = (T_VIAJE + self.tf) / (T_VIAJE + T_LLEGADA)
        self._t(scr, f"Distancia a la Tierra: {_miles(self._distancia(g))} km", self.f_mid, (255, 255, 255),
                center=(SW // 2, int(SH * 0.88)))
        self._t(scr, "ESPACIO: saltar", self.f_peq, (200, 200, 210), topleft=(int(16 * u), SH - int(40 * u)))

        if p > 0.88:
            self.blanco.set_alpha(int(255 * _clamp((p - 0.88) / 0.12)))
            scr.blit(self.blanco, (0, 0))

    # --- escena: periódico --------------------------------------------------
    def _serif(self, frac, bold=False, italic=False):
        return pygame.font.SysFont(SERIF, max(8, int(self.SH * frac)), bold=bold, italic=italic)

    def _armar_periodico(self):
        SW, SH, u = self.SW, self.SH, self.u
        ph = int(SH * 0.88)
        pw = min(int(ph * 1.30), int(SW * 0.92))
        p = pygame.Surface((pw, ph))
        p.fill((236, 228, 206))
        tinta, gris = (30, 28, 26), (150, 145, 135)
        borde = max(2, int(4 * u))
        pygame.draw.rect(p, tinta, p.get_rect(), borde)
        pygame.draw.rect(p, tinta, p.get_rect().inflate(-int(16 * u), -int(16 * u)), max(1, int(2 * u)))
        m = int(34 * u)
        ancho = pw - 2 * m

        def centrar(s, fuente, y, color=tinta):
            img = fuente.render(s, True, color)
            p.blit(img, img.get_rect(midtop=(pw // 2, y)))
            return y + img.get_height()

        y = m
        y = centrar(NOMBRE_PERIODICO, self._serif(0.078, bold=True), y) + int(4 * u)
        hoy = datetime.date.today()
        fecha = f"{hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}"
        pygame.draw.line(p, tinta, (m, y), (pw - m, y), max(2, int(3 * u)))
        y += int(6 * u)
        y = centrar(f"EDICIÓN ESPECIAL  ·  {fecha}  ·  CENTRO DE CONTROL DE MISIÓN", self._serif(0.021), y)
        y += int(6 * u)
        pygame.draw.line(p, tinta, (m, y), (pw - m, y), max(1, int(2 * u)))
        y += int(14 * u)

        y = centrar(TITULAR, self._serif(0.095, bold=True), y)
        f_sub = self._serif(0.036, bold=True)
        for l in self._wrap(SUBTITULAR, f_sub, ancho)[:2]:
            y = centrar(l, f_sub, y)
        y += int(8 * u)
        pygame.draw.line(p, tinta, (m, y), (pw - m, y), max(1, int(2 * u)))
        y += int(14 * u)

        # columna izquierda: foto de Marte
        col_w = int(ancho * 0.42)
        foto = pygame.Rect(m, y, col_w, int(ph * 0.33))
        pygame.draw.rect(p, (8, 8, 18), foto)
        rng = random.Random(4)
        for _ in range(40):
            pygame.draw.rect(p, (200, 200, 220), (foto.x + rng.randint(0, foto.w - 3), foto.y + rng.randint(0, foto.h - 3), 2, 2))
        d = int(min(foto.w, foto.h) * 0.86)
        marte = pygame.transform.smoothscale(self.marte, (d, d))
        p.blit(marte, marte.get_rect(center=foto.center))
        pygame.draw.rect(p, tinta, foto, max(2, int(3 * u)))
        f_pie = self._serif(0.020, italic=True)
        yy = foto.bottom + int(6 * u)
        for l in self._wrap(PIE_FOTO, f_pie, col_w)[:3]:
            p.blit(f_pie.render(l, True, tinta), (m, yy))
            yy += f_pie.get_height()
        # relleno gris bajo la foto (simula texto)
        limite = ph - m - int(50 * u)
        yy += int(10 * u)
        while yy < limite:
            w = int(col_w * rng.uniform(0.7, 1.0))
            pygame.draw.rect(p, gris, (m, yy, w, max(2, int(5 * u))))
            yy += int(14 * u)

        # columna derecha: firma, datos y noticia
        x2 = m + col_w + int(24 * u)
        w2 = pw - m - x2
        pygame.draw.line(p, tinta, (x2 - int(12 * u), y), (x2 - int(12 * u), limite), max(1, int(2 * u)))
        f_firma = self._serif(0.034, bold=True)
        p.blit(f_firma.render("Diseñado por: " + self.jugador, True, (120, 20, 20)), (x2, y))
        y2 = y + f_firma.get_height() + int(6 * u)
        f_dato = self._serif(0.024)
        for linea in (f"Misión: {self.mision}", f"Cohete: {self.cohete_nombre}"):
            for l in self._wrap(linea, f_dato, w2)[:2]:
                p.blit(f_dato.render(l, True, tinta), (x2, y2))
                y2 += f_dato.get_height()
        y2 += int(10 * u)
        pygame.draw.line(p, gris, (x2, y2), (pw - m, y2), max(1, int(2 * u)))
        y2 += int(10 * u)
        f_txt = self._serif(0.025)
        for l in self._wrap(NOTICIA, f_txt, w2):
            if y2 > limite:
                break
            p.blit(f_txt.render(l, True, tinta), (x2, y2))
            y2 += f_txt.get_height()
        y2 += int(8 * u)
        while y2 < limite:
            w = int(w2 * rng.uniform(0.75, 1.0))
            pygame.draw.rect(p, gris, (x2, y2, w, max(2, int(5 * u))))
            y2 += int(14 * u)

        # pie con la firma
        pygame.draw.line(p, tinta, (m, ph - m - int(34 * u)), (pw - m, ph - m - int(34 * u)), max(1, int(2 * u)))
        f_firma2 = self._serif(0.024, italic=True)
        s = f": {self.jugador}, ingeniero de la misión"
        p.blit(f_firma2.render(s, True, tinta), f_firma2.render(s, True, tinta).get_rect(midbottom=(pw // 2, ph - m - int(4 * u))))
        self.periodico = p

    def _draw_informe(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        p = self.periodico
        e = _ease(self.tf / T_PAPEL)
        if e < 1.0:
            img = pygame.transform.rotozoom(p, _lerp(540, 0, e), _lerp(0.08, 1.0, e))
        else:
            img = p
        r = img.get_rect(center=(SW // 2, SH // 2))
        sombra = pygame.Surface(r.size, pygame.SRCALPHA)
        sombra.fill((0, 0, 0, 110))
        scr.blit(sombra, r.move(int(10 * u), int(12 * u)))
        scr.blit(img, r)
        if self.tf > T_PAPEL + 0.2 and int(self.tf * 2) % 2 == 0:
            self._t(scr, "ESPACIO o clic: continuar", self.f_peq, (200, 220, 255), center=(SW // 2, SH - int(18 * u)))
        if self.tf < 0.9:
            self.blanco.set_alpha(int(255 * (1 - self.tf / 0.9)))
            scr.blit(self.blanco, (0, 0))

    # --- escena: créditos ---------------------------------------------------
    def _armar_creditos(self):
        SW, SH, u = self.SW, self.SH, self.u
        ancho = int(SW * 0.58)
        lineas = [
            (TITULO_JUEGO, "titulo"), (SUBTITULO_JUEGO, "sub"), ("", "esp"),
            ("MISIONES COMPLETADAS", "seccion"),
        ] + [(n, "normal") for n in self.misiones] + [
            ("", "esp"),
            ("CREADO POR", "seccion"), (CREADOR, "normal"), ("", "esp"),
            ("JUGADO POR", "seccion"), (self.jugador, "normal"), ("", "esp"),
            ("COHETE DE LA MISIÓN", "seccion"), (self.cohete_nombre, "normal"), ("", "esp"),
            ("INSPIRADO EN MISIONES REALES", "seccion"), ("CAPSTONE y MarCO, de la NASA", "normal"), ("", "esp"),
            ("MENSAJE DE LA NASA", "seccion"),
        ] + [(par, "parrafo") for par in MENSAJE_NASA] + [
            ("", "esp"), ("", "esp"),
            ("GRACIAS POR JUGAR", "titulo"),
        ]
        estilos = {
            "titulo": (self.f_big, (255, 255, 255)), "sub": (self.f_mid, (0, 255, 255)),
            "seccion": (self.f_mid, (255, 255, 0)), "normal": (self.f_tit, (255, 255, 255)),
            "parrafo": (self.f_peq, (200, 220, 255)),
        }
        items, y = [], 0
        for s, est in lineas:
            if est == "esp":
                y += int(SH * 0.05)
                continue
            fuente, color = estilos[est]
            textos = self._wrap(s, fuente, ancho) if est == "parrafo" else [s]
            for t in textos:
                img = fuente.render(t, True, color)
                items.append((img, y))
                y += img.get_height() + int(SH * (0.012 if est == "parrafo" else 0.016))
            if est == "parrafo":
                y += int(SH * 0.02)
        self.creditos = items
        ult_img, ult_y = items[-1]
        self.cred_off_min = SH * 0.5 - (ult_y + ult_img.get_height() / 2)

    def _cred_off(self):
        return max(self.cred_off_min, self.SH - self.tf * self.cred_speed)

    def _draw_creditos(self, scr):
        SW, SH, u = self.SW, self.SH, self.u
        off = self._cred_off()
        borde = SH * 0.14
        for img, y in self.creditos:
            yy = off + y
            if yy < -img.get_height() or yy > SH:
                continue
            centro = yy + img.get_height() / 2
            a = _clamp(min(centro, SH - centro) / borde)
            img.set_alpha(int(255 * a))
            scr.blit(img, img.get_rect(midtop=(SW // 2, int(yy))))
        if self.scroll_fin:
            if int(self.tf * 2) % 2 == 0:
                self._t(scr, "ESPACIO o clic: volver a la estación", self.f_peq, (170, 200, 230),
                        center=(SW // 2, SH - int(28 * u)))
        else:
            self._t(scr, "ESPACIO: saltar", self.f_peq, (200, 200, 210), topleft=(int(16 * u), SH - int(40 * u)))

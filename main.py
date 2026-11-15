import json
import os
import pygame
from Fondo.FondoMenu import FondoMenu 
import player as player_mod
from sprite import sprites
from player import Player
from input import keys_down
from map import ImageMap

# ======================================================================
#  INICIALIZACIÓN
# ======================================================================
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_W, SCREEN_H = screen.get_size()
pygame.display.set_caption("Simulador Espacial - Construcción de Cohetes")
clock = pygame.time.Clock()

UI_W, UI_H = 800, 600
OFF_X, OFF_Y = (SCREEN_W - UI_W) // 2, (SCREEN_H - UI_H) // 2
ui = pygame.Surface((UI_W, UI_H), pygame.SRCALPHA)

font_s = pygame.font.SysFont(None, 19)
font = pygame.font.SysFont(None, 24)
font_title = pygame.font.SysFont(None, 38)
font_big = pygame.font.SysFont(None, 64)

BG = (15, 15, 30)
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.json")
menu_bg = FondoMenu("planeta rotando.mp4", (SCREEN_W, SCREEN_H), BG)

# Estados
MENU, OPCIONES, ESTACION, PANEL_MISION, PANEL_NAVE, PANEL_INFORME = range(6)
estado = MENU

# ======================================================================
#  DATOS DEL JUEGO (Nombres simplificados - Cohetes)
# ======================================================================
def P(nombre, info, **kw):
    return {"nombre": nombre, "info": info, **kw}

BASE_POT = 1.5

# --- TAMAÑOS DE COHETE ---
FORMATOS_CUBESAT = [
    P("Cohete Pequeño (1U)", "Caja de 10x10x11 cm. Peso máximo: 1.33 kg. Ideal para pruebas básicas.",
      vol=1.0, masa_chasis=0.35, cap_max=1.33, costo=15),
    P("Cohete Mediano (3U)", "Caja alargada de 10x10x34 cm. Peso máximo: 4 kg. Buen espacio para baterías y cámaras.",
      vol=3.0, masa_chasis=0.95, cap_max=4.00, costo=35),
    P("Cohete Grande (6U)", "Caja de 10x20x34 cm. Peso máximo: 12 kg. Perfecto para misiones largas y equipo pesado.",
      vol=6.0, masa_chasis=1.80, cap_max=12.00, costo=70),
]

# --- SISTEMAS DE SEGURIDAD ---
MECANISMOS = [
    P("Sin seguridad", "Peligroso: no tiene interruptor de seguridad ni cables de emergencia. No será aprobado para volar.",
      rbf=False, burn=False, masa=0.0, costo=0),
    P("Seguridad completa", "Incluye interruptor de seguridad (RBF) y cables de emergencia para las antenas. Aprobado para volar.",
      rbf=True, burn=True, masa=0.15, costo=20),
]

# --- DESTINOS (ÓRBITAS) ---
ORBITAS = [
    P("Órbita Baja (400 km)", "Cerca de la Tierra. Fácil de alcanzar desde la Estación Espacial.",
      factor=1.0, solar=1.0, enl=1.0, dv_req=0, rad=10),
    P("Órbita Polar (800 km)", "Pasa por los polos. Da cobertura global todos los días.",
      factor=0.85, solar=1.0, enl=0.9, dv_req=250, rad=15),
    P("Órbita Geoestacionaria", "Muy lejos (35,786 km). Se queda fijo sobre un punto de la Tierra.",
      factor=0.28, solar=1.0, enl=0.7, dv_req=1800, rad=25),
    P("Órbita Lunar", "Alrededor de la Luna. Requiere mucha energía y motores potentes.",
      factor=0.22, solar=1.0, enl=0.45, dv_req=2200, rad=30),
    P("Órbita de Marte", "Viaje interplanetario. Solo posible con el cohete más potente.",
      factor=0.12, solar=0.43, enl=0.12, dv_req=3200, rad=45),
]

# --- COHETES LANZADORES ---
LANZADORES = [
    P("Cohete Pequeño", "Solo llega a órbita baja. Capacidad máxima: 15 kg.", cap=15.0, costo=50),
    P("Cohete Mediano", "Llega a órbitas altas y lunares. Capacidad máxima: 30 kg.", cap=30.0, costo=140),
    P("Cohete Pesado", "Llega hasta Marte. Capacidad máxima: 50 kg.", cap=50.0, costo=330),
]

# --- MOTORES ---
MOTORES = [
    P("Sin motor", "El cohete no puede moverse por sí solo. Depende del lanzador.",
      dv=0, masa=0.0, pot=0.0, costo=0),
    P("Motor Químico", "Motor pequeño para ajustes finos de órbita.",
      dv=450, masa=0.45, pot=2.5, costo=35),
    P("Motor Iónico", "Motor muy eficiente para viajes largos (Luna, Marte).",
      dv=3500, masa=1.30, pot=18.0, costo=95),
]

# --- PANELES SOLARES ---
ENERGIAS = [
    P("Paneles básicos", "Paneles pegados al cuerpo del cohete. Generan poca energía.",
      gen=6.0, masa=0.18, costo=15),
    P("Paneles desplegables", "Alas solares que se abren después del lanzamiento. Generan el doble.",
      gen=18.0, masa=0.45, costo=40),
    P("Paneles de alta eficiencia", "Paneles especiales para misiones lejanas. Generan mucha energía.",
      gen=42.0, masa=0.90, costo=85),
]

# --- ANTENAS (COMUNICACIONES) ---
COMMS = [
    P("Antena simple", "Envía datos lentamente. Bajo consumo de energía.",
      enlace=10, masa=0.12, pot=1.5, costo=15),
    P("Antena de banda S", "Envía datos a velocidad media. Buena para la mayoría de misiones.",
      enlace=60, masa=0.30, pot=5.0, costo=40),
    P("Antena de alta ganancia", "Envía datos rápidamente desde muy lejos (Luna, Marte).",
      enlace=250, masa=0.65, pot=12.0, costo=80),
]

# --- INSTRUMENTOS CIENTÍFICOS ---
INSTRS = [
    P("Cámara fotográfica", "Toma fotos de la Tierra. Necesita permiso especial.",
      tag="optico", masa=0.25, pot=2.5, datos=8, ciencia=55, costo=25),
    P("Radar de imágenes", "Ve a través de las nubes usando microondas.",
      tag="radar", masa=0.85, pot=11.0, datos=45, ciencia=80, costo=70),
    P("Espectrómetro", "Analiza de qué están hechas las atmósferas y superficies.",
      tag="espectro", masa=0.50, pot=4.5, datos=20, ciencia=85, costo=60),
    P("Sensor térmico", "Mide el calor de los planetas.",
      tag="ir", masa=0.75, pot=7.5, datos=35, ciencia=95, costo=90),
    P("Repetidor de datos", "Retransmite mensajes entre estaciones en la Tierra.",
      tag="comm", masa=0.40, pot=6.0, datos=5, ciencia=65, costo=45),
    P("Detector de radiación", "Mide la radiación espacial alrededor del cohete.",
      tag="particulas", masa=0.20, pot=1.5, datos=6, ciencia=65, costo=30),
]

# --- PROTECCIÓN (BLINDAJE) ---
BLINDAJES = [
    P("Protección básica", "Aluminio estándar. Suficiente para órbita baja.",
      prot=10, masa=0.10, costo=10),
    P("Protección térmica", "Aislamiento contra el frío y calor extremos.",
      prot=30, masa=0.45, costo=40),
    P("Protección espacial", "Escudo reforzado contra radiación del espacio profundo.",
      prot=50, masa=1.10, costo=85),
]

# --- CATEGORÍAS DEL MENÚ DE CONSTRUCCIÓN ---
CATEGORIAS = [
    ("Tamaño", "formato", FORMATOS_CUBESAT),
    ("Seguridad", "seguridad", MECANISMOS),
    ("Destino", "orbita", ORBITAS),
    ("Lanzador", "lanz", LANZADORES),
    ("Motor", "motor", MOTORES),
    ("Energía", "energia", ENERGIAS),
    ("Antena", "comm", COMMS),
    ("Instrumento", "instr", INSTRS),
    ("Protección", "blind", BLINDAJES),
]

TAGS = {
    "optico": "cámara", "radar": "radar", "espectro": "espectrómetro",
    "ir": "sensor térmico", "comm": "repetidor", "particulas": "detector de radiación"
}

# --- MISIONES ---
MISIONES = [
    {"nombre": "Vigía de la Tierra", "tipo": "Observación terrestre", "presupuesto": 180,
     "orbitas": [0, 1], "tags": ["optico", "radar", "ir"], "prot": 10, "cmin": 50,
     "desc": "Cohete pequeño para vigilar el clima, los océanos y el cambio climático desde órbita baja."},
    {"nombre": "Cohete de Comunicaciones", "tipo": "Comunicaciones", "presupuesto": 360,
     "orbitas": [2], "tags": ["comm"], "prot": 25, "cmin": 60,
     "desc": "Cohete grande que se queda fijo sobre un punto de la Tierra para transmitir televisión y datos."},
    {"nombre": "Explorador Lunar", "tipo": "Exploración lunar", "presupuesto": 480,
     "orbitas": [3], "tags": ["espectro", "radar", "particulas"], "prot": 30, "cmin": 70,
     "desc": "Cohete que viaja a la Luna para mapear su superficie y buscar hielo en los polos."},
    {"nombre": "Estación de Relevo", "tipo": "Telemetría orbital", "presupuesto": 230,
     "orbitas": [0], "tags": ["comm", "optico"], "prot": 10, "cmin": 55,
     "desc": "Cohete que orbita cerca de la Tierra y retransmite datos de otras misiones."},
    {"nombre": "Explorador de Marte", "tipo": "Exploración de Marte", "presupuesto": 750,
     "orbitas": [4], "tags": ["espectro", "ir", "radar"], "prot": 45, "cmin": 80,
     "desc": "Cohete interplanetario que viaja a Marte para analizar su atmósfera y su suelo."},
]

cfg = {"zoom_extra": 1.0, "velocidad": 3}

def nave_default():
    return {c[1]: 0 for c in CATEGORIAS}

game = {"mision": None, "nave": nave_default()}
player_start = (600, 450)

ETQ = {
    "masa": "peso {} kg", "masa_chasis": "chasis {} kg", "cap_max": "límite {} kg",
    "pot": "consume {} W", "gen": "genera {} W", "dv": "movilidad {} m/s",
    "enlace": "envía {} GB/día", "datos": "genera {} GB/día", "ciencia": "ciencia {}",
    "prot": "protección {}", "cap": "lanzador {} kg", "costo": "${}M",
    "solar": "sol x{}", "enl": "señal x{}", "dv_req": "necesita {} m/s", "rad": "radiación {}"
}

def detalle(c):
    partes = [ETQ[k].format(v) for k, v in c.items() if k in ETQ]
    return c["nombre"] + " (" + ", ".join(partes) + "). " + c["info"]

def evaluar(idx_mision):
    n = game["nave"]
    mis = MISIONES[idx_mision] if idx_mision is not None else None
    fmt = FORMATOS_CUBESAT[n["formato"]]
    seg = MECANISMOS[n["seguridad"]]
    orb, lan = ORBITAS[n["orbita"]], LANZADORES[n["lanz"]]
    mot, ene = MOTORES[n["motor"]], ENERGIAS[n["energia"]]
    com, ins, bli = COMMS[n["comm"]], INSTRS[n["instr"]], BLINDAJES[n["blind"]]

    r = {"mis": mis}
    r["masa"] = round(fmt["masa_chasis"] + seg["masa"] + mot["masa"] + ene["masa"] + com["masa"] + ins["masa"] + bli["masa"], 2)
    r["cap"] = min(fmt["cap_max"], lan["cap"])
    r["consumo"] = round(BASE_POT + mot["pot"] + com["pot"] + ins["pot"], 2)
    r["gen"] = round(ene["gen"] * orb["solar"], 2)
    r["datos"] = ins["datos"]
    r["enlace"] = round(com["enlace"] * orb["enl"], 1)
    r["costo"] = fmt["costo"] + seg["costo"] + lan["costo"] + sum(c["costo"] for c in (mot, ene, com, ins, bli))
    r["pres"] = mis["presupuesto"] if mis else None
    r["dv"], r["dv_req"] = mot["dv"], orb["dv_req"]
    r["prot"] = bli["prot"]
    r["prot_req"] = max(orb["rad"], mis["prot"] if mis else 0)
    tag_ok = mis is None or ins["tag"] in mis["tags"]
    recibido = min(1.0, r["enlace"] / max(1, r["datos"]))
    r["ciencia"] = int(ins["ciencia"] * (1 if tag_ok else 0.25) * recibido)
    r["cmin"] = mis["cmin"] if mis else 0

    chk = [
        ("Peso permitido", r["masa"] <= r["cap"],
         f"El cohete pesa {r['masa']} kg y el límite es {r['cap']} kg."),
        ("Seguridad de vuelo", seg["rbf"] and seg["burn"],
         "Falta el interruptor de seguridad o los cables de emergencia. No se puede lanzar."),
        ("Energía suficiente", r["gen"] >= r["consumo"],
         f"Los paneles generan {r['gen']} W pero el cohete consume {r['consumo']} W."),
        ("Antena adecuada", r["enlace"] >= r["datos"],
         f"El instrumento genera {r['datos']} GB/día y la antena solo envía {r['enlace']} GB/día."),
        ("Movilidad (motor)", r["dv"] >= r["dv_req"],
         f"El motor da {r['dv']} m/s y el destino exige {r['dv_req']} m/s."),
        ("Protección", r["prot"] >= r["prot_req"],
         f"Se necesita protección {r['prot_req']} y tienes {r['prot']}."),
    ]
    if mis:
        chk += [
            ("Presupuesto", r["costo"] <= mis["presupuesto"],
             f"Cuesta ${r['costo']}M y el presupuesto es ${mis['presupuesto']}M."),
            ("Destino correcto", n["orbita"] in mis["orbitas"],
             "La misión necesita otro destino."),
            ("Instrumento correcto", tag_ok,
             "El instrumento elegido no sirve para esta misión."),
            ("Ciencia mínima", r["ciencia"] >= mis["cmin"],
             f"Se obtienen {r['ciencia']} puntos y se necesitan {mis['cmin']}."),
        ]
    r["checks"] = chk
    r["ok"] = all(c[1] for c in chk)
    return r

# ======================================================================
#  GUARDADO
# ======================================================================
def hay_partida():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("partida") is not None
    except (OSError, ValueError):
        return False

def guardar(solo_opciones=False):
    data = {"opciones": cfg, "partida": None}
    if solo_opciones:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data["partida"] = json.load(f).get("partida")
        except (OSError, ValueError):
            pass
    else:
        data["partida"] = {"x": player.x, "y": player.y, "mision": game["mision"],
                           "nave": game["nave"]}
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        print("No se pudo guardar la partida")

def cargar_opciones():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f).get("opciones", {}))
    except (OSError, ValueError):
        pass

# ======================================================================
#  MAPA Y JUGADOR
# ======================================================================
SOLIDOS = [
    (0, 0, 2400, 45), (0, 0, 40, 1216), (2376, 0, 30, 1216), (0, 1190, 2400, 30),
    (0, 0, 1210, 170), (1150, 0, 75, 880),
    (40, 150, 100, 420), (130, 570, 320, 160), (790, 570, 275, 190),
    (0, 850, 530, 32), (670, 850, 480, 32),
    (1210, 0, 1190, 135), (1488, 200, 720, 445), (2248, 150, 90, 500),
    (1225, 215, 90, 360), (1255, 725, 295, 110), (2020, 725, 290, 115),
    (1210, 868, 540, 14), (1852, 868, 525, 14),
]
station_map = ImageMap("images/mapa_completo.png", SOLIDOS)
player = Player("images/player.png", *player_start)

OBJ_NAVE = pygame.Rect(1488, 200, 720, 445)
OBJ_PC = pygame.Rect(130, 570, 320, 160)
INTERACTIVOS = {
    "nave": (OBJ_NAVE, OBJ_NAVE.inflate(160, 160), "Construir cohete", PANEL_NAVE),
    "pc": (OBJ_PC, OBJ_PC.inflate(140, 140), "Elegir misión", PANEL_MISION),
}
cerca = None

def clamp_camera(c, view_size, map_size):
    if view_size >= map_size:
        return -(view_size - map_size) // 2
    return max(0, min(c, map_size - view_size))

def apply_zoom():
    global ZOOM, VIEW_W, VIEW_H, view
    fx, fy = SCREEN_W / station_map.width, SCREEN_H / station_map.height
    ZOOM = max(fx, fy) * cfg["zoom_extra"]
    VIEW_W, VIEW_H = int(SCREEN_W / ZOOM), int(SCREEN_H / ZOOM)
    view = pygame.Surface((VIEW_W, VIEW_H))

cargar_opciones()
apply_zoom()
player_mod.movement_speed = cfg["velocidad"]

# ======================================================================
#  INTERFAZ
# ======================================================================
clickables = []
mouse_ui = (0, 0)
aviso = ""
sel_m = 0
det_cat = "formato"

def txt(s, f, color, pos, center=False, surf=None):
    surf = surf or ui
    img = f.render(s, True, color)
    r = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, r)

def wrap(s, f, width):
    lines, cur = [], ""
    for w in s.split():
        if f.size(cur + " " + w)[0] > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines

def button(rect, label, ident, enabled=True, selected=False):
    r = pygame.Rect(rect)
    hover = enabled and r.collidepoint(mouse_ui)
    if not enabled:
        bg, border, fg = (45, 45, 55), (90, 90, 100), (120, 120, 130)
    else:
        bg = (0, 120, 90) if selected else ((0, 90, 200) if hover else (0, 50, 150))
        border = (255, 255, 0) if (selected or hover) else (0, 200, 255)
        fg = (255, 255, 255)
    pygame.draw.rect(ui, bg, r, border_radius=6)
    pygame.draw.rect(ui, border, r, 2, border_radius=6)
    txt(label, font_s if len(label) > 22 else font, fg, r.center, center=True)
    if enabled:
        clickables.append((r, ident))

def ventana(titulo, rect=(80, 60, 640, 480)):
    r = pygame.Rect(rect)
    pygame.draw.rect(ui, (14, 22, 55), r, border_radius=10)
    pygame.draw.rect(ui, (0, 200, 255), r, 3, border_radius=10)
    txt(titulo, font_title, (255, 255, 0), (r.centerx, r.y + 30), center=True)
    pygame.draw.line(ui, (0, 200, 255), (r.x + 20, r.y + 54), (r.right - 20, r.y + 54), 1)
    return r

def draw_menu():
    # TÍTULOS AJUSTADOS EN LA PRIMERA PANTALLA
    txt("SIMULADOR ESPACIAL", font_big, (0, 255, 255), (UI_W // 2, 110), center=True)
    txt("Construye tu Cohete", font_title, (255, 255, 0), (UI_W // 2, 175), center=True)
    button((250, 260, 300, 50), "Continuar", "continuar", enabled=hay_partida())
    button((250, 325, 300, 50), "Nuevo juego", "nuevo")
    button((250, 390, 300, 50), "Opciones", "opciones")
    button((250, 455, 300, 50), "Salir", "salir")

def draw_opciones():
    txt("OPCIONES", font_big, (0, 255, 255), (UI_W // 2, 110), center=True)
    txt("Zoom de cámara", font, (255, 255, 255), (170, 235))
    button((470, 225, 40, 40), "-", "zoom-")
    txt(f"{cfg['zoom_extra']:.1f}x", font, (255, 255, 0), (565, 245), center=True)
    button((620, 225, 40, 40), "+", "zoom+")
    txt("Velocidad del jugador", font, (255, 255, 255), (170, 315))
    button((470, 305, 40, 40), "-", "vel-")
    txt(str(cfg["velocidad"]), font, (255, 255, 0), (565, 325), center=True)
    button((620, 305, 40, 40), "+", "vel+")
    button((250, 440, 300, 50), "Volver", "volver")

def draw_world():
    global cerca
    cam_x = clamp_camera(int(player.x) + player.image.get_width() // 2 - VIEW_W // 2, VIEW_W, station_map.width)
    cam_y = clamp_camera(int(player.y) + player.image.get_height() // 2 - VIEW_H // 2, VIEW_H, station_map.height)
    camera = (cam_x, cam_y)

    cerca = None
    prect = player.rect()
    for clave, (obj, zona, _, _) in INTERACTIVOS.items():
        if prect.colliderect(zona):
            cerca = clave
            break

    view.fill(BG)
    station_map.draw(view, camera)
    if cerca:
        obj = INTERACTIVOS[cerca][0]
        pygame.draw.rect(view, (255, 255, 0), obj.move(-cam_x, -cam_y), 4)
    for s in sprites:
        s.draw(view, camera)
    if pygame.K_F1 in keys_down:
        station_map.draw_debug(view, camera)
    screen.blit(pygame.transform.smoothscale(view, (SCREEN_W, SCREEN_H)), (0, 0))

    mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "ninguna"
    info = font.render(f"Misión: {mision}   |   WASD: caminar   E: interactuar   ESC: menú",
                       True, (255, 255, 255))
    pygame.draw.rect(screen, (0, 0, 0), (10, 10, info.get_width() + 20, 32), border_radius=4)
    screen.blit(info, (20, 17))

    if cerca and estado == ESTACION:
        msg = font.render(f"[E]  {INTERACTIVOS[cerca][2]}", True, (255, 255, 0))
        box = pygame.Rect(0, 0, msg.get_width() + 40, 44)
        box.midbottom = (SCREEN_W // 2, SCREEN_H - 40)
        pygame.draw.rect(screen, (0, 0, 0), box, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 0), box, 2, border_radius=8)
        screen.blit(msg, msg.get_rect(center=box.center))

def barra2(x, y, etiqueta, ratio, texto, ok):
    txt(etiqueta, font_s, (200, 200, 200), (x, y))
    pygame.draw.rect(ui, (40, 45, 70), (x + 82, y + 2, 110, 13), border_radius=4)
    color = (90, 220, 120) if ok else (255, 90, 90)
    pygame.draw.rect(ui, color, (x + 82, y + 2, int(110 * max(0.03, min(1.0, ratio))), 13), border_radius=4)
    txt(texto, font_s, (255, 255, 255), (x + 198, y))

def draw_panel_mision():
    ventana("ELIGE TU MISIÓN")
    for i, m in enumerate(MISIONES):
        etiqueta = m["nombre"] + (" *" if game["mision"] == i else "")
        button((100, 140 + i * 58, 240, 48), etiqueta, ("mision", i), selected=(sel_m == i))
    m = MISIONES[sel_m]
    x, y = 365, 135
    txt(m["nombre"], font, (255, 255, 0), (x, y)); y += 26
    txt(f"Tipo: {m['tipo']}", font_s, (200, 220, 255), (x, y)); y += 20
    for l in wrap("Destino: " + " / ".join(ORBITAS[i]["nombre"] for i in m["orbitas"]), font_s, 330):
        txt(l, font_s, (200, 220, 255), (x, y)); y += 19
    txt(f"Presupuesto: ${m['presupuesto']}M", font_s, (200, 220, 255), (x, y)); y += 20
    txt(f"Ciencia necesaria: {m['cmin']}   Protección mínima: {m['prot']}", font_s, (200, 220, 255), (x, y)); y += 20
    for l in wrap("Instrumento: " + ", ".join(TAGS[t] for t in m["tags"]), font_s, 330):
        txt(l, font_s, (200, 220, 255), (x, y)); y += 19
    y += 6
    for l in wrap(m["desc"], font_s, 330):
        txt(l, font_s, (170, 170, 190), (x, y)); y += 19
    r = evaluar(sel_m)
    ok = sum(1 for c in r["checks"] if c[1])
    color = (90, 230, 120) if r["ok"] else (255, 190, 90)
    txt(f"Tu cohete cumple {ok} de {len(r['checks'])} requisitos.", font_s, color, (x, 405))
    txt("Construye el cohete en el hangar.", font_s, (170, 170, 190), (x, 425))
    button((365, 455, 200, 46), "Aceptar misión", "aceptar")
    button((580, 455, 120, 46), "Cerrar", "cerrar")
    if aviso:
        txt(aviso, font_s, (90, 230, 120), (100, 480))

def draw_panel_nave():
    global det_cat
    ventana("HANGAR - CONSTRUIR COHETE", (20, 15, 760, 570))
    for i, (nombre, clave, lista) in enumerate(CATEGORIAS):
        y = 78 + i * 38
        fila = pygame.Rect(35, y, 395, 34)
        if fila.collidepoint(mouse_ui):
            det_cat = clave
        txt(nombre, font_s, (255, 255, 255), (35, y + 9))
        button((145, y, 32, 34), "<", ("nave", clave, -1, len(lista)))
        pygame.draw.rect(ui, (20, 30, 70), (181, y, 210, 34), border_radius=6)
        if det_cat == clave:
            pygame.draw.rect(ui, (255, 255, 0), (181, y, 210, 34), 1, border_radius=6)
        nom = lista[game["nave"][clave]]["nombre"]
        txt(nom, font_s, (255, 255, 0), (286, y + 17), center=True)
        button((395, y, 32, 34), ">", ("nave", clave, 1, len(lista)))

    lista = next(c[2] for c in CATEGORIAS if c[1] == det_cat)
    for k, l in enumerate(wrap(detalle(lista[game["nave"][det_cat]]), font_s, 395)[:6]):
        txt(l, font_s, (170, 200, 230), (35, 428 + k * 19))

    r = evaluar(game["mision"])
    mis = r["mis"]
    X = 445
    txt("Misión: " + (mis["nombre"] if mis else "ninguna (elige en la computadora)"),
        font_s, (255, 255, 0) if mis else (255, 150, 90), (X, 78))
    rat = lambda a, b: a / b if b else 1.0
    seg_ok = MECANISMOS[game["nave"]["seguridad"]]["rbf"]
    filas = [
        ("Peso", rat(r["masa"], r["cap"]), f"{r['masa']}/{r['cap']} kg", r["masa"] <= r["cap"]),
        ("Seguridad", 1.0 if seg_ok else 0.1, "OK" if seg_ok else "FALTA", seg_ok),
        ("Energía", rat(r["consumo"], r["gen"]), f"{r['consumo']}/{r['gen']} W", r["gen"] >= r["consumo"]),
        ("Antena", rat(r["datos"], r["enlace"]), f"{r['datos']}/{r['enlace']} GB/d", r["enlace"] >= r["datos"]),
        ("Motor", rat(r["dv_req"], r["dv"]), f"{r['dv_req']}/{r['dv']} m/s", r["dv"] >= r["dv_req"]),
        ("Protección", rat(r["prot_req"], r["prot"]), f"{r['prot_req']}/{r['prot']}", r["prot"] >= r["prot_req"]),
    ]
    if mis:
        filas.append(("Costo", rat(r["costo"], r["pres"]), f"${r['costo']}/{r['pres']}M", r["costo"] <= r["pres"]))
        filas.append(("Ciencia", rat(r["ciencia"], r["cmin"]), f"{r['ciencia']}/{r['cmin']}", r["ciencia"] >= r["cmin"]))
    else:
        filas.append(("Costo", 0.0, f"${r['costo']}M", True))

    for i, (et, ra, tx, ok) in enumerate(filas):
        barra2(X, 104 + i * 26, et, ra, tx, ok)

    fallos = [c for c in r["checks"] if not c[1]]
    if not mis:
        msg, col = "Elige una misión para revisar tu cohete.", (200, 200, 200)
    elif fallos:
        msg, col = f"{len(fallos)} problema(s) encontrados:", (255, 120, 90)
    else:
        msg, col = "¡Todo listo para volar!", (90, 230, 120)
    txt(msg, font_s, col, (X, 322))
    if mis and fallos:
        for k, l in enumerate(wrap(fallos[0][0] + ": " + fallos[0][2], font_s, 315)[:8]):
            txt(l, font_s, (255, 200, 170), (X, 344 + k * 19))

    button((445, 515, 200, 44), "Revisar vuelo", "evaluar", enabled=mis is not None)
    button((655, 515, 105, 44), "Cerrar", "cerrar")

def draw_informe():
    r = evaluar(game["mision"])
    mis = r["mis"]
    ventana("REVISIÓN FINAL DEL COHETE", (20, 15, 760, 570))
    exito = r["ok"]
    txt(mis["nombre"] + " - " + FORMATOS_CUBESAT[game["nave"]["formato"]]["nombre"], font, (255, 255, 255), (40, 82))
    txt("LISTO PARA VOLAR" if exito else "NO APTO PARA VOLAR", font_title,
        (90, 230, 120) if exito else (255, 90, 90), (480, 78))
    txt("Lista de revisión", font_s, (255, 255, 0), (40, 118))
    for i, (nombre, ok, _) in enumerate(r["checks"]):
        txt(("[OK] " if ok else "[X]  ") + nombre, font_s, (90, 230, 120) if ok else (255, 100, 100), (40, 142 + i * 26))
    txt("Resultado", font_s, (255, 255, 0), (420, 118))
    y = 142
    fallos = [c for c in r["checks"] if not c[1]]
    if exito:
        lineas = wrap("¡Felicidades! Tu cohete cumple con todos los requisitos: peso, seguridad, energía, antena y protección.", font_s, 330)
        for l in lineas:
            txt(l, font_s, (170, 220, 190), (420, y)); y += 20
    else:
        for nombre, _, causa in fallos:
            for l in wrap("- " + nombre + ": " + causa, font_s, 335):
                if y < 430:
                    txt(l, font_s, (255, 200, 170), (420, y))
                y += 19
            y += 5
    if exito:
        sobra = r["pres"] - r["costo"]
        pts = int(300 + r["ciencia"] * 4 + (1 - r["costo"] / r["pres"]) * 300 + (1 - r["masa"] / r["cap"]) * 200)
        txt(f"Puntuación: {pts} puntos", font_title, (255, 255, 0), (40, 440))
        txt(f"Ciencia {r['ciencia']}  |  Sobra ${sobra}M  |  Peso libre {round(r['cap'] - r['masa'], 2)} kg",
            font_s, (200, 220, 255), (40, 478))
    else:
        txt(f"Puntuación parcial: {sum(1 for c in r['checks'] if c[1]) * 30}", font_title, (255, 150, 90), (40, 440))
        txt("Arregla los problemas en el hangar y vuelve a revisar.", font_s, (200, 220, 255), (40, 478))
    button((450, 515, 190, 44), "Volver al hangar", "taller")
    button((655, 515, 105, 44), "Cerrar", "cerrar")

# ======================================================================
#  ACCIONES
# ======================================================================
def iniciar(continuar):
    global estado
    keys_down.clear()
    game["mision"], game["nave"] = None, nave_default()
    player.x, player.y = player_start
    if continuar:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                p = json.load(f)["partida"]
            player.x, player.y = p["x"], p["y"]
            game["mision"] = p["mision"]
            for _, clave, lista in CATEGORIAS:
                v = int(p["nave"].get(clave, 0))
                game["nave"][clave] = max(0, min(v, len(lista) - 1))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    estado = ESTACION

def on_click(ident):
    global estado, running, sel_m, aviso, det_cat
    if isinstance(ident, tuple):
        if ident[0] == "mision":
            sel_m, aviso = ident[1], ""
        elif ident[0] == "nave":
            _, clave, delta, n = ident
            det_cat = clave
            game["nave"][clave] = (game["nave"][clave] + delta) % n
            guardar()
        return
    if ident == "continuar":
        iniciar(True)
    elif ident == "nuevo":
        iniciar(False)
    elif ident == "opciones":
        estado = OPCIONES
    elif ident == "salir":
        running = False
    elif ident == "volver":
        guardar(solo_opciones=True)
        estado = MENU
    elif ident in ("zoom-", "zoom+"):
        cfg["zoom_extra"] = round(max(0.6, min(1.8, cfg["zoom_extra"] + (0.1 if ident == "zoom+" else -0.1))), 1)
        apply_zoom()
        guardar(solo_opciones=True)
    elif ident in ("vel-", "vel+"):
        cfg["velocidad"] = max(2, min(6, cfg["velocidad"] + (1 if ident == "vel+" else -1)))
        player_mod.movement_speed = cfg["velocidad"]
    elif ident == "aceptar":
        game["mision"] = sel_m
        aviso = f"Misión «{MISIONES[sel_m]['nombre']}» aceptada."
        guardar()
    elif ident == "evaluar":
        estado = PANEL_INFORME
    elif ident == "taller":
        estado = PANEL_NAVE
    elif ident == "cerrar":
        estado = ESTACION
        aviso = ""

# ======================================================================
#  BUCLE PRINCIPAL
# ======================================================================
running = True
while running:
    if estado == MENU:
        MARGEN_DER = 60
        # El bloque de botones va de x=250 a x=550 dentro del lienzo
        OFF_X = SCREEN_W - 550 - MARGEN_DER
    else:
        OFF_X = (SCREEN_W - UI_W) // 2
    OFF_Y = (SCREEN_H - UI_H) // 2

    mx, my = pygame.mouse.get_pos()
    mouse_ui = (mx - OFF_X, my - OFF_Y)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            keys_down.add(event.key)
            if event.key == pygame.K_ESCAPE:
                if estado == MENU:
                    running = False
                elif estado == OPCIONES:
                    on_click("volver")
                elif estado == ESTACION:
                    guardar()
                    estado = MENU
                else:
                    on_click("cerrar")
            elif event.key == pygame.K_e and estado == ESTACION and cerca:
                estado = INTERACTIVOS[cerca][3]
                if estado == PANEL_MISION and game["mision"] is not None:
                    sel_m = game["mision"]
                keys_down.clear()

        elif event.type == pygame.KEYUP:
            keys_down.discard(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = (event.pos[0] - OFF_X, event.pos[1] - OFF_Y)
            for rect, ident in list(clickables):
                if rect.collidepoint(pos):
                    on_click(ident)
                    break

    if estado == ESTACION:
        player.update(station_map)

    clickables.clear()
    ui.fill((0, 0, 0, 0))

    if estado == MENU:
        menu_bg.draw(screen)
        draw_menu()
    elif estado == OPCIONES:
        screen.fill(BG)
        draw_opciones()
    else:
        draw_world()
        if estado in (PANEL_MISION, PANEL_NAVE, PANEL_INFORME):
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            {PANEL_MISION: draw_panel_mision, PANEL_NAVE: draw_panel_nave, PANEL_INFORME: draw_informe}[estado]()

    screen.blit(ui, (OFF_X, OFF_Y))
    pygame.display.flip()
    clock.tick(60)

menu_bg.release()
guardar(solo_opciones=True)
pygame.quit()
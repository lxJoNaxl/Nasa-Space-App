import json
import math
import os
import random
import pygame
from Fondo.FondoMenu import FondoMenu
import player as player_mod
from sprite import sprites
from player import Player
from input import keys_down
from map import ImageMap
from despegue import Despegue

# ======================================================================
#  INICIALIZACIÓN
# ======================================================================
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_W, SCREEN_H = screen.get_size()
pygame.display.set_caption("Simulador Espacial - Construye tu Cohete")
clock = pygame.time.Clock()

UI_W, UI_H = 800, 600
OFF_X, OFF_Y = (SCREEN_W - UI_W) // 2, (SCREEN_H - UI_H) // 2
ui = pygame.Surface((UI_W, UI_H), pygame.SRCALPHA)

font_s = pygame.font.SysFont(None, 19)
font = pygame.font.SysFont(None, 24)
font_title = pygame.font.SysFont(None, 38)
font_big = pygame.font.SysFont(None, 64)
font_star = pygame.font.SysFont(None, 26)

BG = (15, 15, 30)
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.json")
menu_bg = FondoMenu("planeta rotando.mp4", (SCREEN_W, SCREEN_H), BG)

# Estados
(MENU, OPCIONES, ESTACION, PANEL_MISION, PANEL_NAVE, PANEL_INFORME,
 PANEL_COHETE, GLOSARIO, DESPEGUE, VIAJE, LUNA, MISION_OK) = range(12)
anim = None  # animación de despegue activa
estado = MENU

# ----------------------------------------------------------------------
#  VIAJE Y ESCENA LUNAR
# ----------------------------------------------------------------------
DESTINO_FONDO = {3: "FondoEspacio.png"}  # índice de ORBITAS -> imagen del mapa (en /images)
T_TEXTO = 3.5  # segundos mostrando "VIAJE EN PROGRESO"
T_FADE = 0.8  # segundos que tarda en ponerse negra la pantalla
T_NEGRO = 0.8  # segundos que se queda en negro
LUNA_DEMORA = 0.5  # segundos antes de que entre el cohete
LUNA_LLEGADA = 3.5  # segundos que tarda en llegar volando

# Zona marcada en rojo (centro y tamaño máximo), como fracción del mapa (0 a 1)
LUNA_CX = 0.092  # centro horizontal del cohete
LUNA_CY = 0.575  # centro vertical del cohete
LUNA_LARGO = 0.165  # largo del cohete más grande (fracción del ancho del mapa)
LUNA_GROSOR = 0.15  # grosor máximo (fracción del alto del mapa)

# Robot al fondo derecho del mapa (imágenes dentro de /images)
ROBOT_ROTO = "ROBOT(ROTO).png"
ROBOT_REPARADO = "ROBOT(REPARADO).png"
ROBOT_X = 0.93  # posición horizontal (fracción del ancho del mapa)
ROBOT_BASE_Y = 0.75  # donde apoya los pies (fracción del alto del mapa)
ROBOT_ALTO = 0.17  # alto del robot (fracción del alto del mapa)
T_REPARAR = 5.0  # segundos que hay que mantener presionada la E

# Cohetes SIN estela (uno por nivel, mismo orden que LANZADORES).
# Es el sprite que se ve cuando el cohete ya llegó al planeta.
# >>> AJUSTA ESTOS NOMBRES a los de tus archivos dentro de /images <<<
COHETES_SIN_ESTELA = ["COHETE_NIVEL1(SIN ESTELA).png",
                      "COHETE_NIVEL2(SIN ESTELA).png",
                      "COHETE_NIVEL3(SIN ESTELA).png"]

# Objetos que hay que recoger para reparar el robot: (id, archivo en /images, nombre, color si falta el PNG)
OBJETOS = [
    ("antena", "ANTENA.png", "Antena", (230, 200, 60, 255)),
    ("placa", "PLACA.png", "Placa", (60, 200, 120, 255)),
    ("bateria", "BATERIA.png", "Batería", (80, 160, 255, 255)),
]
ITEM_ALTO = 0.06  # alto de cada objeto (fracción del alto del mapa)

# Final de la misión
ASTRO_WIN = "astroWIN.png"
N_PARPADEOS = 5  # veces que alterna entre el sprite normal y astroWIN
T_PARPADEO = 0.25  # segundos por cada cambio de sprite
T_CELEBRAR = N_PARPADEOS * 2 * T_PARPADEO
T_SUBIR = 1.2  # segundos que tarda en subir a la nave
T_REGRESO = 6.0  # segundos del vuelo de regreso a la Tierra
TIERRA_X, TIERRA_Y = 0.63, 0.095  # dónde está la Tierra en el mapa lunar (fracción)
BONIFICACION = 100  # millones de $

viaje_t0 = 0
luna_t0 = 0
luna_map = None
luna_view = None
luna_cohete = None
luna_cohete_pos = (0, 0)
luna_fase = "bajando"
COHETES_HORIZ = None  # cohetes sin llama y acostados (se calculan una vez)
robot_roto = robot_ok = None
robot_rect = pygame.Rect(0, 0, 1, 1)
robot_zona = pygame.Rect(0, 0, 1, 1)
robot_reparado = False
reparar_t0 = None
reparado_t = 0
COHETES_HORIZ_LL = None  # cohetes acostados CON llama (para la llegada y el vuelo de regreso)
luna_cohete_llama = None
luna_items = []
nave_rect = pygame.Rect(0, 0, 1, 1)
nave_zona = pygame.Rect(0, 0, 1, 1)
astro_win = None
fin_t0 = 0
luna_activa = False  # hay una misión lunar en curso (se guarda para "Continuar")
ultima_mision = "-"
negro = pygame.Surface((SCREEN_W, SCREEN_H))
negro.fill((0, 0, 0))
ESTRELLAS = [(random.random(), random.random(), random.uniform(0.03, 0.12), random.choice([1, 2, 2, 3]))
             for _ in range(140)]


# ======================================================================
#  DATOS DEL JUEGO (Lenguaje Simple)
# ======================================================================
def P(nombre, info, simple, **kw):
    return {"nombre": nombre, "info": info, "simple": simple, **kw}


BASE_POT = 1.5

FORMATOS_CUBESAT = [
    P("Cohete Pequeño", "Caja pequeña. Límite: 1.33 kg.", "Para misiones cortas.", vol=1.0, masa_chasis=0.35,
      cap_max=1.33, costo=15),
    P("Cohete Mediano", "Caja mediana. Límite: 4 kg.", "Equilibrado para la Luna.", vol=3.0, masa_chasis=0.95,
      cap_max=4.00, costo=35),
    P("Cohete Grande", "Caja grande. Límite: 12 kg.", "Para viajes a Marte.", vol=6.0, masa_chasis=1.80, cap_max=12.00,
      costo=70),
]

MECANISMOS = [
    P("Sin seguridad", "Peligroso.", "No se puede lanzar.", rbf=False, burn=False, masa=0.0, costo=0),
    P("Seguridad completa", "Interruptor y cables.", "Obligatorio para despegar.", rbf=True, burn=True, masa=0.15,
      costo=20),
]

ORBITAS = [
    P("Cerca de la Tierra", "Órbita Baja (LEO).", "Cerca de casa.", factor=1.0, solar=1.0, enl=1.0, dv_req=0, rad=10),
    P("Sobre los Polos", "Órbita Polar.", "Ve todo el planeta.", factor=0.85, solar=1.0, enl=0.9, dv_req=250, rad=15),
    P("Lejos de la Tierra", "Órbita Geoestacionaria.", "Fijo en el cielo.", factor=0.28, solar=1.0, enl=0.7,
      dv_req=1800, rad=25),
    P("La Luna", "Órbita Lunar.", "Nuestro satélite.", factor=0.22, solar=1.0, enl=0.45, dv_req=2200, rad=30),
    P("Marte", "Órbita Marciana.", "El planeta rojo.", factor=0.12, solar=0.8, enl=0.15, dv_req=3200, rad=45),
]

LANZADORES = [
    P("Cohete Electron", "El más pequeño.", "Solo va cerca de la Tierra.", cap=15.0, costo=50, img="COHETE__NIVEL1.png",
      empresa="Rocket Lab", altura=18),
    P("Cohete Falcon 9", "Tamaño medio.", "Llega a la Luna.", cap=30.0, costo=140, img="COHETE_NIVEL2.png",
      empresa="SpaceX", altura=70),
    P("Cohete Falcon Heavy", "El más potente.", "El único que llega a Marte.", cap=50.0, costo=330,
      img="COHETE_NIVEL3.png", empresa="SpaceX", altura=70),
]

MOTORES = [
    P("Sin motor", "No se mueve.", "No sirve para viajar.", dv=0, masa=0.0, pot=0.0, costo=0),
    P("Motor Químico", "Fuerza media.", "Sirve para cerca de la Tierra.", dv=450, masa=0.45, pot=2.5, costo=35),
    P("Motor Iónico", "Fuerza extrema.", "Obligatorio para Luna y Marte.", dv=3500, masa=1.30, pot=10.0, costo=95),
]

ENERGIAS = [
    P("Paneles Pequeños", "Poca energía.", "Suficiente para la Tierra.", gen=6.0, masa=0.18, costo=15),
    P("Paneles Medianos", "Energía media.", "Suficiente para la Luna.", gen=18.0, masa=0.45, costo=40),
    P("Paneles Grandes", "Máxima energía.", "Obligatorio para Marte.", gen=42.0, masa=0.90, costo=85),
]

COMMS = [
    P("Antena Lenta", "Poca señal.", "Para cerca de la Tierra.", enlace=10, masa=0.12, pot=1.5, costo=15),
    P("Antena Media", "Señal media.", "Para la Luna.", enlace=60, masa=0.30, pot=5.0, costo=40),
    P("Antena Rápida", "Señal potente.", "Obligatoria para Marte.", enlace=250, masa=0.65, pot=12.0, costo=80),
]

INSTRS = [
    P("Cámara", "Fotos.", "Para ver la Tierra.", tag="optico", masa=0.25, pot=2.5, datos=8, ciencia=55, costo=25),
    P("Radar", "Ve nubes.", "Para atmósferas.", tag="radar", masa=0.85, pot=11.0, datos=45, ciencia=80, costo=70),
    P("Espectrómetro", "Analiza suelos.", "Para analizar planetas.", tag="espectro", masa=0.50, pot=4.5, datos=20,
      ciencia=85, costo=60),
    P("Sensor Térmico", "Mide calor.", "Para medir temperatura.", tag="ir", masa=0.75, pot=7.5, datos=35, ciencia=95,
      costo=90),
    P("Repetidor", "Repite datos.", "Para comunicaciones.", tag="comm", masa=0.40, pot=6.0, datos=5, ciencia=65,
      costo=45),
    P("Detector", "Mide radiación.", "Para medir el espacio.", tag="particulas", masa=0.20, pot=1.5, datos=6,
      ciencia=65, costo=30),
]

BLINDAJES = [
    P("Blindaje Fino", "Protección baja.", "Para cerca de la Tierra.", prot=10, masa=0.10, costo=10),
    P("Blindaje Medio", "Protección media.", "Para la Luna.", prot=30, masa=0.45, costo=40),
    P("Blindaje Grueso", "Protección máxima.", "Obligatorio para Marte.", prot=50, masa=1.10, costo=85),
]

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

TAGS = {"optico": "Cámara", "radar": "Radar", "espectro": "Espectrómetro", "ir": "Sensor Térmico", "comm": "Repetidor",
        "particulas": "Detector"}

MISIONES = [
    {"nombre": "Vigía de la Tierra", "tipo": "Observación", "presupuesto": 180, "orbitas": [0, 1],
     "tags": ["optico", "radar", "ir"], "prot": 10, "cmin": 50,
     "historia": "Ver cómo cambia el clima.", "necesitas": "Cámara, paneles pequeños y cohete Electron.",
     "mision_real": "Como Landsat.",
     "recomendados": {"formato": 0, "motor": 1, "energia": 0, "comm": 0, "instr": 0, "blind": 0, "lanz": 0,
                      "seguridad": 1, "orbita": 0}, "desc": "Vigilar la Tierra."},
    {"nombre": "Comunicaciones", "tipo": "Comms", "presupuesto": 360, "orbitas": [2], "tags": ["comm"], "prot": 25,
     "cmin": 60,
     "historia": "Llevar internet remoto.", "necesitas": "Repetidor, antena rápida y cohete Falcon 9.",
     "mision_real": "Satélites geoestacionarios.",
     "recomendados": {"formato": 1, "motor": 1, "energia": 1, "comm": 2, "instr": 4, "blind": 1, "lanz": 1,
                      "seguridad": 1, "orbita": 2}, "desc": "Fijo sobre la Tierra."},
    {"nombre": "Explorador Lunar", "tipo": "Reparación lunar", "presupuesto": 480, "orbitas": [3],
     "tags": ["espectro", "radar", "particulas"], "prot": 30, "cmin": 70,
     "historia": "Misión de reparación de un repetidor lunar: el repetidor que enlaza la Luna con la Tierra dejó de funcionar y debes llegar a arreglarlo.",
     "necesitas": "Motor iónico, blindaje medio y Falcon 9.", "mision_real": "CAPSTONE.",
     "recomendados": {"formato": 1, "motor": 2, "energia": 1, "comm": 1, "instr": 2, "blind": 1, "lanz": 1,
                      "seguridad": 1, "orbita": 3}, "desc": "Reparar un repetidor en la Luna."},
    {"nombre": "Estación de Relevo", "tipo": "Telemetría", "presupuesto": 230, "orbitas": [0],
     "tags": ["comm", "optico"], "prot": 10, "cmin": 55,
     "historia": "Retransmitir datos.", "necesitas": "Repetidor, antena lenta y cohete Electron.",
     "mision_real": "TDRS.",
     "recomendados": {"formato": 0, "motor": 0, "energia": 0, "comm": 0, "instr": 4, "blind": 0, "lanz": 0,
                      "seguridad": 1, "orbita": 0}, "desc": "Órbita cercana."},
    {"nombre": "Explorador de Marte", "tipo": "Marte", "presupuesto": 750, "orbitas": [4],
     "tags": ["espectro", "ir", "radar"], "prot": 45, "cmin": 80,
     "historia": "Analizar Marte.", "necesitas": "Falcon Heavy, motor iónico, paneles y blindaje grueso.",
     "mision_real": "MarCO.",
     "recomendados": {"formato": 2, "motor": 2, "energia": 2, "comm": 2, "instr": 3, "blind": 2, "lanz": 2,
                      "seguridad": 1, "orbita": 4}, "desc": "Viaje interplanetario."},
]

cfg = {"zoom_extra": 1.0, "velocidad": 3}


def nave_default():
    return {c[1]: 0 for c in CATEGORIAS}


game = {"mision": None, "nave": nave_default(), "dinero": 0}
player_start = (600, 450)

GLOSARIO_TEXTO = [
    ("Peso", "Si pesa más de lo permitido, no despega."),
    ("Energía", "Electricidad para los aparatos."),
    ("Antena", "Para enviar datos a la Tierra."),
    ("Motor", "Fuerza para viajar."),
    ("Protección", "Escudo contra la radiación."),
    ("Órbita", "El camino alrededor de un planeta."),
    ("Presupuesto", "Dinero. Si te pasas, fallas."),
    ("Ciencia", "Puntos por descubrir."),
]

# ======================================================================
#  FUNCIONES
# ======================================================================
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
    r["masa"] = round(
        fmt["masa_chasis"] + seg["masa"] + mot["masa"] + ene["masa"] + com["masa"] + ins["masa"] + bli["masa"], 2)
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

    # --- LISTA DE VERIFICACIÓN TRADUCIDA A LENGUAJE HUMANO ---
    chk = []
    chk.append(
        ("Peso permitido", r["masa"] <= r["cap"], "El cohete pesa demasiado. Usa un cohete más grande o quita equipo."))
    chk.append(("Seguridad de vuelo", seg["rbf"] and seg["burn"], "Necesitas poner: Seguridad completa."))
    chk.append(("Energía suficiente", r["gen"] >= r["consumo"],
                "No hay suficiente electricidad. Necesitas poner: Paneles mejores."))
    chk.append(("Antena adecuada", r["enlace"] >= r["datos"],
                "La antena no puede enviar tantos datos. Necesitas poner: Antena más rápida."))
    chk.append(("Movilidad (motor)", r["dv"] >= r["dv_req"],
                "El motor no tiene fuerza para llegar. Necesitas poner: Motor más potente."))
    chk.append(
        ("Protección", r["prot"] >= r["prot_req"], "Hay demasiada radiación. Necesitas poner: Blindaje más grueso."))

    if mis:
        chk.append(
            ("Presupuesto", r["costo"] <= mis["presupuesto"], "Te pasaste del presupuesto. Usa piezas más baratas."))
        chk.append(
            ("Destino correcto", n["orbita"] in mis["orbitas"], "El destino no es el correcto para esta misión."))
        chk.append(("Instrumento correcto", tag_ok, "El instrumento no sirve para esta misión. Cambia el Instrumento."))
        chk.append(
            ("Ciencia mínima", r["ciencia"] >= mis["cmin"], "El instrumento no da suficiente ciencia. Usa uno mejor."))

    r["checks"] = chk
    r["ok"] = all(c[1] for c in chk)
    return r


def puntaje(r):
    return int(300 + r["ciencia"] * 4 + (1 - r["costo"] / r["pres"]) * 300 + (1 - r["masa"] / r["cap"]) * 200)


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
        en_estacion = not luna_activa
        data["partida"] = {"x": player.x if en_estacion else player_start[0],
                           "y": player.y if en_estacion else player_start[1],
                           "mision": game["mision"], "nave": game["nave"],
                           "dinero": game["dinero"], "luna": luna_guardado()}
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


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
    (0, 0, 1210, 170), (1150, 0, 75, 880), (40, 150, 100, 420), (130, 570, 320, 160), (790, 570, 275, 190),
    (0, 850, 530, 32), (670, 850, 480, 32), (1210, 0, 1190, 135), (1488, 200, 720, 445), (2248, 150, 90, 500),
    (1225, 215, 90, 360), (1255, 725, 295, 110), (2020, 725, 290, 115), (1210, 868, 540, 14), (1852, 868, 525, 14),
]
station_map = ImageMap("images/mapa_completo.png", SOLIDOS)
player = Player("images/ASTRONAUTA.png", *player_start)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_cohete(nombre):
    try:
        img = pygame.image.load(os.path.join(BASE_DIR, "images", nombre)).convert_alpha()
    except (pygame.error, FileNotFoundError):
        img = pygame.Surface((60, 200), pygame.SRCALPHA)
        img.fill((200, 200, 200, 255))
    caja = img.get_bounding_rect()
    if caja.width > 0 and caja.height > 0:
        img = img.subsurface(caja).copy()
    return img


def cargar_cohete_sin_estela(i):
    """Sprite del cohete nivel i+1 SIN estela. Si falta el PNG, quita la llama del original."""
    ruta = os.path.join(BASE_DIR, "images", COHETES_SIN_ESTELA[i])
    if os.path.exists(ruta):
        return cargar_cohete(COHETES_SIN_ESTELA[i])
    print("No se encontró", COHETES_SIN_ESTELA[i], "- se usa el cohete original sin llama")
    return sin_llama(COHETES_IMG[i])


def escalar(img, factor):
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, int(w * factor)), max(1, int(h * factor))))


COHETES_IMG = [cargar_cohete(l["img"]) for l in LANZADORES]
ALTO_MAX = max(i.get_height() for i in COHETES_IMG)
ANCHO_MAX = max(i.get_width() for i in COHETES_IMG)

CENTRO_HANGAR = (1846, 423)
FACTOR_HANGAR = min(660 / ALTO_MAX, 320 / ANCHO_MAX)
COHETES_HANGAR = [pygame.transform.rotate(escalar(i, FACTOR_HANGAR), -90) for i in COHETES_IMG]
FACTOR_TARJETA = 175 / ALTO_MAX
COHETES_TARJETA = [escalar(i, FACTOR_TARJETA) for i in COHETES_IMG]

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


# ----------------------------------------------------------------------
#  DINERO (solo se muestra en el mapa de la estación)
# ----------------------------------------------------------------------
DINERO_PNG = "dinero.png"
DINERO_ALTO = 80  # alto del sprite en pantalla (px)
_dinero_img = None


def draw_dinero():
    """PNG del dinero arriba a la derecha, con el total ganado en las misiones encima."""
    global _dinero_img
    if _dinero_img is None:
        img = cargar_imagen(DINERO_PNG, (60, 160, 80, 255))
        _dinero_img = escalar(img, DINERO_ALTO / img.get_height())
    rect = _dinero_img.get_rect(topright=(SCREEN_W - 10, 10))
    screen.blit(_dinero_img, rect)
    s = f"${game['dinero']}M"
    sombra = font_title.render(s, True, (0, 0, 0))
    texto = font_title.render(s, True, (255, 255, 255))
    c = rect.center  # mueve este punto si el número no cae bien sobre tu imagen
    screen.blit(sombra, sombra.get_rect(center=(c[0] + 2, c[1] + 2)))
    screen.blit(texto, texto.get_rect(center=c))


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
    cohete = COHETES_HANGAR[game["nave"]["lanz"]]
    view.blit(cohete,
              (CENTRO_HANGAR[0] - cohete.get_width() // 2 - cam_x, CENTRO_HANGAR[1] - cohete.get_height() // 2 - cam_y))
    if cerca:
        obj = INTERACTIVOS[cerca][0]
        pygame.draw.rect(view, (255, 255, 0), obj.move(-cam_x, -cam_y), 4)
    for s in sprites:
        s.draw(view, camera)
    if pygame.K_F1 in keys_down:
        station_map.draw_debug(view, camera)
    screen.blit(pygame.transform.smoothscale(view, (SCREEN_W, SCREEN_H)), (0, 0))

    mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "ninguna"
    nombre_cohete = LANZADORES[game["nave"]["lanz"]]["nombre"]
    info = font.render(
        f"Misión: {mision}   |   Cohete: {nombre_cohete}   |   H: Glosario   |   ESC: Menú",
        True, (255, 255, 255))
    pygame.draw.rect(screen, (0, 0, 0), (10, 10, info.get_width() + 20, 32), border_radius=4)
    screen.blit(info, (20, 17))

    draw_dinero()

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
    txt(m["nombre"], font, (255, 255, 0), (x, y))
    y += 26
    txt(f"Tipo: {m['tipo']}", font_s, (200, 220, 255), (x, y))
    y += 20
    txt("Historia:", font_s, (255, 255, 0), (x, y))
    y += 18
    for l in wrap(m["historia"], font_s, 330):
        txt(l, font_s, (200, 220, 255), (x, y))
        y += 19
    y += 4
    txt("Qué necesitas:", font_s, (255, 255, 0), (x, y))
    y += 18
    for l in wrap(m["necesitas"], font_s, 330):
        txt(l, font_s, (200, 220, 255), (x, y))
        y += 19
    y += 4
    txt("Misión real parecida:", font_s, (255, 255, 0), (x, y))
    y += 18
    for l in wrap(m["mision_real"], font_s, 330):
        txt(l, font_s, (170, 170, 190), (x, y))
        y += 19
    r = evaluar(sel_m)
    ok = sum(1 for c in r["checks"] if c[1])
    color = (90, 230, 120) if r["ok"] else (255, 190, 90)
    txt(f"Tu cohete cumple {ok} de {len(r['checks'])} requisitos.", font_s, color, (x, 420))
    button((365, 455, 200, 46), "Aceptar misión", "aceptar")
    button((580, 455, 120, 46), "Cerrar", "cerrar")


def draw_panel_nave():
    global det_cat
    ventana("HANGAR - CONSTRUIR COHETE", (20, 15, 760, 570))
    mis = MISIONES[game["mision"]] if game["mision"] is not None else None

    for i, (nombre, clave, lista) in enumerate(CATEGORIAS):
        y = 78 + i * 38
        fila = pygame.Rect(35, y, 395, 34)
        if fila.collidepoint(mouse_ui):
            det_cat = clave

        if mis and clave in mis["recomendados"]:
            idx_rec = mis["recomendados"][clave]
            if game["nave"][clave] == idx_rec:
                txt("★", font_star, (255, 255, 0), (20, y + 4))
            else:
                txt("☆", font_star, (150, 150, 150), (20, y + 4))
        else:
            txt("☆", font_star, (150, 150, 150), (20, y + 4))

        txt(nombre, font_s, (255, 255, 255), (45, y + 9))
        button((145, y, 32, 34), "<", ("nave", clave, -1, len(lista)))
        pygame.draw.rect(ui, (20, 30, 70), (181, y, 210, 34), border_radius=6)
        if det_cat == clave:
            pygame.draw.rect(ui, (255, 255, 0), (181, y, 210, 34), 1, border_radius=6)
        nom = lista[game["nave"][clave]]["nombre"]
        txt(nom, font_s, (255, 255, 0), (286, y + 17), center=True)
        button((395, y, 32, 34), ">", ("nave", clave, 1, len(lista)))

    lista = next(c[2] for c in CATEGORIAS if c[1] == det_cat)
    actual = lista[game["nave"][det_cat]]
    txt("Simple:", font_s, (255, 255, 0), (35, 420))
    for k, l in enumerate(wrap(actual["simple"], font_s, 395)[:2]):
        txt(l, font_s, (170, 200, 230), (35, 440 + k * 19))

    if mis and det_cat in mis["recomendados"]:
        idx_rec = mis["recomendados"][det_cat]
        nom_rec = lista[idx_rec]["nombre"]
        if game["nave"][det_cat] != idx_rec:
            txt(f"Recomendado: {nom_rec}", font_s, (90, 230, 120), (35, 505))

    txt("Ficha técnica:", font_s, (255, 255, 0), (35, 480))
    for k, l in enumerate(wrap(detalle(actual), font_s, 395)[:3]):
        txt(l, font_s, (200, 220, 255), (35, 500 + k * 17))

    r = evaluar(game["mision"])
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
        filas.append(
            ("Ciencia", rat(r["ciencia"], r["cmin"]), f"{r['ciencia']}/{r['cmin']}", r["ciencia"] >= r["cmin"]))
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
        for k, l in enumerate(wrap(fallos[0][0] + ": " + fallos[0][2], font_s, 315)[:3]):
            txt(l, font_s, (255, 200, 170), (X, 344 + k * 19))
        button((X, 400, 150, 30), "Sugerir arreglo", "sugerir", enabled=bool(fallos))

    button((35, 532, 390, 36), "Ver y elegir cohete (3 modelos)", "ver_cohetes")
    button((445, 515, 200, 44), "Revisar vuelo", "evaluar", enabled=mis is not None)
    button((655, 515, 105, 44), "Cerrar", "cerrar")


def draw_panel_cohete():
    ventana("ELIGE TU COHETE", (20, 15, 760, 570))
    actual = game["nave"]["lanz"]
    mis = MISIONES[game["mision"]] if game["mision"] is not None else None

    if mis and "lanz" in mis["recomendados"]:
        idx_rec = mis["recomendados"]["lanz"]
        nom_rec = LANZADORES[idx_rec]["nombre"]
        txt(f"Para esta misión se recomienda: {nom_rec}", font, (90, 230, 120), (400, 65), center=True)

    for i, l in enumerate(LANZADORES):
        x = 40 + i * 245
        carta = pygame.Rect(x, 76, 230, 454)
        elegido = (i == actual)
        hover = carta.collidepoint(mouse_ui)
        es_rec = mis and "lanz" in mis["recomendados"] and mis["recomendados"]["lanz"] == i
        color_borde = (90, 230, 120) if es_rec else (
            (90, 230, 120) if elegido else ((255, 255, 0) if hover else (0, 130, 180)))

        pygame.draw.rect(ui, (20, 40, 80) if (hover or elegido) else (18, 28, 62), carta, border_radius=8)
        pygame.draw.rect(ui, color_borde, carta, 3 if elegido else 2, border_radius=8)

        if es_rec:
            txt("★ RECOMENDADO", font_s, (90, 230, 120), (carta.centerx, 260), center=True)

        img = COHETES_TARJETA[i]
        ui.blit(img, (carta.centerx - img.get_width() // 2, 86 + (175 - img.get_height()) // 2))
        txt(l["nombre"], font, (255, 255, 0), (carta.centerx, 276), center=True)
        txt(f"{l['empresa']}  |  {l['altura']} m de alto", font_s, (200, 220, 255), (carta.centerx, 298), center=True)
        for k, linea in enumerate(wrap(l["simple"], font_s, 208)[:3]):
            txt(linea, font_s, (170, 190, 215), (carta.x + 12, 318 + k * 19))
        for k, linea in enumerate(wrap(l["info"], font_s, 208)[:4]):
            txt(linea, font_s, (130, 150, 180), (carta.x + 12, 380 + k * 17))
        txt(f"Cupo: {l['cap']:g} kg   Costo: ${l['costo']}M", font_s, (255, 255, 255), (carta.centerx, 462),
            center=True)
        button((carta.x + 15, 482, 200, 36), "Elegido" if elegido else "Elegir este cohete", ("cohete", i),
               selected=elegido)
    button((325, 540, 150, 36), "Volver", "atras")


def draw_informe():
    r = evaluar(game["mision"])
    mis = r["mis"]
    ventana("REVISIÓN FINAL DEL COHETE", (20, 15, 760, 570))
    exito = r["ok"]
    txt(mis["nombre"] + " - " + FORMATOS_CUBESAT[game["nave"]["formato"]]["nombre"], font, (255, 255, 255), (40, 82))
    txt("LISTO PARA VOLAR" if exito else "NO APTO PARA VOLAR", font_title, (90, 230, 120) if exito else (255, 90, 90),
        (480, 78))
    txt("Lista de revisión", font_s, (255, 255, 0), (40, 118))
    for i, (nombre, ok, _) in enumerate(r["checks"]):
        txt(("[OK] " if ok else "[X]  ") + nombre, font_s, (90, 230, 120) if ok else (255, 100, 100),
            (40, 142 + i * 26))
    txt("Resultado", font_s, (255, 255, 0), (420, 118))
    y = 142
    fallos = [c for c in r["checks"] if not c[1]]
    if exito:
        lineas = wrap("¡Felicidades! Tu cohete cumple con todos los requisitos para esta misión.", font_s, 330)
        for l in lineas:
            txt(l, font_s, (170, 220, 190), (420, y))
            y += 20
    else:
        for nombre, _, causa in fallos:
            for l in wrap("- " + causa, font_s, 335):
                if y < 430:
                    txt(l, font_s, (255, 200, 170), (420, y))
                y += 19
            y += 5
    if exito:
        sobra = r["pres"] - r["costo"]
        pts = puntaje(r)
        txt(f"Puntuación: {pts} puntos", font_title, (255, 255, 0), (40, 440))
        txt(f"Ciencia {r['ciencia']}  |  Sobra ${sobra}M  |  Peso libre {round(r['cap'] - r['masa'], 2)} kg", font_s,
            (200, 220, 255), (40, 478))
    else:
        txt(f"Puntuación parcial: {sum(1 for c in r['checks'] if c[1]) * 30}", font_title, (255, 150, 90), (40, 440))
        txt("Usa el botón 'Sugerir arreglo' en el Hangar.", font_s, (200, 220, 255), (40, 478))
    if exito:
        button((40, 515, 390, 44), "¡DESPEGAR!", "despegar")
    button((450, 515, 190, 44), "Volver al hangar", "taller")
    button((655, 515, 105, 44), "Cerrar", "cerrar")


def draw_glosario():
    ventana("GLOSARIO - ¿QUÉ SIGNIFICA?", (40, 30, 720, 540))
    for i, (palabra, definicion) in enumerate(GLOSARIO_TEXTO):
        y = 100 + i * 50
        txt(palabra + ":", font, (255, 255, 0), (70, y))
        for k, l in enumerate(wrap(definicion, font_s, 560)[:2]):
            txt(l, font_s, (200, 220, 255), (70, y + 22 + k * 18))
    button((320, 520, 160, 36), "Cerrar", "cerrar_glosario")


# ======================================================================
#  ACCIONES
# ======================================================================
def iniciar(continuar):
    global estado, luna_activa
    keys_down.clear()
    luna_activa = False
    game["mision"], game["nave"], game["dinero"] = None, nave_default(), 0
    player.x, player.y = player_start
    luna_guardada = None
    if continuar:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                p = json.load(f)["partida"]
            player.x, player.y = p["x"], p["y"]
            game["mision"] = p["mision"]
            game["dinero"] = int(p.get("dinero", 0))
            luna_guardada = p.get("luna")
            for _, clave, lista in CATEGORIAS:
                v = int(p["nave"].get(clave, 0))
                game["nave"][clave] = max(0, min(v, len(lista) - 1))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    # Si había una misión lunar en curso, se continúa ahí (no se puede volver a la estación sin completarla)
    if luna_guardada and game["mision"] is not None and iniciar_luna(luna_guardada):
        return
    estado = ESTACION


def on_click(ident):
    global estado, running, sel_m, aviso, det_cat
    if isinstance(ident, tuple):
        if ident[0] == "mision":
            sel_m, aviso = ident[1], ""
        elif ident[0] == "cohete":
            game["nave"]["lanz"] = ident[1]
            det_cat = "lanz"
            guardar()
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
    elif ident == "despegar":
        iniciar_despegue()
    elif ident == "taller" or ident == "atras":
        estado = PANEL_NAVE
    elif ident == "ver_cohetes":
        estado = PANEL_COHETE
    elif ident == "sugerir":
        sugerir_arreglo()
    elif ident == "cerrar_glosario":
        estado = ESTACION if game["mision"] is None else PANEL_NAVE
    elif ident == "cerrar":
        if estado == PANEL_COHETE:
            estado = PANEL_NAVE
        elif estado == GLOSARIO:
            estado = ESTACION
        else:
            estado = ESTACION
        aviso = ""


def iniciar_despegue():
    """Arranca la animación SOLO si todos los componentes son correctos."""
    global estado, anim
    if game["mision"] is None:
        return
    r = evaluar(game["mision"])
    if not r["ok"]:
        return
    n = game["nave"]
    anim = Despegue(screen, os.path.join(BASE_DIR, "images"), n["lanz"], n["orbita"],
                    ORBITAS[n["orbita"]]["nombre"], MISIONES[game["mision"]]["nombre"],
                    LANZADORES[n["lanz"]]["nombre"], puntaje(r))
    keys_down.clear()
    estado = DESPEGUE


def pulsar_despegue():
    """Primer toque: salta al final de la animación. Después pasa a VIAJE EN PROGRESO."""
    global anim
    if anim is not None and not anim.terminado:
        anim.saltar()
    else:
        iniciar_viaje()


def sugerir_arreglo():
    """Aplica TODOS los componentes recomendados de golpe."""
    global aviso
    if game["mision"] is None:
        return
    mis = MISIONES[game["mision"]]

    # Aplicar todos los componentes ideales
    for clave, idx in mis["recomendados"].items():
        game["nave"][clave] = idx

    aviso = "¡He colocado los componentes ideales para esta misión!"
    guardar()


# ----------------------------------------------------------------------
#  VIAJE EN PROGRESO  ->  PANTALLA NEGRA  ->  ESCENA LUNAR
# ----------------------------------------------------------------------
def regresar_estacion():
    global estado
    keys_down.clear()
    player.x, player.y = player_start
    estado = ESTACION


def iniciar_viaje():
    global estado, anim, viaje_t0
    anim = None
    keys_down.clear()
    viaje_t0 = pygame.time.get_ticks()
    estado = VIAJE


def saltar_viaje():
    """Salta el texto y pasa directo a la pantalla negra."""
    global viaje_t0
    limite = pygame.time.get_ticks() - int(T_TEXTO * 1000)
    if viaje_t0 > limite:
        viaje_t0 = limite


def txt_screen(s, f, color, pos):
    img = f.render(s, True, color)
    screen.blit(img, img.get_rect(center=pos))


def draw_viaje():
    t = (pygame.time.get_ticks() - viaje_t0) / 1000.0
    if t >= T_TEXTO + T_FADE + T_NEGRO:
        screen.fill((0, 0, 0))
        if not iniciar_luna():
            regresar_estacion()
        return

    screen.fill((5, 5, 15))
    for x0, y0, vel, tam in ESTRELLAS:
        x = int(((x0 - t * vel) % 1.0) * SCREEN_W)
        pygame.draw.rect(screen, (200, 200, 255), (x, int(y0 * SCREEN_H), tam, tam))

    n = game["nave"]
    mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "-"
    cx = SCREEN_W // 2
    txt_screen("VIAJE EN PROGRESO", font_big, (0, 255, 255), (cx, int(SCREEN_H * 0.30)))
    txt_screen("Misión: " + mision, font_title, (255, 255, 0), (cx, int(SCREEN_H * 0.42)))
    txt_screen("Cohete: " + LANZADORES[n["lanz"]]["nombre"], font_title, (255, 255, 255), (cx, int(SCREEN_H * 0.49)))
    txt_screen("Destino: " + ORBITAS[n["orbita"]]["nombre"], font_title, (255, 255, 255), (cx, int(SCREEN_H * 0.56)))

    # barra de progreso del viaje
    bw, bh = 500, 16
    bx, by = cx - bw // 2, int(SCREEN_H * 0.66)
    pygame.draw.rect(screen, (40, 45, 70), (bx, by, bw, bh), border_radius=6)
    pygame.draw.rect(screen, (0, 200, 255), (bx, by, int(bw * min(1.0, t / T_TEXTO)), bh), border_radius=6)
    txt_screen("Click o ESPACIO para continuar", font_s, (150, 150, 170), (cx, by + 40))

    if t > T_TEXTO:
        negro.set_alpha(int(255 * min(1.0, (t - T_TEXTO) / T_FADE)))
        screen.blit(negro, (0, 0))


def es_llama(c):
    r, g, b, a = c
    return a > 40 and r > 190 and b < 110 and r > g + 25


def sin_llama(img):
    """Quita la llama del motor (parte de abajo del cohete vertical) para que no se vea encendida."""
    w, h = img.get_size()
    y = h - 1
    while y >= 0:
        opacos = llama = 0
        for x in range(0, w, 2):
            c = img.get_at((x, y))
            if c[3] > 40:
                opacos += 1
                if es_llama(c):
                    llama += 1
        if opacos == 0 or llama / opacos >= 0.5:
            y -= 1
        else:
            break
    if y + 1 < h * 0.5 or y + 1 >= h:
        return img  # no había llama (o la detección falló): se deja igual
    return img.subsurface((0, 0, w, y + 1)).copy()


def cargar_imagen(nombre, color):
    """Carga un PNG de /images recortado a su contenido. Si no existe, devuelve un cuadro de color."""
    try:
        img = pygame.image.load(os.path.join(BASE_DIR, "images", nombre)).convert_alpha()
        caja = img.get_bounding_rect()
        if caja.width > 0 and caja.height > 0:
            img = img.subsurface(caja).copy()
        return img
    except (pygame.error, FileNotFoundError, OSError):
        print("No se encontró", nombre, "en la carpeta images")
        img = pygame.Surface((80, 120), pygame.SRCALPHA)
        img.fill(color)
        return img


def cargar_robots(alto_px):
    """Devuelve (robot roto, robot reparado) escalados con el mismo factor."""
    roto = cargar_imagen(ROBOT_ROTO, (200, 80, 80, 255))
    ok = cargar_imagen(ROBOT_REPARADO, (80, 200, 120, 255))
    factor = alto_px / roto.get_height()
    return escalar(roto, factor), escalar(ok, factor)


def cargar_astro_win(size):
    """astroWIN.png ajustado al tamaño del sprite normal del astronauta (None si no existe)."""
    try:
        img = pygame.image.load(os.path.join(BASE_DIR, "images", ASTRO_WIN)).convert_alpha()
    except (pygame.error, FileNotFoundError, OSError):
        print("No se encontró", ASTRO_WIN, "en la carpeta images")
        return None
    ancho, alto = size
    img = escalar(img, min(ancho / img.get_width(), alto / img.get_height()))
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.blit(img, img.get_rect(midbottom=(ancho // 2, alto)))
    return surf


def generar_items(w, h, evitar, guardado=None):
    """Crea los 3 objetos en posiciones aleatorias del suelo (o en las posiciones guardadas)."""
    pos = {d["id"]: d for d in (guardado or [])}
    ocupados = list(evitar)
    items = []
    for oid, archivo, nombre, color in OBJETOS:
        img = cargar_imagen(archivo, color)
        img = escalar(img, int(h * ITEM_ALTO) / img.get_height())
        iw, ih = img.get_size()
        r = pygame.Rect(0, 0, iw, ih)
        d = pos.get(oid)
        if d:
            r.topleft = (d["x"], d["y"])
        else:
            # Zona de aparición: el suelo del mapa (ajustable cuando se definan las colisiones finales)
            for _ in range(600):
                r.topleft = (random.randint(int(w * 0.06), int(w * 0.94) - iw),
                             random.randint(int(h * 0.60), int(h * 0.93) - ih))
                if not any(r.inflate(80, 80).colliderect(o) for o in ocupados):
                    break
        ocupados.append(r.inflate(300, 200))  # separa los objetos entre sí
        items.append({"id": oid, "nombre": nombre, "img": img, "rect": r, "ok": bool(d and d.get("ok"))})
    return items


def cargar_luna(restaurar=None):
    """Carga mapa, cohete, robot, objetos y personaje. 'restaurar' = datos guardados de una misión en curso."""
    global luna_map, luna_cohete, luna_cohete_llama, luna_cohete_pos, COHETES_HORIZ, COHETES_HORIZ_LL
    global robot_roto, robot_ok, robot_rect, robot_zona, robot_reparado, reparar_t0, reparado_t
    global luna_items, nave_rect, nave_zona, astro_win
    n = game["nave"]
    archivo = DESTINO_FONDO.get(n["orbita"])
    if archivo is None:
        return False
    ruta = os.path.join(BASE_DIR, "images", archivo)
    try:
        w, h = pygame.image.load(ruta).get_size()
    except (pygame.error, FileNotFoundError, OSError) as e:
        print("No se pudo cargar el mapa lunar:", e)
        return False

    # Robot al fondo derecho
    robot_roto, robot_ok = cargar_robots(int(h * ROBOT_ALTO))
    rrw, rrh = robot_roto.get_size()
    robot_rect = pygame.Rect(int(w * ROBOT_X) - rrw // 2, int(h * ROBOT_BASE_Y) - rrh, rrw, rrh)
    robot_zona = robot_rect.inflate(220, 180)
    robot_reparado, reparar_t0, reparado_t = False, None, 0

    g = max(4, w // 100)
    # COLISIONES PROVISIONALES: bordes, cielo/montañas (el suelo empieza ~54% de la altura) y el robot
    luna_solidos = [
        (0, 0, w, g), (0, h - g, w, g), (0, 0, g, h), (w - g, 0, g, h),
        (0, 0, w, int(h * 0.54)),
        (robot_rect.x, robot_rect.bottom - int(rrh * 0.4), rrw, int(rrh * 0.4)),
    ]
    try:
        luna_map = ImageMap(ruta, luna_solidos)
    except (pygame.error, FileNotFoundError, OSError) as e:
        print("No se pudo cargar el mapa lunar:", e)
        return False

    # Cohetes acostados (nariz a la derecha):
    #   COHETES_HORIZ    -> sprite SIN estela (el cohete elegido, ya estacionado en el planeta)
    #   COHETES_HORIZ_LL -> sprite CON estela (mientras vuela hacia el planeta y en el regreso)
    if COHETES_HORIZ is None:
        COHETES_HORIZ = [pygame.transform.rotate(cargar_cohete_sin_estela(i), -90)
                         for i in range(len(COHETES_IMG))]
        COHETES_HORIZ_LL = [pygame.transform.rotate(i, -90) for i in COHETES_IMG]
    mw = max(i.get_width() for i in COHETES_HORIZ)
    mh = max(i.get_height() for i in COHETES_HORIZ)
    factor = min(LUNA_LARGO * w / mw, LUNA_GROSOR * h / mh)
    luna_cohete = escalar(COHETES_HORIZ[n["lanz"]], factor)
    luna_cohete_llama = escalar(COHETES_HORIZ_LL[n["lanz"]], factor)
    rw, rh = luna_cohete.get_size()
    cx, cy = int(w * LUNA_CX), int(h * LUNA_CY)
    luna_cohete_pos = (cx - rw // 2, cy - rh // 2)
    nave_rect = pygame.Rect(luna_cohete_pos, (rw, rh))
    nave_zona = nave_rect.inflate(160, 160)

    # El personaje aparece enfrente (a la derecha) de la nariz del cohete
    pw, ph = player.image.get_size()
    player.x = cx + rw // 2 + 45
    player.y = cy - ph // 2 + 30
    spawn = pygame.Rect(int(player.x), int(player.y), pw, ph)
    astro_win = cargar_astro_win((pw, ph))

    # Objetos aleatorios (evitando colisiones, cohete, robot y el punto de aparición)
    evitar = [pygame.Rect(*sol) for sol in luna_solidos] + [nave_zona, robot_zona, spawn.inflate(160, 160)]
    luna_items = generar_items(w, h, evitar, restaurar.get("items") if restaurar else None)

    if restaurar:
        robot_reparado = bool(restaurar.get("reparado"))
        player.x = restaurar.get("px", player.x)
        player.y = restaurar.get("py", player.y)
    return True


def iniciar_luna(restaurar=None):
    global estado, luna_t0, luna_fase, luna_activa
    if not cargar_luna(restaurar):
        return False
    keys_down.clear()
    player.reposo()
    luna_activa = True
    if restaurar:
        luna_fase = "listo"  # el cohete ya está estacionado: sin animación de llegada
        luna_t0 = pygame.time.get_ticks() - int((LUNA_DEMORA + LUNA_LLEGADA + 2) * 1000)
    else:
        luna_fase = "bajando"
        luna_t0 = pygame.time.get_ticks()
    estado = LUNA
    return True


def luna_guardado():
    """Datos de la misión lunar en curso para guardarlos (None si no hay)."""
    if not luna_activa:
        return None
    return {"items": [{"id": it["id"], "x": it["rect"].x, "y": it["rect"].y, "ok": it["ok"]} for it in luna_items],
            "reparado": robot_reparado, "px": player.x, "py": player.y}


def salir_luna_al_menu():
    """ESC en la misión: guarda el avance y va al menú principal (no se vuelve a la estación)."""
    global estado
    guardar()
    keys_down.clear()
    estado = MENU


def interactuar_luna():
    """Tecla E (pulsación): recoger un objeto cercano o subir a la nave si el robot ya está reparado."""
    if luna_fase != "listo":
        return
    prect = player.rect()
    for it in luna_items:
        if not it["ok"] and prect.colliderect(it["rect"].inflate(90, 90)):
            it["ok"] = True
            return
    if robot_reparado and prect.colliderect(nave_zona):
        iniciar_regreso()


def iniciar_regreso():
    global luna_fase, fin_t0, reparar_t0
    keys_down.clear()
    player.reposo()
    reparar_t0 = None
    luna_fase = "celebrando"
    fin_t0 = pygame.time.get_ticks()


def completar_mision():
    """Termina la misión: bonificación, limpia la misión y muestra el menú MISIÓN EXITOSA."""
    global estado, luna_activa, ultima_mision
    ultima_mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "-"
    game["dinero"] += BONIFICACION
    game["mision"] = None
    luna_activa = False
    player.x, player.y = player_start
    keys_down.clear()
    guardar()
    estado = MISION_OK


def update_luna():
    global luna_fase, reparar_t0, robot_reparado, reparado_t, fin_t0
    ahora = pygame.time.get_ticks()
    t = (ahora - luna_t0) / 1000.0

    # Fuera de la fase de caminar, el astronauta se ve en su sprite normal
    if luna_fase != "listo":
        player.reposo()

    if luna_fase == "bajando":
        if t >= LUNA_DEMORA + LUNA_LLEGADA:
            luna_fase = "listo"
        return

    if luna_fase == "listo":
        cerca_robot = player.rect().colliderect(robot_zona)
        todos = all(it["ok"] for it in luna_items)
        if cerca_robot and todos and pygame.K_e in keys_down and not robot_reparado:
            # Manteniendo E junto al robot: el astronauta se queda quieto mientras repara
            player.reposo()
            if reparar_t0 is None:
                reparar_t0 = ahora
            if (ahora - reparar_t0) / 1000.0 >= T_REPARAR:
                robot_reparado = True
                reparado_t = ahora
                reparar_t0 = None
        else:
            reparar_t0 = None
            player.update(luna_map)
        return

    # Secuencia final: celebrar -> subir a la nave -> volar a la Tierra
    tf = (ahora - fin_t0) / 1000.0
    if luna_fase == "celebrando" and tf >= T_CELEBRAR:
        luna_fase, fin_t0 = "subiendo", ahora
    elif luna_fase == "subiendo" and tf >= T_SUBIR:
        luna_fase, fin_t0 = "regreso", ahora
    elif luna_fase == "regreso" and tf >= T_REGRESO:
        completar_mision()


def caja_texto(msg, color, midbottom=None, midtop=None):
    img = font.render(msg, True, color)
    box = pygame.Rect(0, 0, img.get_width() + 40, 44)
    if midbottom:
        box.midbottom = midbottom
    else:
        box.midtop = midtop
    pygame.draw.rect(screen, (0, 0, 0), box, border_radius=8)
    pygame.draw.rect(screen, color, box, 2, border_radius=8)
    screen.blit(img, img.get_rect(center=box.center))


def hud_objetivo():
    """Mensaje arriba a la derecha: cuántos objetos llevas, o REGRESO A CASA."""
    if robot_reparado:
        lineas = [("REGRESO A CASA", (90, 230, 120))]
    else:
        n_ok = sum(1 for it in luna_items if it["ok"])
        lineas = [(f"Objetos para reparar: {n_ok}/{len(luna_items)}", (255, 255, 0))]
        for it in luna_items:
            lineas.append((("[OK] " if it["ok"] else "[  ] ") + it["nombre"],
                           (90, 230, 120) if it["ok"] else (200, 200, 200)))
    ancho = max(font.size(l)[0] for l, _ in lineas) + 28
    caja = pygame.Rect(SCREEN_W - ancho - 10, 10, ancho, 12 + 24 * len(lineas))
    pygame.draw.rect(screen, (0, 0, 0), caja, border_radius=6)
    pygame.draw.rect(screen, lineas[0][1], caja, 2, border_radius=6)
    for i, (l, c) in enumerate(lineas):
        screen.blit(font.render(l, True, c), (caja.x + 14, caja.y + 8 + i * 24))


def draw_luna():
    global luna_view
    ahora = pygame.time.get_ticks()
    t = (ahora - luna_t0) / 1000.0
    zoom = max(SCREEN_W / luna_map.width, SCREEN_H / luna_map.height) * cfg["zoom_extra"]
    vw, vh = int(SCREEN_W / zoom), int(SCREEN_H / zoom)
    if luna_view is None or luna_view.get_size() != (vw, vh):
        luna_view = pygame.Surface((vw, vh))

    cam_x = clamp_camera(int(player.x) + player.image.get_width() // 2 - vw // 2, vw, luna_map.width)
    cam_y = clamp_camera(int(player.y) + player.image.get_height() // 2 - vh // 2, vh, luna_map.height)
    camera = (cam_x, cam_y)

    luna_view.fill((0, 0, 0))
    luna_map.draw(luna_view, camera)

    # ---- Cohete ----
    rx_final, ry = luna_cohete_pos
    rw, rh = luna_cohete.get_size()
    if luna_fase == "regreso":
        # Vuelo de regreso: despega con llama hacia la Tierra, achicándose
        tt = (ahora - fin_t0) / 1000.0
        e = min(1.0, tt / T_REGRESO) ** 2
        sx, sy = nave_rect.center
        tx, ty = luna_map.width * TIERRA_X, luna_map.height * TIERRA_Y
        bx, by = sx + (tx - sx) * e, sy + (ty - sy) * e
        ang = math.degrees(math.atan2(sy - ty, tx - sx))
        esc = 1.0 - 0.9 * e
        d = (luna_cohete_llama.get_width() - rw) / 2 * esc
        img = pygame.transform.rotozoom(luna_cohete_llama, ang, esc)
        cxp = bx - d * math.cos(math.radians(ang)) - cam_x
        cyp = by + d * math.sin(math.radians(ang)) - cam_y
        luna_view.blit(img, img.get_rect(center=(int(cxp), int(cyp))))
    else:
        if luna_fase == "bajando":
            p = max(0.0, min(1.0, (t - LUNA_DEMORA) / LUNA_LLEGADA))
            e = 1 - (1 - p) ** 3
            rx_ini = cam_x - rw - 30
            rx = int(rx_ini + (rx_final - rx_ini) * e)
            # Volando hacia el planeta: sprite CON estela, alineado por la nariz con el sprite final
            lw, lh = luna_cohete_llama.get_size()
            luna_view.blit(luna_cohete_llama,
                           (rx + rw - lw - cam_x, ry + (rh - lh) // 2 - cam_y))
        else:
            # Ya llegó al planeta: sprite SIN estela del cohete que eligió el jugador
            luna_view.blit(luna_cohete, (rx_final - cam_x, ry - cam_y))

    # ---- Objetos, robot y personaje ----
    robot_img = robot_ok if robot_reparado else robot_roto
    rr = robot_img.get_rect(midbottom=robot_rect.midbottom)

    def pintar_robot():
        luna_view.blit(robot_img, (rr.x - cam_x, rr.y - cam_y))

    def pintar_items():
        prect = player.rect()
        for it in luna_items:
            if it["ok"]:
                continue
            r = it["rect"]
            luna_view.blit(it["img"], (r.x - cam_x, r.y - cam_y))
            if luna_fase == "listo" and prect.colliderect(r.inflate(90, 90)):
                pygame.draw.rect(luna_view, (255, 255, 0), r.move(-cam_x, -cam_y).inflate(8, 8), 2)

    def pintar_player():
        if luna_fase == "celebrando":
            tt = (ahora - fin_t0) / 1000.0
            usar_win = astro_win is not None and int(tt / T_PARPADEO) % 2 == 1
            luna_view.blit(astro_win if usar_win else player.image,
                           (int(player.x) - cam_x, int(player.y) - cam_y))
        elif luna_fase == "subiendo":
            p = min(1.0, (ahora - fin_t0) / 1000.0 / T_SUBIR)
            tx = nave_rect.centerx - player.image.get_width() // 2
            ty = nave_rect.centery - player.image.get_height() // 2
            img = player.image.copy()
            img.set_alpha(int(255 * (1 - p)))
            luna_view.blit(img, (int(player.x + (tx - player.x) * p) - cam_x,
                                 int(player.y + (ty - player.y) * p) - cam_y))
        else:
            for s in sprites:
                s.draw(luna_view, camera)

    if luna_fase == "bajando":
        pintar_robot()
    elif luna_fase == "regreso":
        pintar_items()
        pintar_robot()
    else:
        pintar_items()
        if player.y + player.image.get_height() < robot_rect.bottom:
            pintar_player()
            pintar_robot()
        else:
            pintar_robot()
            pintar_player()
        if pygame.K_F1 in keys_down:
            luna_map.draw_debug(luna_view, camera)

    screen.blit(pygame.transform.smoothscale(luna_view, (SCREEN_W, SCREEN_H)), (0, 0))

    # ---- HUD ----
    mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "-"
    extra = "Llegando a la Luna..." if luna_fase == "bajando" else "WASD: caminar   E: interactuar"
    info = font.render(f"Misión: {mision}   |   {extra}   |   ESC: menú", True, (255, 255, 255))
    pygame.draw.rect(screen, (0, 0, 0), (10, 10, info.get_width() + 20, 32), border_radius=4)
    screen.blit(info, (20, 17))
    if luna_fase != "bajando":
        hud_objetivo()

    # ---- Avisos de interacción ----
    if luna_fase == "listo":
        prect = player.rect()
        todos = all(it["ok"] for it in luna_items)
        n_ok = sum(1 for it in luna_items if it["ok"])
        base = (SCREEN_W // 2, SCREEN_H - 40)
        item_cerca = next((it for it in luna_items
                           if not it["ok"] and prect.colliderect(it["rect"].inflate(90, 90))), None)
        if item_cerca:
            caja_texto(f"[E]  Recoger {item_cerca['nombre']}", (255, 255, 0), midbottom=base)
        elif reparar_t0 is not None:
            prog = min(1.0, (ahora - reparar_t0) / 1000.0 / T_REPARAR)
            bw = 360
            box = pygame.Rect(0, 0, bw + 40, 74)
            box.midbottom = base
            pygame.draw.rect(screen, (0, 0, 0), box, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 0), box, 2, border_radius=8)
            img = font.render(f"Reparando robot...  {int(prog * 100)}%", True, (255, 255, 0))
            screen.blit(img, img.get_rect(midtop=(box.centerx, box.y + 10)))
            pygame.draw.rect(screen, (40, 45, 70), (box.x + 20, box.y + 44, bw, 16), border_radius=6)
            pygame.draw.rect(screen, (90, 230, 120), (box.x + 20, box.y + 44, int(bw * prog), 16), border_radius=6)
        elif not robot_reparado and prect.colliderect(robot_zona):
            if todos:
                caja_texto(f"Mantén [E] {T_REPARAR:g} segundos para reparar el robot", (255, 255, 0), midbottom=base)
            else:
                caja_texto(f"Te faltan objetos para repararlo ({n_ok}/{len(luna_items)})", (255, 170, 90),
                           midbottom=base)
        elif robot_reparado and prect.colliderect(nave_zona):
            caja_texto("[E]  Volver a la Tierra", (90, 230, 120), midbottom=base)
        if robot_reparado and ahora - reparado_t < 4000:
            caja_texto("¡Robot reparado! Regresa a la nave", (90, 230, 120), midtop=(SCREEN_W // 2, 60))

    # ---- Fundidos: entrada desde negro / salida hacia la Tierra ----
    alpha = max(0, 255 - int(255 * t / 1.0))
    if luna_fase == "regreso":
        resto = T_REGRESO - (ahora - fin_t0) / 1000.0
        if resto < 1.0:
            alpha = int(255 * (1 - max(0.0, resto)))
    if alpha > 0:
        negro.set_alpha(alpha)
        screen.blit(negro, (0, 0))


def draw_mision_ok():
    t = pygame.time.get_ticks() / 1000.0
    screen.fill((5, 5, 15))
    for x0, y0, vel, tam in ESTRELLAS:
        x = int(((x0 - t * vel) % 1.0) * SCREEN_W)
        pygame.draw.rect(screen, (200, 200, 255), (x, int(y0 * SCREEN_H), tam, tam))
    ventana("RESULTADO DE LA MISIÓN", (100, 70, 600, 460))
    txt("MISIÓN EXITOSA", font_big, (90, 230, 120), (UI_W // 2, 160), center=True)
    txt(ultima_mision, font_title, (255, 255, 255), (UI_W // 2, 220), center=True)
    txt("Repetidor lunar reparado. ¡Regresaste a la Tierra!", font, (200, 220, 255), (UI_W // 2, 255), center=True)
    txt("BONIFICACIÓN ECONÓMICA", font, (255, 255, 0), (UI_W // 2, 315), center=True)
    txt(f"+${BONIFICACION}M", font_big, (255, 255, 0), (UI_W // 2, 360), center=True)
    txt(f"Fondos totales: ${game['dinero']}M", font_title, (255, 255, 255), (UI_W // 2, 420), center=True)
    button((300, 458, 200, 50), "Volver a la estación", "cerrar")


# ======================================================================
#  BUCLE PRINCIPAL
# ======================================================================
running = True

while running:
    if estado == MENU:
        MARGEN_DER = 60
        # El bloque de botones va de x=250 a x=550 dentro del lienzo
        OFF_X = SCREEN_W - 650 - MARGEN_DER
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
            if estado == DESPEGUE:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    pulsar_despegue()
            elif estado == VIAJE:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    saltar_viaje()
            elif estado == LUNA:
                if event.key == pygame.K_ESCAPE:
                    salir_luna_al_menu()
                elif event.key == pygame.K_e:
                    interactuar_luna()
            elif event.key == pygame.K_ESCAPE:
                if estado == MENU:
                    running = False
                elif estado == OPCIONES:
                    on_click("volver")
                elif estado == ESTACION:
                    guardar()
                    estado = MENU
                elif estado == GLOSARIO:
                    on_click("cerrar_glosario")
                else:
                    on_click("cerrar")
            elif event.key == pygame.K_h and estado in (ESTACION, PANEL_NAVE, PANEL_MISION):
                estado = GLOSARIO
            elif event.key == pygame.K_e and estado == ESTACION and cerca:
                estado = INTERACTIVOS[cerca][3]
                if estado == PANEL_MISION and game["mision"] is not None:
                    sel_m = game["mision"]
                keys_down.clear()
                player.reposo()
        elif event.type == pygame.KEYUP:
            keys_down.discard(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = (event.pos[0] - OFF_X, event.pos[1] - OFF_Y)
            if estado == DESPEGUE:
                pulsar_despegue()
            elif estado == VIAJE:
                saltar_viaje()
            else:
                for rect, ident in list(clickables):
                    if rect.collidepoint(pos):
                        on_click(ident)
                        break

    # Fuera de la estación y la Luna el astronauta siempre se ve en su sprite normal
    if estado not in (ESTACION, LUNA):
        player.reposo()

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
    elif estado == DESPEGUE:
        anim.update()
        if anim.terminado:
            iniciar_viaje()  # en vez del mensaje de "misión completada"
        else:
            anim.draw()
    elif estado == VIAJE:
        draw_viaje()
    elif estado == LUNA:
        update_luna()
        draw_luna()
    elif estado == MISION_OK:
        draw_mision_ok()
    else:
        draw_world()
        if estado in (PANEL_MISION, PANEL_NAVE, PANEL_INFORME, PANEL_COHETE, GLOSARIO):
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            paneles = {
                PANEL_MISION: draw_panel_mision,
                PANEL_NAVE: draw_panel_nave,
                PANEL_INFORME: draw_informe,
                PANEL_COHETE: draw_panel_cohete,
                GLOSARIO: draw_glosario,
            }
            paneles[estado]()

    screen.blit(ui, (OFF_X, OFF_Y))
    pygame.display.flip()
    clock.tick(60)

menu_bg.release()
guardar(solo_opciones=True)
pygame.quit()
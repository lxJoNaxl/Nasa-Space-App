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
from dron import DronMarte
from final import FinalEpico
import sonido

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
font_xs = pygame.font.SysFont(None, 17)

BG = (15, 15, 30)
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.json")
menu_bg = FondoMenu("planeta rotando.mp4", (SCREEN_W, SCREEN_H), BG)

# Estados
(MENU, OPCIONES, ESTACION, PANEL_MISION, PANEL_NAVE, PANEL_INFORME,
 PANEL_COHETE, GLOSARIO, DESPEGUE, VIAJE, LUNA, MISION_OK, PANEL_TIENDA, PANEL_SIMULA, FINAL) = range(15)
anim = None  # animación de despegue activa
final = None  # cinemática final (al completar la última misión)
final_sonando = False  # Final.wav suena en bucle desde la cinemática hasta volver a la base
estado = MENU

# ----------------------------------------------------------------------
#  VIAJE Y ESCENA LUNAR
# ----------------------------------------------------------------------
DESTINO_FONDO = {3: "FondoEspacio.png", 4: "Escena_Marte.jpeg"}  # índice de ORBITAS -> imagen del mapa (en /images)
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

# Escena de Marte (índice 4 de ORBITAS). Las imágenes van en /images
MARTE_ORBITA = 4
DRON_PNG = "dron.png"
MARTE_CX = 0.12  # centro horizontal del cohete en Marte
MARTE_CY = 0.76  # centro vertical del cohete en Marte (sobre el suelo)

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

# Dinero: PNG arriba a la derecha con el total ganado encima (solo en el mapa de la estación)
DINERO_PNG = "dinero.png"
DINERO_ALTO = 80  # alto del sprite en pantalla (px)
_dinero_img = None

# Objetos que hay que recoger para reparar el robot: (id, archivo en /images, nombre, color si falta el PNG)
OBJETOS = [
    ("antena", "ANTENA.png", "Antena", (230, 200, 60, 255)),
    ("placa", "PLACA.png", "Placa", (60, 200, 120, 255)),
    ("bateria", "BATERIA.png", "Batería", (80, 160, 255, 255)),
]
ITEM_ALTO = 0.06  # alto de cada objeto (fracción del alto del mapa)

# Qué hace cada pieza del repetidor lunar (se muestra al acercarte a recogerla): id -> (apodo, descripción)
OBJETOS_DESC = {
    "bateria": ("La energía",
                "Es la «pila» gigante del repetidor. Sin ella, el aparato está apagado y no tiene electricidad "
                "para encender sus luces ni funcionar."),
    "placa": ("El cerebro",
              "Es una tarjeta verde con chips que funciona como la «mente» del repetidor. Se encarga de recibir "
              "los mensajes de los astronautas y traducirlos para que no se pierdan."),
    "antena": ("La voz",
               "Es el plato que apunta hacia el espacio. Sirve para lanzar la señal con mucha fuerza hacia arriba "
               "y lograr que el mensaje viaje miles de kilómetros hasta llegar a la Tierra."),
}

# Final de la misión
ASTRO_WIN = "astroWIN.png"
N_PARPADEOS = 5  # veces que alterna entre el sprite normal y astroWIN
T_PARPADEO = 0.25  # segundos por cada cambio de sprite
T_CELEBRAR = N_PARPADEOS * 2 * T_PARPADEO
T_SUBIR = 1.2  # segundos que tarda en subir a la nave
T_REGRESO = 6.0  # segundos del vuelo de regreso a la Tierra
TIERRA_X, TIERRA_Y = 0.63, 0.095  # dónde está la Tierra en el mapa lunar (fracción)
DINERO_INICIAL = 600  # millones de $ con los que empiezas (alcanza para armar la nave de la misión 1)

viaje_t0 = 0
luna_t0 = 0
luna_map = None
luna_view = None
luna_cohete = None
luna_cohete_pos = (0, 0)
luna_fase = "bajando"
dron = None  # DronMarte (solo en la misión a Marte)
es_marte = False
COHETES_HORIZ = None  # cohetes SIN estela y acostados (se calculan una vez)
robot_roto = robot_ok = None
robot_rect = pygame.Rect(0, 0, 1, 1)
robot_zona = pygame.Rect(0, 0, 1, 1)
robot_reparado = False
reparar_t0 = None
reparado_t = 0
COHETES_HORIZ_LL = None  # cohetes acostados CON estela (llegada al planeta y vuelo de regreso)
luna_cohete_llama = None
luna_items = []
nave_rect = pygame.Rect(0, 0, 1, 1)
nave_zona = pygame.Rect(0, 0, 1, 1)
astro_win = None
fin_t0 = 0
luna_activa = False  # hay una misión lunar en curso (se guarda para "Continuar")
ultima_mision = "-"
ultimo_exito = ""
ultima_recompensa = 0
ultimo_desbloqueo = []
ultimo_reporte = None  # reporte científico de la última misión
ok_pagina = 0  # 0 = resultado, 1 = reporte científico
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
    P("Nave Pequeña", "Caja pequeña. Límite: 1.33 kg.", "Para misiones ligeras y cerca de casa.", vol=1.0, masa_chasis=0.35,
      cap_max=1.33, costo=15),
    P("Nave Mediana", "Caja mediana. Límite: 4 kg.", "Equilibrada, pero justa de peso.", vol=3.0, masa_chasis=0.95,
      cap_max=4.00, costo=35),
    P("Nave Grande", "Caja grande. Límite: 12 kg.", "Cabe todo el equipo para la Luna y Marte.", vol=6.0, masa_chasis=1.80, cap_max=12.00,
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
      empresa="Rocket Lab", altura=18, alcance=1),
    P("Cohete Falcon 9", "Tamaño medio.", "Llega a la Luna.", cap=30.0, costo=140, img="COHETE_NIVEL2.png",
      empresa="SpaceX", altura=70, alcance=3),
    P("Cohete Falcon Heavy", "El más potente.", "El único que llega a Marte.", cap=50.0, costo=330,
      img="COHETE_NIVEL3.png", empresa="SpaceX", altura=70, alcance=4),
]

MOTORES = [
    P("Sin motor", "No se mueve.", "No sirve para viajar.", dv=0, masa=0.0, pot=0.0, costo=0),
    P("Motor Químico", "Fuerza media.", "Sirve para cerca de la Tierra.", dv=450, masa=0.45, pot=2.5, costo=35),
    P("Motor Iónico", "Fuerza extrema.", "Obligatorio para Luna y Marte.", dv=3500, masa=1.30, pot=10.0, costo=95),
]

ENERGIAS = [
    P("Paneles Pequeños", "Poca energía.", "Suficiente para la Tierra.", gen=6.0, masa=0.18, costo=15),
    P("Paneles Medianos", "Energía media.", "Para naves de poco consumo.", gen=18.0, masa=0.45, costo=40),
    P("Paneles Grandes", "Máxima energía.", "Necesarios con motor iónico (Luna y Marte).", gen=42.0, masa=0.90, costo=85),
]

COMMS = [
    P("Antena Lenta", "Poca señal.", "Para cerca de la Tierra.", enlace=10, masa=0.12, pot=1.5, costo=15),
    P("Antena Media", "Señal media.", "Para la Luna.", enlace=60, masa=0.30, pot=5.0, costo=40),
    P("Antena Rápida", "Señal potente.", "La necesitas para Marte.", enlace=250, masa=0.65, pot=12.0, costo=80),
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
    P("Blindaje Grueso", "Protección máxima.", "Lo necesitas para Marte.", prot=50, masa=1.10, costo=85),
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
    {"nombre": "Explorador Lunar", "tipo": "Reparación lunar", "destino": "Luna", "dificultad": "Fácil",
     "presupuesto": 600, "recompensa": 500, "requiere": None,
     "orbitas": [3], "tags": ["espectro", "radar", "particulas"], "prot": 30, "cmin": 70,
     "historia": "El repetidor que conecta la Luna con la Tierra (el «router» de internet lunar) dejó de funcionar. Viaja hasta allá, recoge 3 piezas y repáralo.",
     "pasos": ["Compra las piezas en la TIENDA.",
               "Ármalas en el HANGAR (la nave grande).",
               "Pulsa «Revisar vuelo» y despega.",
               "En la Luna: recoge 3 piezas y repara el robot."],
     "dato": "La Luna está a unos 384 000 km de la Tierra. Una señal de radio tarda solo 1,3 segundos en llegar.",
     "mision_real": "Parecida a CAPSTONE, de la NASA.",
     "exito": "Repetidor lunar reparado. ¡Regresaste a la Tierra!",
     "recomendados": {"formato": 2, "seguridad": 1, "orbita": 3, "lanz": 1, "motor": 2, "energia": 2,
                      "comm": 1, "instr": 2, "blind": 1},
     "desc": "Reparar un repetidor en la Luna."},
    {"nombre": "Explorador de Marte", "tipo": "Exploración de Marte", "destino": "Marte", "dificultad": "Difícil",
     "presupuesto": 900, "recompensa": 1000, "requiere": 0,
     "orbitas": [4], "tags": ["espectro", "ir", "radar"], "prot": 45, "cmin": 80,
     "historia": "Marte está muchísimo más lejos que la Luna. Tu nave viajará hasta el planeta rojo para analizar su suelo con sus instrumentos.",
     "pasos": ["Revisa qué piezas reutilizas de la misión anterior.",
               "Compra en la TIENDA las piezas más potentes.",
               "Ármalas en el HANGAR y revisa el vuelo.",
               "Despega y llega a Marte."],
     "dato": "Marte está entre 55 y 400 millones de km de la Tierra. Una señal tarda de 3 a 22 minutos en llegar.",
     "mision_real": "Parecida a MarCO, de la NASA.",
     "exito": "¡Tu nave llegó a Marte y ya estudia su suelo! Los datos viajan hacia la Tierra.",
     "recomendados": {"formato": 2, "seguridad": 1, "orbita": 4, "lanz": 2, "motor": 2, "energia": 2,
                      "comm": 2, "instr": 2, "blind": 2},
     "desc": "Viaje interplanetario."},
]

ALTURA_MIN, ALTURA_MAX = 40, 140  # límites del tamaño del personaje (px) en Opciones
cfg = {"zoom_extra": 1.0, "velocidad": 3, "altura_jugador": player_mod.PLAYER_HEIGHT}


def nave_default():
    return {c[1]: 0 for c in CATEGORIAS}


LISTA_DE = {c[1]: c[2] for c in CATEGORIAS}
NOMBRE_CAT = {c[1]: c[0] for c in CATEGORIAS}
COMPRABLES = [c for c in CATEGORIAS if c[1] != "orbita"]  # el destino no se compra

CAT_AYUDA = {
    "formato": "La caja donde va todo el equipo. Más grande = cabe más peso, pero cuesta más.",
    "seguridad": "Interruptores y cables que evitan que algo se encienda antes de tiempo. Sin ellos no se puede lanzar.",
    "orbita": "El lugar al que quieres llegar. Se ajusta solo al aceptar la misión.",
    "lanz": "El cohete gigante que te saca de la Tierra. Cuanto más lejos quieras ir, más potente debe ser.",
    "motor": "Es lo que te empuja por el espacio. Para llegar a la Luna o a Marte necesitas el motor iónico.",
    "energia": "Los paneles solares dan electricidad a todos los aparatos. Si no alcanza, la nave se apaga.",
    "comm": "La antena envía los datos a la Tierra. Más rápida = más información enviada cada día.",
    "instr": "Es lo que usa tu nave para estudiar: cámaras, radares y sensores. Cada misión pide uno distinto.",
    "blind": "Un escudo contra la radiación del espacio. Cuanto más lejos de la Tierra, más grueso debe ser.",
}

# A qué categoría(s) corresponde cada punto de la revisión (para marcar en rojo lo que falla)
CHECK_CAT = {
    "Peso permitido": ("formato",), "Alcance del cohete": ("lanz",), "Seguridad de vuelo": ("seguridad",),
    "Energía suficiente": ("energia",), "Antena adecuada": ("comm",), "Movilidad (motor)": ("motor",),
    "Protección": ("blind",), "Destino correcto": ("orbita",), "Instrumento correcto": ("instr",),
    "Ciencia mínima": ("instr",),
}


def inventario_inicial():
    """Piezas con las que empiezas: la más básica de cada tipo y todo lo que cuesta $0."""
    inv = {}
    for _, clave, lista in COMPRABLES:
        inv[clave] = {0} | {i for i, c in enumerate(lista) if c.get("costo", 0) == 0}
    return inv


INICIALES = inventario_inicial()

game = {"mision": None, "nave": nave_default(), "dinero": DINERO_INICIAL,
        "inventario": inventario_inicial(), "completadas": []}
player_start = (600, 450)


def tiene(clave, idx):
    return clave == "orbita" or idx in game["inventario"].get(clave, ())


def mision_estado(i):
    if i in game["completadas"]:
        return "completada"
    req = MISIONES[i]["requiere"]
    if req is not None and req not in game["completadas"]:
        return "bloqueada"
    return "disponible"


def piezas_faltantes(idx_mision):
    """Piezas recomendadas para la misión que todavía no compraste: [(clave, idx)]"""
    mis = MISIONES[idx_mision]
    out = []
    for _, clave, _lista in COMPRABLES:
        idx = mis["recomendados"].get(clave)
        if idx is not None and not tiene(clave, idx):
            out.append((clave, idx))
    return out


GLOSARIO_TEXTO = [
    ("Misión", "El trabajo que tiene que cumplir tu nave. Se hacen en orden: primero la Luna, luego Marte."),
    ("Fondos", "Tu dinero, en millones de dólares. Se gasta en la TIENDA y se gana al terminar misiones."),
    ("Peso", "Si tu nave pesa más de lo permitido, no despega."),
    ("Energía", "Electricidad para los aparatos. La dan los paneles solares."),
    ("Antena", "Sirve para enviar los datos a la Tierra."),
    ("Motor", "La fuerza para viajar por el espacio. El iónico llega más lejos."),
    ("Lanzador", "El cohete gigante que te saca de la Tierra. Más lejos = más potente."),
    ("Protección", "Escudo contra la radiación del espacio."),
    ("Órbita", "El camino que sigue algo alrededor de un planeta. Es tu destino."),
    ("Ciencia", "Puntos por los descubrimientos que hace tu instrumento."),
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
    if "alcance" in c:
        partes.append("llega hasta: " + ORBITAS[c["alcance"]]["nombre"])
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
    chk.append(("Alcance del cohete", n["orbita"] <= lan["alcance"],
                "Este cohete no llega tan lejos. Necesitas poner: un cohete más potente."))
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
            ("Destino correcto", n["orbita"] in mis["orbitas"], "El destino no es el correcto para esta misión."))
        chk.append(("Instrumento correcto", tag_ok, "El instrumento no sirve para esta misión. Cambia el Instrumento."))
        chk.append(
            ("Ciencia mínima", r["ciencia"] >= mis["cmin"], "El instrumento no da suficiente ciencia. Usa uno mejor."))

    r["checks"] = chk
    r["ok"] = all(c[1] for c in chk)
    return r


def puntaje(r):
    ahorro = max(0.0, 1 - r["costo"] / r["pres"]) if r["pres"] else 0.0
    return int(300 + r["ciencia"] * 4 + ahorro * 300 + max(0.0, 1 - r["masa"] / r["cap"]) * 200)


def inicio_jugador():
    """Punto de inicio del astronauta (con los pies en el mismo lugar sea cual sea su tamaño)."""
    return player.convertir_pos(player_start[0], player_start[1], player_mod.PLAYER_HEIGHT)


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
        ix, iy = inicio_jugador()
        data["partida"] = {"x": player.x if en_estacion else ix,
                           "y": player.y if en_estacion else iy,
                           "altura_jugador": player.altura,
                           "mision": game["mision"], "nave": game["nave"],
                           "dinero": game["dinero"], "luna": luna_guardado(),
                           "inventario": {k: sorted(v) for k, v in game["inventario"].items()},
                           "completadas": game["completadas"],
                           "jugador": game.get("jugador", "")}
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


def ruta_imagen(nombre):
    """Ruta de una imagen dentro de /images. Si el nombre exacto no existe, busca uno parecido
    (sin importar mayúsculas, espacios, guiones bajos ni la extensión: .jpg/.jpeg/.png)."""
    carpeta = os.path.join(BASE_DIR, "images")
    ruta = os.path.join(carpeta, nombre)
    if os.path.exists(ruta):
        return ruta

    def norm(s):
        return os.path.splitext(s)[0].lower().replace(" ", "").replace("_", "").replace("-", "")

    try:
        for f in os.listdir(carpeta):
            if norm(f) == norm(nombre) and f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
                print("Se usa", f, "en lugar de", nombre)
                return os.path.join(carpeta, f)
    except OSError:
        pass
    print("No se encontró", nombre, "en", carpeta)
    return ruta


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
OBJ_TIENDA = pygame.Rect(2020, 725, 290, 115)  # la mesa del fondo a la derecha del hangar
INTERACTIVOS = {
    "nave": (OBJ_NAVE, OBJ_NAVE.inflate(160, 160), "Armar tu cohete", PANEL_NAVE),
    "pc": (OBJ_PC, OBJ_PC.inflate(140, 140), "Elegir misión", PANEL_MISION),
    "tienda": (OBJ_TIENDA, OBJ_TIENDA.inflate(140, 140), "Abrir la tienda", PANEL_TIENDA),
}
ETIQUETAS = {"nave": "HANGAR", "pc": "MISIONES", "tienda": "TIENDA"}
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
cfg["altura_jugador"] = max(ALTURA_MIN, min(ALTURA_MAX, int(cfg.get("altura_jugador", player_mod.PLAYER_HEIGHT))))
apply_zoom()
player_mod.movement_speed = cfg["velocidad"]
player.set_altura(cfg["altura_jugador"])

# ======================================================================
#  INTERFAZ
# ======================================================================
clickables = []
mouse_ui = (0, 0)
SLIDER = pygame.Rect(440, 400, 220, 10)  # barra del tamaño del personaje (coordenadas de la interfaz)
arrastrando_tamano = False
aviso = ""
sel_m = 0
det_cat = "formato"  # categoría abierta en el hangar
tienda_cat = "formato"  # categoría abierta en la tienda
glosario_volver = ESTACION  # a dónde se vuelve al cerrar el glosario
toast_msg, toast_t0, toast_color = "", 0, (255, 255, 0)  # aviso temporal arriba a la derecha


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


def button(rect, label, ident, enabled=True, selected=False, peligro=False):
    r = pygame.Rect(rect)
    hover = enabled and r.collidepoint(mouse_ui)
    if not enabled:
        bg, border, fg = (45, 45, 55), (90, 90, 100), (120, 120, 130)
    elif peligro:
        bg = (170, 40, 40) if hover else (120, 25, 25)
        border = (255, 220, 120) if hover else (255, 110, 90)
        fg = (255, 255, 255)
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
    # Tamaño del personaje: vista previa + barra deslizante
    txt("Tamaño del personaje", font, (255, 255, 255), (170, 395))
    pygame.draw.rect(ui, (40, 45, 70), SLIDER, border_radius=4)
    frac = (cfg["altura_jugador"] - ALTURA_MIN) / (ALTURA_MAX - ALTURA_MIN)
    hx = SLIDER.x + int(SLIDER.w * frac)
    pygame.draw.rect(ui, (0, 200, 255), (SLIDER.x, SLIDER.y, hx - SLIDER.x, SLIDER.h), border_radius=4)
    hover = SLIDER.inflate(30, 34).collidepoint(mouse_ui) or arrastrando_tamano
    pygame.draw.circle(ui, (255, 255, 0) if hover else (255, 255, 255), (hx, SLIDER.centery), 11)
    pygame.draw.circle(ui, (0, 90, 200), (hx, SLIDER.centery), 11, 2)
    txt(f"{cfg['altura_jugador']} px", font, (255, 255, 0), (SLIDER.right + 50, SLIDER.centery), center=True)
    caja = pygame.Rect(30, 205, 120, 205)
    pygame.draw.rect(ui, (14, 22, 55), caja, border_radius=8)
    pygame.draw.rect(ui, (0, 200, 255), caja, 2, border_radius=8)
    suelo_y = caja.bottom - 18
    pygame.draw.line(ui, (90, 100, 140), (caja.x + 10, suelo_y), (caja.right - 10, suelo_y), 2)
    ui.blit(player.image_der, player.image_der.get_rect(midbottom=(caja.centerx, suelo_y)))
    txt("Vista previa", font_xs, (200, 220, 255), (caja.centerx, caja.y + 12), center=True)
    button((250, 510, 300, 50), "Volver", "volver")


def fijar_altura(x_ui):
    """Mueve la barra de tamaño según la posición del mouse; el cambio se ve al instante."""
    f = max(0.0, min(1.0, (x_ui - SLIDER.x) / SLIDER.w))
    v = ALTURA_MIN + round(f * (ALTURA_MAX - ALTURA_MIN))
    if v != cfg["altura_jugador"]:
        cfg["altura_jugador"] = v
        player.set_altura(v)


def draw_dinero():
    """PNG del dinero arriba a la derecha, con el total ganado en las misiones encima (solo en la estación)."""
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
    for s in sprites:
        s.draw(view, camera)
    if pygame.K_F1 in keys_down:
        station_map.draw_debug(view, camera)
    screen.blit(pygame.transform.smoothscale(view, (SCREEN_W, SCREEN_H)), (0, 0))
    draw_etiquetas(cam_x, cam_y)

    mision = MISIONES[game["mision"]]["nombre"] if game["mision"] is not None else "ninguna"
    info = font.render(
        f"Misión: {mision}   |   Mover: WASD o flechas   |   E: usar   |   H: Glosario   |   ESC: Menú",
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

    if estado == ESTACION:
        draw_objetivo()


# ----------------------------------------------------------------------
#  Utilidades de dibujo (formas hechas con pygame.draw, sin depender de símbolos de la fuente)
# ----------------------------------------------------------------------
def estrella(surf, cx, cy, r, color):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, color, pts)


def candado(surf, cx, cy, color):
    pygame.draw.rect(surf, color, (cx - 8, cy - 2, 16, 12), border_radius=3)
    pygame.draw.arc(surf, color, pygame.Rect(cx - 5, cy - 11, 10, 14), 0, math.pi, 3)


def marca(surf, cx, cy, ok):
    """Círculo con check (ok), X (mal) o guion (sin dato)."""
    if ok is None:
        pygame.draw.circle(surf, (90, 95, 115), (cx, cy), 9)
        pygame.draw.line(surf, (200, 200, 210), (cx - 4, cy), (cx + 4, cy), 2)
    elif ok:
        pygame.draw.circle(surf, (60, 190, 100), (cx, cy), 9)
        pygame.draw.lines(surf, (255, 255, 255), False, [(cx - 4, cy), (cx - 1, cy + 4), (cx + 5, cy - 4)], 2)
    else:
        pygame.draw.circle(surf, (230, 80, 80), (cx, cy), 9)
        pygame.draw.line(surf, (255, 255, 255), (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
        pygame.draw.line(surf, (255, 255, 255), (cx + 4, cy - 4), (cx - 4, cy + 4), 2)


def chip(texto, x, y, bg, fg=(255, 255, 255), f=None, derecha=False):
    f = f or font_s
    img = f.render(texto, True, fg)
    w, h = img.get_width() + 16, img.get_height() + 6
    r = pygame.Rect(x - w if derecha else x, y, w, h)
    pygame.draw.rect(ui, bg, r, border_radius=h // 2)
    ui.blit(img, (r.x + 8, r.y + 3))
    return r


def recortar(s_, f, ancho):
    if f.size(s_)[0] <= ancho:
        return s_
    while s_ and f.size(s_ + "...")[0] > ancho:
        s_ = s_[:-1]
    return s_ + "..."


def chips_flow(items, x, y, ancho):
    """Dibuja etiquetas una tras otra, saltando de línea. items = [(texto, fondo, color_texto)]. Devuelve la y final."""
    cx, cy = x, y
    for texto, bg, fg in items:
        w = font_s.size(texto)[0] + 16
        if cx + w > x + ancho and cx > x:
            cx, cy = x, cy + 26
        r = pygame.Rect(cx, cy, w, 22)
        pygame.draw.rect(ui, bg, r, border_radius=11)
        txt(texto, font_s, fg, r.center, center=True)
        cx += w + 6
    return cy + 26


def barra_lectura(x, y, ancho, etiqueta, texto, ratio, ok):
    txt(etiqueta, font_s, (200, 200, 200), (x, y))
    img = font_s.render(texto, True, (255, 255, 255))
    ui.blit(img, (x + ancho - img.get_width(), y))
    pygame.draw.rect(ui, (40, 45, 70), (x, y + 16, ancho, 8), border_radius=4)
    color = (90, 220, 120) if ok else (255, 150, 90)
    pygame.draw.rect(ui, color, (x, y + 16, int(ancho * max(0.03, min(1.0, ratio))), 8), border_radius=4)


def problemas_por_cat(r):
    """(problemas, relacionadas): problemas[clave] = lista de causas; relacionadas = categorías con alguna revisión."""
    prob, rel = {}, set()
    for nombre, ok, causa in r["checks"]:
        for clave in CHECK_CAT.get(nombre, ()):
            rel.add(clave)
            if not ok:
                prob.setdefault(clave, []).append(causa)
    return prob, rel


def stats_simples(c):
    partes = [ETQ[k].format(v) for k, v in c.items() if k in ETQ and k != "costo"]
    if "alcance" in c:
        partes.append("llega hasta " + ORBITAS[c["alcance"]]["nombre"])
    return ", ".join(partes)


# ----------------------------------------------------------------------
#  Avisos, etiquetas y objetivo (ayudas para quien no conoce de misiones espaciales)
# ----------------------------------------------------------------------
def toast(msg, color=(255, 255, 0)):
    global toast_msg, toast_t0, toast_color
    toast_msg, toast_t0, toast_color = msg, pygame.time.get_ticks(), color


def draw_toast():
    if not toast_msg or estado in (MENU, OPCIONES, DESPEGUE, VIAJE, LUNA, FINAL):
        return
    if pygame.time.get_ticks() - toast_t0 > 4500:
        return
    lineas = wrap(toast_msg, font, 420)[:3]
    ancho = max(font.size(l)[0] for l in lineas) + 28
    # Va debajo del dinero (esquina superior derecha) para no taparlo
    caja = pygame.Rect(SCREEN_W - ancho - 10, DINERO_ALTO + 20, ancho, 14 + 22 * len(lineas))
    pygame.draw.rect(screen, (0, 0, 0), caja, border_radius=8)
    pygame.draw.rect(screen, toast_color, caja, 2, border_radius=8)
    for k, l in enumerate(lineas):
        screen.blit(font.render(l, True, toast_color), (caja.x + 14, caja.y + 8 + k * 22))


def objetivo_actual():
    if game["mision"] is None:
        if len(game["completadas"]) >= len(MISIONES):
            return "¡Completaste todas las misiones! Eres un ingeniero espacial."
        return "Objetivo: ve a la computadora (a la izquierda) y elige tu misión."
    if evaluar(game["mision"])["ok"]:
        return "Objetivo: tu cohete está listo. Ve al HANGAR, pulsa «Revisar vuelo» y despega."
    if piezas_faltantes(game["mision"]):
        return "Objetivo: compra las piezas que te faltan en la TIENDA (la mesa del fondo a la derecha)."
    return "Objetivo: arma tu cohete en el HANGAR (la nave grande). Usa «Sugerir piezas» si no sabes cómo."


def draw_objetivo():
    img = font.render(objetivo_actual(), True, (255, 255, 255))
    caja = pygame.Rect(10, 50, img.get_width() + 28, 32)
    pygame.draw.rect(screen, (0, 60, 110), caja, border_radius=6)
    screen.blit(img, (caja.x + 14, caja.y + 7))


def draw_etiquetas(cam_x, cam_y):
    """Rótulo flotante sobre cada lugar interactivo (sin recuadros ni líneas)."""
    for clave, (obj, _z, _t, _e) in INTERACTIVOS.items():
        sx = int((obj.centerx - cam_x) * SCREEN_W / VIEW_W)
        sy = int((obj.top - cam_y) * SCREEN_H / VIEW_H) - 14
        if not (0 <= sx <= SCREEN_W and 20 <= sy <= SCREEN_H):
            continue
        img = font_s.render(ETIQUETAS[clave], True, (255, 255, 0) if cerca == clave else (255, 255, 255))
        w, h = img.get_width() + 20, img.get_height() + 8
        caja = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(caja, (0, 0, 0, 170), (0, 0, w, h), border_radius=h // 2)
        screen.blit(caja, (sx - w // 2, sy - h // 2))
        screen.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2))


# ----------------------------------------------------------------------
#  Compra y venta
# ----------------------------------------------------------------------
def comprar(clave, idx):
    c = LISTA_DE[clave][idx]
    if tiene(clave, idx):
        return
    if game["dinero"] < c["costo"]:
        toast("No te alcanza el dinero para esta pieza.", (255, 120, 90))
        return
    game["dinero"] -= c["costo"]
    game["inventario"][clave].add(idx)
    sonido.tocar(sonido.COMPRA)
    toast(f"Compraste «{c['nombre']}». Ya puedes usarla en el HANGAR.", (90, 230, 120))
    guardar()


def vender(clave, idx):
    c = LISTA_DE[clave][idx]
    if idx in INICIALES[clave] or idx not in game["inventario"][clave]:
        return
    game["inventario"][clave].discard(idx)
    game["dinero"] += c["costo"]
    if game["nave"][clave] == idx:
        game["nave"][clave] = 0
    sonido.tocar(sonido.COMPRA)
    toast(f"Vendiste «{c['nombre']}» y recuperaste ${c['costo']}M.", (255, 220, 120))
    guardar()


# ----------------------------------------------------------------------
#  PANEL: ELEGIR MISIÓN
# ----------------------------------------------------------------------
def draw_panel_mision():
    ventana("ELEGIR MISIÓN", (30, 20, 740, 560))
    txt(f"Las misiones se juegan en orden. Completadas: {len(game['completadas'])} de {len(MISIONES)}",
        font_s, (170, 200, 230), (50, 84))

    # --- tarjetas de misión ---
    for i, m in enumerate(MISIONES):
        est = mision_estado(i)
        bloq = est == "bloqueada"
        r = pygame.Rect(50, 108 + i * 108, 255, 98)
        elegida = (i == sel_m)
        hover = r.collidepoint(mouse_ui)
        bg = (30, 60, 120) if elegida else ((24, 40, 90) if hover else (18, 28, 62))
        borde = (255, 255, 0) if elegida else ((90, 90, 100) if bloq else (0, 130, 180))
        pygame.draw.rect(ui, bg, r, border_radius=8)
        pygame.draw.rect(ui, borde, r, 3 if elegida else 2, border_radius=8)
        txt(f"MISIÓN {i + 1}", font_s, (150, 170, 200), (r.x + 12, r.y + 8))
        txt(m["nombre"], font, (130, 130, 140) if bloq else (255, 255, 0), (r.x + 12, r.y + 26))
        txt("Destino: " + m["destino"], font_s, (200, 220, 255), (r.x + 12, r.y + 52))
        if est == "completada":
            chip("COMPLETADA", r.x + 12, r.y + 70, (20, 110, 60))
        elif bloq:
            chip("BLOQUEADA", r.x + 12, r.y + 70, (70, 70, 80), (200, 200, 200))
            candado(ui, r.right - 30, r.y + 36, (150, 150, 160))
        elif game["mision"] == i:
            chip("EN CURSO", r.x + 12, r.y + 70, (150, 110, 0))
        else:
            chip("DISPONIBLE", r.x + 12, r.y + 70, (0, 90, 160))
        clickables.append((r, ("mision", i)))

    # --- camino Tierra -> Luna -> Marte ---
    txt("Tu camino", font_s, (150, 170, 200), (50, 326))
    nodos = ["Tierra"] + [m["destino"] for m in MISIONES]
    x0, x1, yc = 75, 280, 358
    pygame.draw.line(ui, (60, 80, 130), (x0, yc), (x1, yc), 3)
    for k, nom in enumerate(nodos):
        cx = x0 + (x1 - x0) * k // (len(nodos) - 1)
        if k == 0:
            col = (90, 200, 255)
        else:
            e = mision_estado(k - 1)
            col = (90, 220, 120) if e == "completada" else ((255, 255, 0) if e == "disponible" else (110, 110, 120))
        pygame.draw.circle(ui, col, (cx, yc), 9)
        txt(nom, font_s, (200, 220, 255), (cx, yc + 22), center=True)

    # --- fondos ---
    caja = pygame.Rect(50, 405, 255, 130)
    pygame.draw.rect(ui, (20, 30, 70), caja, border_radius=8)
    pygame.draw.rect(ui, (0, 130, 180), caja, 2, border_radius=8)
    txt("Tus fondos", font_s, (170, 200, 230), (caja.x + 12, caja.y + 10))
    txt(f"${game['dinero']}M", font_title, (255, 255, 0), (caja.x + 12, caja.y + 28))
    for k, l in enumerate(wrap("Se gastan en la TIENDA. Si compras algo que no necesitas, puedes venderlo.",
                               font_s, 230)[:3]):
        txt(l, font_s, (170, 200, 230), (caja.x + 12, caja.y + 66 + k * 18))

    # --- detalle de la misión elegida ---
    m = MISIONES[sel_m]
    est = mision_estado(sel_m)
    x, anch = 330, 420
    txt(m["nombre"], font_title, (255, 255, 0), (x, 104))
    c1 = chip("Dificultad: " + m["dificultad"], x, 140, (0, 90, 160))
    chip(f"Recompensa: ${m['recompensa']}M", c1.right + 8, 140, (20, 110, 60))
    y = 172
    txt("De qué trata", font_s, (255, 255, 0), (x, y))
    y += 18
    for l in wrap(m["historia"], font_s, anch)[:4]:
        txt(l, font_s, (200, 220, 255), (x, y))
        y += 19
    y += 6
    txt("Qué harás", font_s, (255, 255, 0), (x, y))
    y += 20
    for n, paso in enumerate(m["pasos"], 1):
        pygame.draw.circle(ui, (0, 130, 180), (x + 8, y + 7), 8)
        txt(str(n), font_xs, (255, 255, 255), (x + 8, y + 7), center=True)
        for l in wrap(paso, font_s, anch - 26)[:2]:
            txt(l, font_s, (200, 220, 255), (x + 24, y))
            y += 18
        y += 3
    y += 4
    txt("Piezas necesarias (verde = ya la tienes)", font_s, (255, 255, 0), (x, y))
    y += 20
    items = []
    for _, clave, lista in COMPRABLES:
        idx = m["recomendados"].get(clave)
        if idx is None:
            continue
        ok = tiene(clave, idx)
        items.append((lista[idx]["nombre"], (25, 110, 70) if ok else (130, 80, 20),
                      (255, 255, 255) if ok else (255, 225, 170)))
    y = chips_flow(items, x, y, anch) + 4
    if est == "bloqueada":
        aviso_txt = f"Completa «{MISIONES[m['requiere']]['nombre']}» para desbloquear esta misión."
        for l in wrap(aviso_txt, font_s, anch)[:2]:
            txt(l, font_s, (255, 170, 90), (x, y))
            y += 19
    else:
        for l in wrap("Dato curioso: " + m["dato"], font_s, anch)[:2]:
            txt(l, font_s, (150, 220, 255), (x, y))
            y += 19
        txt(m["mision_real"], font_xs, (150, 150, 170), (x, y))

    # --- botones ---
    if est == "completada":
        button((x, 522, 250, 42), "Misión completada", "nada", enabled=False)
    elif est == "bloqueada":
        button((x, 522, 250, 42), "Bloqueada", "nada", enabled=False)
    else:
        button((x, 522, 250, 42), "Aceptar misión" if game["mision"] != sel_m else "Seguir con esta misión", "aceptar")
    button((600, 522, 150, 42), "Cerrar", "cerrar")


# ----------------------------------------------------------------------
#  PANEL: HANGAR (armar la nave con las piezas que tienes)
# ----------------------------------------------------------------------
def draw_panel_nave():
    ventana("HANGAR - ARMA TU COHETE", (10, 10, 780, 580))
    mis = MISIONES[game["mision"]] if game["mision"] is not None else None
    r = evaluar(game["mision"])
    prob, rel = problemas_por_cat(r)

    # --- misión actual ---
    caja = pygame.Rect(25, 70, 235, 40)
    pygame.draw.rect(ui, (20, 30, 70), caja, border_radius=6)
    pygame.draw.rect(ui, (0, 130, 180), caja, 1, border_radius=6)
    if mis:
        txt("Tu misión", font_xs, (150, 170, 200), (caja.x + 10, caja.y + 4))
        txt(mis["nombre"], font_s, (255, 255, 0), (caja.x + 10, caja.y + 19))
    else:
        txt("Todavía sin misión", font_s, (255, 150, 90), (caja.x + 10, caja.y + 4))
        txt("Elígela en la computadora", font_xs, (200, 200, 200), (caja.x + 10, caja.y + 22))

    # --- lista de categorías ---
    for i, (nombre, clave, lista) in enumerate(CATEGORIAS):
        fila = pygame.Rect(25, 116 + i * 40, 235, 36)
        sel = (det_cat == clave)
        hover = fila.collidepoint(mouse_ui)
        pygame.draw.rect(ui, (30, 60, 120) if sel else ((24, 40, 90) if hover else (18, 28, 62)), fila, border_radius=6)
        pygame.draw.rect(ui, (255, 255, 0) if sel else (0, 130, 180), fila, 2 if sel else 1, border_radius=6)
        txt(nombre, font_xs, (170, 190, 220), (fila.x + 10, fila.y + 3))
        actual = lista[game["nave"][clave]]
        txt(recortar(actual["nombre"], font_s, 170), font_s, (255, 255, 0), (fila.x + 10, fila.y + 17))
        if prob.get(clave):
            marca(ui, fila.right - 20, fila.centery, False)
        elif clave in rel:
            marca(ui, fila.right - 20, fila.centery, True)
        else:
            marca(ui, fila.right - 20, fila.centery, None)
        clickables.append((fila, ("cat", clave)))

    # --- lecturas rápidas (peso, energía, requisitos) ---
    ok_n = sum(1 for c in r["checks"] if c[1])
    barra_lectura(25, 484, 235, "Peso", f"{r['masa']} / {r['cap']} kg", r["masa"] / r["cap"], r["masa"] <= r["cap"])
    barra_lectura(25, 514, 235, "Energía", f"{r['consumo']} / {r['gen']} W",
                  r["consumo"] / r["gen"] if r["gen"] else 1.0, r["gen"] >= r["consumo"])
    barra_lectura(25, 544, 235, "Requisitos cumplidos", f"{ok_n} / {len(r['checks'])}", ok_n / len(r["checks"]),
                  ok_n == len(r["checks"]))

    # --- cabecera de la categoría abierta ---
    lista = LISTA_DE[det_cat]
    txt(NOMBRE_CAT[det_cat], font_title, (255, 255, 0), (270, 72))
    ancho_ayuda = 360 if det_cat == "lanz" else 500
    for k, l in enumerate(wrap(CAT_AYUDA[det_cat], font_s, ancho_ayuda)[:2]):
        txt(l, font_s, (190, 210, 235), (270, 106 + k * 18))
    if det_cat == "lanz":
        button((645, 74, 130, 30), "Ver con fotos", "ver_cohetes")

    # --- opciones ---
    rec_idx = mis["recomendados"].get(det_cat) if mis else None
    puesto = game["nave"][det_cat]
    hover_i = None
    for i, c in enumerate(lista):
        card = pygame.Rect(270, 146 + i * 50, 505, 44)
        hover = card.collidepoint(mouse_ui)
        if hover:
            hover_i = i
        propio = tiene(det_cat, i)
        en_uso = (i == puesto)
        bg = (20, 70, 60) if en_uso else ((24, 40, 90) if hover else (18, 28, 62))
        borde = (90, 230, 120) if en_uso else ((255, 255, 0) if hover else (0, 130, 180))
        pygame.draw.rect(ui, bg, card, border_radius=6)
        pygame.draw.rect(ui, borde, card, 2, border_radius=6)
        if rec_idx == i:
            estrella(ui, card.x + 16, card.centery, 8, (255, 220, 0))
        txt(c["nombre"], font, (255, 255, 255) if propio else (140, 140, 150), (card.x + 34, card.y + 4))
        txt(recortar(c["simple"], font_s, 330), font_s, (170, 200, 230) if propio else (120, 130, 150),
            (card.x + 34, card.y + 25))
        if en_uso:
            chip("EN USO", card.right - 12, card.y + 11, (20, 130, 70), derecha=True)
        elif propio:
            clickables.append((card, ("equipar", det_cat, i)))
            button((card.right - 110, card.y + 6, 100, 32), "Usar", ("equipar", det_cat, i))
        else:
            clickables.append((card, ("bloqueada", det_cat, i)))
            candado(ui, card.right - 128, card.centery, (150, 150, 160))
            txt(f"Tienda ${c['costo']}M", font_s, (170, 170, 180), (card.right - 112, card.centery - 7))
    if rec_idx is not None:
        estrella(ui, 478, 85, 7, (255, 220, 0))
        txt("= recomendada", font_xs, (255, 220, 120), (490, 79))

    # --- ficha técnica y diagnóstico de la pieza ---
    c_info = lista[hover_i if hover_i is not None else puesto]
    txt("Ficha técnica", font_xs, (255, 255, 0), (270, 452))
    for k, l in enumerate(wrap(detalle(c_info), font_s, 500)[:2]):
        txt(l, font_s, (200, 220, 255), (270, 466 + k * 17))
    causas = prob.get(det_cat, [])
    if causas:
        lineas, col = wrap("Problema: " + causas[0], font_s, 500)[:2], (255, 140, 110)
    elif det_cat in rel:
        lineas, col = ["Esta pieza cumple lo que pide tu misión."], (90, 230, 120)
    else:
        lineas, col = ["Elige una misión en la computadora para saber si esta pieza sirve."], (170, 170, 180)
    for k, l in enumerate(lineas):
        txt(l, font_s, col, (270, 506 + k * 17))

    # --- botones ---
    button((270, 542, 110, 34), "Sugerir", "sugerir", enabled=mis is not None)
    button((386, 542, 140, 34), "¿Qué pasa si…?", "simula", enabled=mis is not None)
    button((532, 542, 130, 34), "Revisar vuelo", "evaluar", enabled=mis is not None)
    button((668, 542, 107, 34), "Cerrar", "cerrar")


# ----------------------------------------------------------------------
#  Descripciones que aparecen al pasar el cursor sobre una pieza de la tienda
#  (mismo orden que las listas: FORMATOS, MECANISMOS, LANZADORES, MOTORES, ENERGIAS, COMMS, INSTRS, BLINDAJES)
# ----------------------------------------------------------------------
TIENDA_DESC = {
    "formato": [
        "Estructura básica y ligera. Ideal para empezar y llevar pocos aparatos cerca de la Tierra.",
        "Amplía el espacio interior para cargar más equipo y soporta mayor peso sin perder equilibrio.",
        "Chasis reforzado de máxima capacidad. Permite instalar todo el equipo pesado necesario para viajar a la Luna o Marte.",
    ],
    "seguridad": [
        "Sistema desactivado. Impide el despegue para evitar accidentes en la plataforma.",
        "Activa los seguros e interruptores de control. Desbloquea el lanzamiento y evita fallos al encender motores.",
    ],
    "lanz": [
        "Impulso básico para salir de la atmósfera. Alcanza solo órbitas cercanas a la Tierra.",
        "Aumenta la potencia de empuje para cargar naves medianas y alcanzar la órbita de la Luna.",
        "Máxima fuerza de despegue. Único cohete capaz de impulsar cargas pesadas hasta Marte.",
    ],
    "motor": [
        "La nave queda a la deriva sin poder corregir su rumbo ni viajar a otros destinos.",
        "Propulsión rápida de corto alcance. Permite maniobrar y moverse en misiones alrededor de la Tierra.",
        "Alta eficiencia y velocidad constante con bajo consumo. Indispensable para viajes largos a la Luna y Marte.",
    ],
    "energia": [
        "Genera electricidad básica para mantener encendidos los sistemas simples cerca de la Tierra.",
        "Triplica la producción eléctrica para alimentar varios instrumentos científicos al mismo tiempo.",
        "Máxima captación solar. Obligatorio para dar energía al motor iónico y equipos avanzados.",
    ],
    "comm": [
        "Señal básica de corto alcance. Envía pocos datos al día y solo funciona cerca de la Tierra.",
        "Mejora la potencia de transmisión para enviar información científica desde la Luna sin perder señal.",
        "Conexión de espacio profundo. Envía grandes cantidades de datos a alta velocidad incluso desde Marte.",
    ],
    "instr": [
        "Toma fotografías de alta calidad para estudiar la superficie y el clima de la Tierra.",
        "Usa ondas para atravesar nubes densas y mapear el terreno o la atmósfera de otros mundos.",
        "Analiza la luz para descubrir de qué materiales y minerales está hecho un planeta.",
        "Mide cambios de temperatura extrema para detectar calor o hielo oculto en el espacio.",
        "Amplifica y rebota señales de radio para mejorar la comunicación con otras naves o bases.",
        "Mide partículas invisibles, radiación y campos magnéticos en el espacio exterior.",
    ],
    "blind": [
        "Capa ligera que protege los circuitos básicos contra el calor y la radiación cercana a la Tierra.",
        "Refuerzo intermedio que evita daños por radiación solar al salir hacia la Luna.",
        "Escudo de máxima resistencia. Protege la nave contra la radiación extrema en viajes hacia Marte.",
    ],
}


def descripcion_pieza(clave, idx):
    lista = TIENDA_DESC.get(clave, [])
    return lista[idx] if 0 <= idx < len(lista) else ""


def draw_tooltip(titulo, texto, ancho=270):
    """Recuadro flotante junto al cursor (se mantiene dentro de la ventana)."""
    lineas = wrap(texto, font_s, ancho)
    w = max(max(font_s.size(l)[0] for l in lineas), font.size(titulo)[0]) + 24
    h = 40 + len(lineas) * 17
    x, y = mouse_ui[0] + 18, mouse_ui[1] + 20
    if x + w > UI_W - 6:
        x = mouse_ui[0] - w - 14
    if y + h > UI_H - 6:
        y = mouse_ui[1] - h - 14
    x, y = max(6, x), max(6, y)
    caja = pygame.Rect(x, y, w, h)
    fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
    pygame.draw.rect(fondo, (8, 12, 32, 245), fondo.get_rect(), border_radius=8)
    ui.blit(fondo, caja.topleft)
    pygame.draw.rect(ui, (255, 255, 0), caja, 2, border_radius=8)
    txt(titulo, font, (255, 255, 0), (x + 12, y + 8))
    for k, l in enumerate(lineas):
        txt(l, font_s, (220, 235, 255), (x + 12, y + 34 + k * 17))


# ----------------------------------------------------------------------
#  PANEL: TIENDA
# ----------------------------------------------------------------------
def draw_panel_tienda():
    ventana("TIENDA DE COMPONENTES", (20, 15, 760, 570))
    mis = MISIONES[game["mision"]] if game["mision"] is not None else None

    caja = pygame.Rect(35, 78, 175, 50)
    pygame.draw.rect(ui, (20, 30, 70), caja, border_radius=6)
    pygame.draw.rect(ui, (255, 255, 0), caja, 1, border_radius=6)
    txt("Tus fondos", font_xs, (170, 200, 230), (caja.x + 10, caja.y + 5))
    txt(f"${game['dinero']}M", font_title, (255, 255, 0), (caja.x + 10, caja.y + 19))

    # --- pestañas por tipo de pieza ---
    for i, (nombre, clave, lista) in enumerate(COMPRABLES):
        t = pygame.Rect(35, 140 + i * 42, 175, 38)
        sel = (clave == tienda_cat)
        hover = t.collidepoint(mouse_ui)
        pygame.draw.rect(ui, (30, 60, 120) if sel else ((24, 40, 90) if hover else (18, 28, 62)), t, border_radius=6)
        pygame.draw.rect(ui, (255, 255, 0) if sel else (0, 130, 180), t, 2 if sel else 1, border_radius=6)
        txt(nombre, font, (255, 255, 255), (t.x + 10, t.y + 10))
        tengo = sum(1 for k in range(len(lista)) if tiene(clave, k))
        txt(f"{tengo}/{len(lista)}", font_xs, (150, 170, 200), (t.right - 36, t.y + 22))
        if mis is not None:
            idx = mis["recomendados"].get(clave)
            if idx is not None and not tiene(clave, idx):
                pygame.draw.circle(ui, (255, 170, 60), (t.right - 14, t.y + 11), 5)  # te falta una pieza de este tipo
        clickables.append((t, ("tcat", clave)))

    # --- cabecera ---
    lista = LISTA_DE[tienda_cat]
    txt(NOMBRE_CAT[tienda_cat], font_title, (255, 255, 0), (225, 78))
    for k, l in enumerate(wrap(CAT_AYUDA[tienda_cat], font_s, 540)[:2]):
        txt(l, font_s, (190, 210, 235), (225, 108 + k * 18))

    # --- piezas ---
    rec = mis["recomendados"].get(tienda_cat) if mis is not None else None
    tip = None  # (titulo, texto) de la pieza bajo el cursor
    for i, c in enumerate(lista):
        card = pygame.Rect(225, 150 + i * 60, 545, 56)
        propio = tiene(tienda_cat, i)
        inicial = i in INICIALES[tienda_cat]
        hover = card.collidepoint(mouse_ui)
        if hover:
            tip = (c["nombre"], descripcion_pieza(tienda_cat, i))
        pygame.draw.rect(ui, (18, 55, 60) if propio else ((24, 40, 90) if hover else (18, 28, 62)), card,
                         border_radius=6)
        pygame.draw.rect(ui, (90, 230, 120) if propio else ((255, 255, 0) if hover else (0, 130, 180)), card, 2,
                         border_radius=6)
        nx = card.x + 32
        if rec == i:
            estrella(ui, card.x + 16, card.y + 14, 8, (255, 220, 0))
        txt(c["nombre"], font, (255, 255, 255), (nx, card.y + 4))
        if rec == i:
            chip("RECOMENDADA", nx + font.size(c["nombre"])[0] + 10, card.y + 4, (150, 110, 0), f=font_xs)
        txt(recortar(c["simple"], font_s, 375), font_s, (190, 210, 235), (nx, card.y + 22))
        txt(recortar(stats_simples(c), font_xs, 375), font_xs, (140, 160, 190), (nx, card.y + 39))
        bx = card.right - 140
        if propio and inicial:
            txt("Incluida", font_s, (90, 230, 120), (bx + 64, card.centery), center=True)
        elif propio:
            txt("COMPRADA", font_xs, (90, 230, 120), (bx + 64, card.y + 9), center=True)
            button((bx, card.y + 24, 128, 26), f"Vender +${c['costo']}M", ("vender", tienda_cat, i))
        else:
            falta = c["costo"] - game["dinero"]
            if falta <= 0:
                button((bx, card.y + 11, 128, 34), f"Comprar ${c['costo']}M", ("comprar", tienda_cat, i))
            else:
                button((bx, card.y + 11, 128, 34), f"Faltan ${falta}M", "nada", enabled=False)

    # --- consejo ---
    if mis is None:
        tip_txt, col = "Consejo: primero elige una misión en la computadora y te diré qué piezas conviene comprar.", (
            170, 170, 180)
    elif rec is not None and tiene(tienda_cat, rec):
        tip_txt, col = f"Ya tienes la pieza recomendada para «{mis['nombre']}». Úsala en el HANGAR.", (90, 230, 120)
    elif rec is not None:
        c = lista[rec]
        tip_txt, col = f"Para «{mis['nombre']}» te recomendamos: {c['nombre']} (${c['costo']}M).", (255, 220, 120)
    else:
        tip_txt, col = "", (200, 200, 200)
    for k, l in enumerate(wrap(tip_txt, font_s, 540)[:2]):
        txt(l, font_s, col, (225, 520 + k * 18))
    button((35, 530, 175, 36), "Cerrar", "cerrar")

    # --- descripción flotante (se dibuja al final para quedar encima de todo) ---
    if tip and tip[1]:
        draw_tooltip(tip[0], tip[1])


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
            estrella(ui, carta.centerx - 62, 260, 7, (255, 220, 0))
            txt("RECOMENDADO", font_s, (90, 230, 120), (carta.centerx + 8, 260), center=True)

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
        if tiene("lanz", i):
            button((carta.x + 15, 482, 200, 36), "Elegido" if elegido else "Elegir este cohete", ("cohete", i),
                   selected=elegido)
        else:
            button((carta.x + 15, 482, 200, 36), f"Sin comprar (${l['costo']}M)", ("cohete", i), enabled=False)
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
        pts = puntaje(r)
        txt(f"Puntuación: {pts} puntos", font_title, (255, 255, 0), (40, 440))
        txt(f"Ciencia {r['ciencia']}  |  Nave de ${r['costo']}M  |  Peso libre {round(r['cap'] - r['masa'], 2)} kg", font_s,
            (200, 220, 255), (40, 478))
    else:
        txt(f"Puntuación parcial: {sum(1 for c in r['checks'] if c[1]) * 30}", font_title, (255, 150, 90), (40, 440))
        txt("Usa «Sugerir piezas» en el Hangar.", font_s, (200, 220, 255), (40, 474))
        txt("Si despegas así, el cohete se dañará en pleno vuelo y perderás fondos.", font_s, (255, 150, 120), (40, 493))
    if exito:
        button((40, 515, 390, 44), "¡DESPEGAR!", "despegar")
    else:
        button((40, 515, 390, 44), "DESPEGAR DE TODOS MODOS (habrá falla)", "despegar", peligro=True)
    button((450, 515, 190, 44), "Volver al hangar", "taller")
    button((655, 515, 105, 44), "Cerrar", "cerrar")


def simular_cambio(clave, idx):
    """Evalúa la nave como si pusieras otra pieza (sin cambiar tu nave de verdad)."""
    original = game["nave"][clave]
    game["nave"][clave] = idx
    try:
        return evaluar(game["mision"])
    finally:
        game["nave"][clave] = original


def draw_panel_simula():
    global det_cat
    ventana("¿QUÉ PASA SI...?", (10, 10, 780, 580))
    if game["mision"] is None:
        txt("Elige una misión en la computadora para probar cambios.", font, (255, 190, 90), (40, 100))
        button((25, 542, 200, 34), "Volver al hangar", "taller")
        return
    if det_cat == "orbita":
        det_cat = "formato"  # el destino lo fija la misión, no se puede cambiar
    clave = det_cat
    lista = LISTA_DE[clave]
    actual = game["nave"][clave]
    mis = MISIONES[game["mision"]]
    r0 = evaluar(game["mision"])
    pts0 = puntaje(r0) if r0["ok"] else None

    txt("Pasa el mouse sobre una pieza para ver qué pasaría si la pones. Tu nave no cambia hasta que la equipes.",
        font_s, (190, 210, 235), (25, 70))

    # pestañas de categoría
    for i, (nombre, k, _) in enumerate(COMPRABLES):
        tab = pygame.Rect(22 + i * 94, 92, 90, 26)
        sel = (k == clave)
        hover = tab.collidepoint(mouse_ui)
        pygame.draw.rect(ui, (30, 60, 120) if sel else ((24, 40, 90) if hover else (18, 28, 62)), tab, border_radius=6)
        pygame.draw.rect(ui, (255, 255, 0) if sel else (0, 130, 180), tab, 2 if sel else 1, border_radius=6)
        txt(nombre, font_s, (255, 255, 255), tab.center, center=True)
        clickables.append((tab, ("cat", k)))

    # tabla comparativa
    cols = {"pieza": 30, "vuela": 262, "peso": 380, "energia": 478, "puntos": 585, "costo": 702}
    for k, tit in (("pieza", "Pieza"), ("vuela", "¿Vuela?"), ("peso", "Peso libre"), ("energia", "Energía libre"),
                   ("puntos", "Puntos"), ("costo", "Costo")):
        txt(tit, font_xs, (150, 170, 200), (cols[k], 124))
    hover_i = None
    for i, c in enumerate(lista):
        fila = pygame.Rect(22, 142 + i * 42, 756, 38)
        r = simular_cambio(clave, i)
        es_actual = (i == actual)
        hover = fila.collidepoint(mouse_ui)
        if hover:
            hover_i = i
        pygame.draw.rect(ui, (30, 60, 120) if es_actual else ((24, 40, 90) if hover else (18, 28, 62)), fila,
                         border_radius=6)
        pygame.draw.rect(ui, (255, 255, 0) if es_actual else (0, 130, 180), fila, 2 if es_actual else 1,
                         border_radius=6)
        txt(recortar(c["nombre"], font_s, 220), font_s, (255, 255, 255), (cols["pieza"], fila.y + 4))
        if es_actual:
            sub, subcol = "(puesta ahora)", (255, 255, 0)
        elif tiene(clave, i):
            sub, subcol = "(la tienes)", (120, 220, 150)
        else:
            sub, subcol = f"(no la tienes: ${c['costo']}M)", (255, 170, 110)
        txt(sub, font_xs, subcol, (cols["pieza"], fila.y + 21))
        fallos = sum(1 for ch in r["checks"] if not ch[1])
        if r["ok"]:
            chip("SÍ VUELA", cols["vuela"], fila.y + 7, (20, 110, 60))
        else:
            chip(f"NO VUELA ({fallos})", cols["vuela"], fila.y + 7, (150, 40, 40))
        libre_p = round(r["cap"] - r["masa"], 2)
        libre_e = round(r["gen"] - r["consumo"], 1)
        txt(f"{libre_p:+.2f} kg", font_s, (90, 230, 120) if libre_p >= 0 else (255, 110, 100), (cols["peso"], fila.y + 11))
        txt(f"{libre_e:+.1f} W", font_s, (90, 230, 120) if libre_e >= 0 else (255, 110, 100), (cols["energia"], fila.y + 11))
        if r["ok"]:
            pts = puntaje(r)
            txt(str(pts), font_s, (255, 255, 255), (cols["puntos"], fila.y + 11))
            if pts0 is not None and not es_actual:
                d = pts - pts0
                txt(f"({d:+d})", font_xs, (90, 230, 120) if d >= 0 else (255, 150, 100),
                    (cols["puntos"] + 40, fila.y + 13))
        else:
            txt("-", font_s, (150, 150, 160), (cols["puntos"], fila.y + 11))
        txt(f"${c.get('costo', 0)}M", font_s, (200, 220, 255), (cols["costo"], fila.y + 11))
        clickables.append((fila, ("equipar", clave, i) if tiene(clave, i) else ("bloqueada", clave, i)))

    # explicación de la pieza señalada
    det_i = hover_i if hover_i is not None else actual
    rr = simular_cambio(clave, det_i)
    caja = pygame.Rect(22, 404, 756, 128)
    pygame.draw.rect(ui, (10, 16, 40), caja, border_radius=8)
    pygame.draw.rect(ui, (0, 130, 180), caja, 1, border_radius=8)
    txt("Si pones: " + lista[det_i]["nombre"], font, (255, 255, 0), (34, 410))
    lineas = []
    if rr["ok"]:
        pts = puntaje(rr)
        extra = f" ({pts - pts0:+d} que ahora)" if (pts0 is not None and det_i != actual) else ""
        lineas.append((f"Cumple todos los requisitos. Puntuación estimada: {pts}{extra}.", (90, 230, 120)))
        lineas.append((f"Ciencia {rr['ciencia']}  |  Nave de ${rr['costo']}M  |  Peso libre {round(rr['cap'] - rr['masa'], 2)} kg"
                       f"  |  Energía libre {round(rr['gen'] - rr['consumo'], 1)} W", (200, 220, 255)))
        if rr["cap"] - rr["masa"] < 0.3:
            lineas.append(("Ojo: el margen de peso es muy justo.", (255, 190, 90)))
        if rr["gen"] - rr["consumo"] < 2:
            lineas.append(("Ojo: casi no sobra energía.", (255, 190, 90)))
        if rr["costo"] > mis["presupuesto"]:
            lineas.append((f"Ojo: te pasas del presupuesto de la misión (${mis['presupuesto']}M).", (255, 190, 90)))
        if rr["costo"] < mis["presupuesto"] * 0.6:
            lineas.append(("Te sobra mucho dinero: ¿podrías usarlo en una pieza con más ciencia?", (170, 200, 230)))
    else:
        lineas.append(("Con esta pieza el cohete NO podría volar bien:", (255, 110, 100)))
        for nombre, ok, causa in rr["checks"]:
            if not ok:
                lineas.append(("- " + causa, (255, 200, 170)))
    y = 436
    for texto, col in lineas:
        for l in wrap(texto, font_s, 725):
            if y < 524:
                txt(l, font_s, col, (34, y))
            y += 18

    button((25, 542, 200, 34), "Volver al hangar", "taller")
    button((235, 542, 200, 34), "Revisar vuelo", "evaluar")
    txt("Clic en una fila = equipar esa pieza (si ya la tienes)", font_xs, (150, 170, 200), (452, 552))
    button((670, 542, 105, 34), "Cerrar", "cerrar")


# ----------------------------------------------------------------------
#  REPORTE CIENTÍFICO (al terminar la misión)
# ----------------------------------------------------------------------
DIAS_OPERACION = {"Luna": 30, "Marte": 90}

DESCUBRIMIENTOS = {
    ("Luna", "espectro"): "El espectrómetro encontró hielo de agua mezclado con el suelo de un cráter en sombra. "
                          "¡Podría servir para beber y fabricar combustible!",
    ("Luna", "radar"): "El radar miró bajo la superficie: hay capas de polvo lunar de varios metros y cavidades "
                       "ocultas, posibles refugios para futuros astronautas.",
    ("Luna", "particulas"): "El detector midió la radiación del espacio sin atmósfera que la frene: es mucho más "
                            "fuerte que en la Tierra. Dato clave para proteger a los astronautas.",
    ("Luna", "ir"): "El sensor térmico midió más de 100 °C bajo el sol y unos -170 °C en cráteres en sombra: "
                    "un cambio de temperatura enorme.",
    ("Luna", "optico"): "La cámara fotografió cráteres y rocas con gran detalle y ayudó a elegir sitios seguros "
                        "para aterrizar.",
    ("Luna", "comm"): "El repetidor mejoró la conexión con la Tierra: ahora los datos llegan más rápido.",
    ("Marte", "espectro"): "El espectrómetro halló óxido de hierro (por eso Marte es rojo) y minerales que se "
                           "forman con agua: señales de que hubo agua líquida hace mucho tiempo.",
    ("Marte", "ir"): "El sensor térmico midió unos 20 °C al mediodía y cerca de -90 °C de noche: el suelo "
                     "marciano pierde el calor muy rápido.",
    ("Marte", "radar"): "El radar atravesó el suelo y detectó capas de hielo bajo la superficie.",
    ("Marte", "particulas"): "El detector midió la radiación que llega a Marte, que casi no tiene atmósfera "
                             "ni escudo magnético que la frene.",
    ("Marte", "optico"): "La cámara mostró un paisaje rojizo de rocas y polvo y ayudó a elegir por dónde "
                         "explorar con el dron.",
    ("Marte", "comm"): "El repetidor ayuda a que los mensajes de la superficie lleguen a la Tierra, aunque "
                       "tarden varios minutos.",
}


def construir_reporte(idx):
    """Resume cómo les fue a tus decisiones: datos, descubrimiento, consecuencias y puntuación."""
    mis = MISIONES[idx]
    r = evaluar(idx)
    n = game["nave"]
    ins = INSTRS[n["instr"]]
    orb = ORBITAS[n["orbita"]]
    dias = DIAS_OPERACION.get(mis["destino"], 30)
    gb = round(min(r["datos"], r["enlace"]) * dias, 1)
    desc = DESCUBRIMIENTOS.get((mis["destino"], ins["tag"]), "Tu instrumento recolectó datos útiles para la ciencia.")
    if mis["destino"] == "Marte":
        desc += " Además, el dron exploró los alrededores del aterrizaje."

    verde, naranja, azul = (90, 230, 120), (255, 190, 90), (200, 220, 255)
    dec = []
    d_en = round(r["gen"] - r["consumo"], 1)
    if d_en < 3:
        dec.append((f"Energía muy justa: solo sobraron {d_en} W. Paneles mejores darían más margen.", naranja))
    else:
        dec.append((f"Energía: sobraron {d_en} W para tus aparatos.", verde))
    if orb["solar"] < 1:
        dec.append((f"En {mis['destino']} llega menos luz solar: tus paneles rindieron x{orb['solar']}.", azul))
    dec.append((f"Antena: enviaba hasta {r['enlace']} GB/día y tu instrumento generaba {r['datos']} GB/día.",
                verde if r["enlace"] >= r["datos"] * 2 else naranja))
    libre = round(r["cap"] - r["masa"], 2)
    dec.append((f"Peso: te sobraron {libre} kg de {r['cap']} kg.", verde if libre >= 0.3 else naranja))
    ahorro_m = r["pres"] - r["costo"]
    if ahorro_m >= 0:
        dec.append((f"Dinero: gastaste ${r['costo']}M de ${r['pres']}M y ahorraste ${ahorro_m}M.", verde))
    else:
        dec.append((f"Dinero: te pasaste ${-ahorro_m}M del presupuesto (${r['pres']}M).", naranja))
    dec.append((f"Protección: {r['prot']} contra {r['prot_req']} necesaria frente a la radiación.",
                verde if r["prot"] - r["prot_req"] >= 5 else naranja))

    ahorro = max(0.0, 1 - r["costo"] / r["pres"]) if r["pres"] else 0.0
    peso_pt = max(0.0, 1 - r["masa"] / r["cap"]) * 200
    desglose = (300, r["ciencia"] * 4, int(ahorro * 300), int(peso_pt))
    total = puntaje(r)
    fracs = [(desglose[1] / (95 * 4), "Un instrumento con más ciencia subiría tu puntuación (aunque cuesta más)."),
             (desglose[2] / 300, "Gastar menos en piezas que no necesitabas subiría tu puntuación."),
             (desglose[3] / 200, "Una nave más ligera subiría tu puntuación.")]
    consejo = min(fracs, key=lambda f: f[0])[1]
    rango = "Director de misión" if total >= 900 else ("Ingeniero espacial" if total >= 700 else "Cadete espacial")
    return {"mision": mis["nombre"], "destino": mis["destino"], "instrumento": ins["nombre"], "gb": gb, "dias": dias,
            "descubrimiento": desc, "decisiones": dec, "desglose": desglose, "total": total, "rango": rango,
            "consejo": consejo}


def draw_reporte():
    rep_ = ultimo_reporte
    ventana("REPORTE CIENTÍFICO", (40, 16, 720, 570))
    txt(f"{rep_['mision']}  -  {rep_['destino']}  -  Instrumento: {rep_['instrumento']}", font, (255, 255, 0), (60, 82))
    txt("DATOS RECOLECTADOS", font_s, (0, 200, 255), (60, 108))
    txt(f"{rep_['gb']} GB en {rep_['dias']} días de operación, enviados a la Tierra.", font, (255, 255, 255), (60, 126))
    txt("DESCUBRIMIENTO", font_s, (0, 200, 255), (60, 156))
    for k, l in enumerate(wrap(rep_["descubrimiento"], font, 650)[:3]):
        txt(l, font, (200, 255, 210), (60, 174 + k * 22))
    txt("TUS DECISIONES Y SUS CONSECUENCIAS", font_s, (0, 200, 255), (60, 252))
    for k, (texto, col) in enumerate(rep_["decisiones"][:6]):
        pygame.draw.circle(ui, col, (68, 279 + k * 19), 4)
        txt(recortar(texto, font_s, 630), font_s, col, (80, 270 + k * 19))
    b, c, a, p = rep_["desglose"]
    txt("PUNTUACIÓN", font_s, (0, 200, 255), (60, 398))
    txt(f"Base {b}  +  Ciencia {c}  +  Ahorro {a}  +  Peso ligero {p}", font_s, (200, 220, 255), (60, 416))
    txt(f"Total: {rep_['total']} puntos  -  {rep_['rango']}", font_title, (255, 255, 0), (60, 438))
    for k, l in enumerate(wrap("Consejo: " + rep_["consejo"], font_s, 650)[:2]):
        txt(l, font_s, (170, 200, 230), (60, 486 + k * 18))
    button((60, 534, 300, 40), "Volver al resultado", "reporte_volver")
    button((400, 534, 300, 40), "Volver a la estación", "cerrar")


def draw_glosario():
    ventana("GLOSARIO - ¿QUÉ SIGNIFICA?", (40, 30, 720, 540))
    for i, (palabra, definicion) in enumerate(GLOSARIO_TEXTO):
        x, y = 70 + (i % 2) * 340, 95 + (i // 2) * 80
        txt(palabra + ":", font, (255, 255, 0), (x, y))
        for k, l in enumerate(wrap(definicion, font_s, 315)[:3]):
            txt(l, font_s, (200, 220, 255), (x, y + 22 + k * 17))
    button((320, 520, 160, 36), "Cerrar", "cerrar_glosario")


# ======================================================================
#  ACCIONES
# ======================================================================
def mision_sugerida():
    """Misión que aparece seleccionada al abrir la computadora."""
    if game["mision"] is not None:
        return game["mision"]
    for i in range(len(MISIONES)):
        if mision_estado(i) == "disponible":
            return i
    return len(MISIONES) - 1


def categoria_tienda_inicial():
    """Al abrir la tienda se muestra primero un tipo de pieza que te falte para tu misión."""
    if game["mision"] is not None:
        falt = piezas_faltantes(game["mision"])
        if falt:
            return falt[0][0]
    return tienda_cat


def iniciar(continuar):
    global estado, luna_activa
    keys_down.clear()
    luna_activa = False
    game["mision"], game["nave"], game["dinero"] = None, nave_default(), DINERO_INICIAL
    game["inventario"], game["completadas"] = inventario_inicial(), []
    game["jugador"] = ""
    player.x, player.y = inicio_jugador()
    luna_guardada = None
    if continuar:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                p = json.load(f)["partida"]
            h0 = int(p.get("altura_jugador", player_mod.PLAYER_HEIGHT))  # altura con la que se guardó
            player.x, player.y = player.convertir_pos(p["x"], p["y"], h0)
            game["jugador"] = str(p.get("jugador", ""))[:20]
            # Las partidas anteriores a la tienda no tienen inventario: empiezan con la economía nueva.
            if "inventario" in p:
                game["completadas"] = [int(i) for i in p.get("completadas", []) if 0 <= int(i) < len(MISIONES)]
                game["dinero"] = int(p.get("dinero", DINERO_INICIAL))
                for _, clave, lista in COMPRABLES:
                    for i in p["inventario"].get(clave, []):
                        if 0 <= int(i) < len(lista):
                            game["inventario"][clave].add(int(i))
                for _, clave, lista in CATEGORIAS:
                    v = max(0, min(int(p["nave"].get(clave, 0)), len(lista) - 1))
                    game["nave"][clave] = v if tiene(clave, v) else 0
                m = p.get("mision")
                if isinstance(m, int) and 0 <= m < len(MISIONES) and mision_estado(m) == "disponible":
                    game["mision"] = m
                    luna_guardada = p.get("luna")
                    if luna_guardada and "px" in luna_guardada and "py" in luna_guardada:
                        luna_guardada["px"], luna_guardada["py"] = player.convertir_pos(
                            luna_guardada["px"], luna_guardada["py"], h0)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    # Si había una misión lunar en curso, se continúa ahí (no se puede volver a la estación sin completarla)
    if luna_guardada and game["mision"] is not None and iniciar_luna(luna_guardada):
        return
    estado = ESTACION


def on_click(ident):
    global estado, running, sel_m, det_cat, tienda_cat, ok_pagina
    if isinstance(ident, tuple):
        tipo = ident[0]
        if tipo == "mision":
            sel_m = ident[1]
        elif tipo == "cohete":
            if tiene("lanz", ident[1]):
                game["nave"]["lanz"] = ident[1]
                det_cat = "lanz"
                guardar()
        elif tipo == "cat":
            det_cat = ident[1]
        elif tipo == "tcat":
            tienda_cat = ident[1]
        elif tipo == "equipar":
            _, clave, idx = ident
            if tiene(clave, idx):
                game["nave"][clave] = idx
                det_cat = clave
                guardar()
        elif tipo == "bloqueada":
            _, clave, idx = ident
            c = LISTA_DE[clave][idx]
            toast(f"Aún no tienes «{c['nombre']}». Cómprala en la TIENDA (${c['costo']}M).", (255, 190, 90))
        elif tipo == "comprar":
            comprar(ident[1], ident[2])
        elif tipo == "vender":
            vender(ident[1], ident[2])
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
        if mision_estado(sel_m) == "disponible":
            m = MISIONES[sel_m]
            game["mision"] = sel_m
            game["nave"]["orbita"] = m["orbitas"][0]  # el destino se ajusta solo
            siguiente = ("Te faltan piezas: pasa por la TIENDA." if piezas_faltantes(sel_m)
                         else "Ya tienes todo: ve al HANGAR a armar tu cohete.")
            toast(f"Misión «{m['nombre']}» aceptada. {siguiente}", (90, 230, 120))
            guardar()
            keys_down.clear()
            estado = ESTACION  # la ventana se cierra al aceptar
    elif ident == "evaluar":
        estado = PANEL_INFORME
    elif ident == "despegar":
        iniciar_despegue()
    elif ident == "taller" or ident == "atras":
        estado = PANEL_NAVE
    elif ident == "ver_cohetes":
        estado = PANEL_COHETE
    elif ident == "simula":
        estado = PANEL_SIMULA
    elif ident == "reporte":
        ok_pagina = 1
    elif ident == "reporte_volver":
        ok_pagina = 0
    elif ident == "sugerir":
        sugerir_arreglo()
    elif ident == "cerrar_glosario":
        estado = glosario_volver
    elif ident == "cerrar":
        estado = PANEL_NAVE if estado in (PANEL_COHETE, PANEL_SIMULA) else ESTACION


def iniciar_despegue():
    """Arranca la animación SOLO si todos los componentes son correctos."""
    global estado, anim
    if game["mision"] is None:
        return
    r = evaluar(game["mision"])
    n = game["nave"]
    falla, perdida = None, 0
    if not r["ok"]:
        # Se puede despegar con la revisión en rojo, pero el cohete falla en pleno vuelo y se pierden fondos
        falla = [c[2] for c in r["checks"] if not c[1]]
        perdida = min(game["dinero"], max(10, round(r["costo"] * 0.10)))
        game["dinero"] -= perdida
        guardar()
    anim = Despegue(screen, os.path.join(BASE_DIR, "images"), n["lanz"], n["orbita"],
                    ORBITAS[n["orbita"]]["nombre"], MISIONES[game["mision"]]["nombre"],
                    LANZADORES[n["lanz"]]["nombre"], puntaje(r) if r["ok"] else 0,
                    falla=falla, perdida=perdida)
    keys_down.clear()
    estado = DESPEGUE
    sonido.iniciar_despegue()  # arranque y, justo después, despegue (el cohete ya está en pantalla)


def pulsar_despegue():
    """Primer toque: salta al final de la animación. Después pasa a VIAJE EN PROGRESO."""
    global anim
    if anim is not None and not anim.terminado:
        anim.saltar()
        sonido.parar_despegue()  # al saltar la animación se cortan arranque y despegue
    elif anim is not None and anim.fallida:
        anim = None
        sonido.parar_despegue()
        regresar_estacion()
        toast("El cohete falló en pleno vuelo. Revisa la lista de revisión antes de volver a despegar.", (255, 120, 90))
    else:
        iniciar_viaje()


def sugerir_arreglo():
    """Pone las piezas recomendadas que ya compraste y avisa de las que faltan en la tienda."""
    if game["mision"] is None:
        toast("Primero elige una misión en la computadora.", (255, 190, 90))
        return
    mis = MISIONES[game["mision"]]
    faltan = []
    for clave, idx in mis["recomendados"].items():
        if tiene(clave, idx):
            game["nave"][clave] = idx
        else:
            faltan.append(LISTA_DE[clave][idx]["nombre"])
    if faltan:
        toast("Puse las piezas que ya tienes. Te falta comprar en la TIENDA: " + ", ".join(faltan) + ".",
              (255, 190, 90))
    else:
        toast("¡Listo! Puse todas las piezas recomendadas para tu misión.", (90, 230, 120))
    guardar()


# ----------------------------------------------------------------------
#  VIAJE EN PROGRESO  ->  PANTALLA NEGRA  ->  ESCENA LUNAR
# ----------------------------------------------------------------------
def regresar_estacion():
    global estado
    keys_down.clear()
    player.x, player.y = inicio_jugador()
    estado = ESTACION


def iniciar_viaje():
    global estado, anim, viaje_t0
    anim = None
    sonido.parar_despegue(500)
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
        if game["nave"]["orbita"] in DESTINO_FONDO:
            if not iniciar_luna():
                regresar_estacion()
                toast("No se pudo cargar la escena del planeta (revisa /images y la consola)", (255, 120, 90))
        else:
            completar_mision()  # destinos sin escena propia (Marte): llegar bien completa la misión
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
    global luna_items, nave_rect, nave_zona, astro_win, dron, es_marte
    n = game["nave"]
    archivo = DESTINO_FONDO.get(n["orbita"])
    if archivo is None:
        return False
    ruta = ruta_imagen(archivo)
    try:
        w, h = pygame.image.load(ruta).get_size()
    except (pygame.error, FileNotFoundError, OSError) as e:
        print("No se pudo cargar el mapa lunar:", e)
        return False

    es_marte = n["orbita"] == MARTE_ORBITA
    if es_marte:
        # Marte: en vez del robot hay un dron posado (robot_rect = dron posado)
        dron = DronMarte(ruta_imagen(DRON_PNG), w, h)
        robot_roto = robot_ok = None
        robot_rect = dron.rect_suelo.copy()
        rrw, rrh = robot_rect.size
    else:
        dron = None
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
    cx_f, cy_f = (MARTE_CX, MARTE_CY) if es_marte else (LUNA_CX, LUNA_CY)
    cx, cy = int(w * cx_f), int(h * cy_f)
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
    luna_items = [] if es_marte else generar_items(w, h, evitar, restaurar.get("items") if restaurar else None)

    if restaurar:
        robot_reparado = bool(restaurar.get("reparado"))
        if es_marte and robot_reparado:
            dron.fase = "hecho"  # el dron ya volvió y está posado
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
    if not restaurar:
        sonido.tocar(sonido.APARICION)  # llegada a la Luna o a Marte
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
    sonido.detener(sonido.DRON, 300)
    sonido.parar_despegue(300)
    estado = MENU


def interactuar_luna():
    """Tecla E (pulsación): recoger un objeto cercano, desplegar el dron (Marte) o subir a la nave."""
    global luna_fase
    if luna_fase != "listo":
        return
    prect = player.rect()
    if es_marte and dron is not None and not robot_reparado and prect.colliderect(robot_zona):
        keys_down.clear()
        player.reposo()
        dron.iniciar()
        sonido.tocar(sonido.DRON)  # una sola vez, al empezar la expedición
        luna_fase = "dron"
        return
    for it in luna_items:
        if not it["ok"] and prect.colliderect(it["rect"].inflate(90, 90)):
            it["ok"] = True
            sonido.tocar(sonido.TOMA_ITEM)
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
    """Termina la misión: da la recompensa, la marca como completada, desbloquea la siguiente y muestra el resultado."""
    global estado, luna_activa, ultima_mision, ultimo_exito, ultima_recompensa, ultimo_desbloqueo
    global ultimo_reporte, ok_pagina
    sonido.parar_despegue(500)  # termina el sonido del despegue de regreso
    idx = game["mision"]
    mis = MISIONES[idx] if idx is not None else None
    ultimo_reporte = construir_reporte(idx) if idx is not None else None
    ok_pagina = 0
    ultima_mision = mis["nombre"] if mis else "-"
    ultimo_exito = mis["exito"] if mis else ""
    ultima_recompensa = mis["recompensa"] if mis else 0
    antes = [i for i in range(len(MISIONES)) if mision_estado(i) == "disponible"]
    nueva = idx is not None and idx not in game["completadas"]
    if nueva:
        game["completadas"].append(idx)
    ultimo_desbloqueo = [MISIONES[i]["nombre"] for i in range(len(MISIONES))
                         if mision_estado(i) == "disponible" and i not in antes]
    game["dinero"] += ultima_recompensa
    game["mision"] = None
    luna_activa = False
    player.x, player.y = inicio_jugador()
    keys_down.clear()
    guardar()
    if nueva and len(game["completadas"]) >= len(MISIONES):
        iniciar_final()  # última misión completada: cinemática final y créditos
    else:
        estado = MISION_OK


def iniciar_final():
    global estado, final, final_sonando
    final_sonando = True
    n = game["nave"]
    final = FinalEpico(screen, os.path.join(BASE_DIR, "images"), n["lanz"], LANZADORES[n["lanz"]]["nombre"],
                       ultima_mision, [m["nombre"] for m in MISIONES], game.get("jugador", ""))
    keys_down.clear()
    estado = FINAL


def update_luna():
    global luna_fase, reparar_t0, robot_reparado, reparado_t, fin_t0
    ahora = pygame.time.get_ticks()
    t = (ahora - luna_t0) / 1000.0

    # Fuera de la fase de caminar, el astronauta se ve en su sprite normal y no suenan pasos ni reparación
    if luna_fase != "listo":
        player.reposo()
        sonido.pasos(False)
        sonido.parar(sonido.REPARAR)

    if luna_fase == "bajando":
        if t >= LUNA_DEMORA + LUNA_LLEGADA:
            luna_fase = "listo"
        return

    if luna_fase == "dron":
        # El astronauta mira mientras el dron hace su expedición; al volver se puede regresar a la nave
        player.reposo()
        dron.update()
        if dron.hecho:
            sonido.detener(sonido.DRON, 200)  # por si sigue sonando al aterrizar
            robot_reparado = True  # aquí significa "objetivo cumplido"
            reparado_t = ahora
            luna_fase = "listo"
        return

    if luna_fase == "listo":
        cerca_robot = player.rect().colliderect(robot_zona)
        todos = all(it["ok"] for it in luna_items)
        if cerca_robot and todos and pygame.K_e in keys_down and not robot_reparado and not es_marte:
            # Manteniendo E junto al robot: el astronauta se queda quieto mientras repara
            player.reposo()
            sonido.pasos(False)
            sonido.loop(sonido.REPARAR)  # suena en bucle hasta que termina la reparación
            if reparar_t0 is None:
                reparar_t0 = ahora
            if (ahora - reparar_t0) / 1000.0 >= T_REPARAR:
                robot_reparado = True
                reparado_t = ahora
                reparar_t0 = None
                sonido.parar(sonido.REPARAR)
        else:
            reparar_t0 = None
            sonido.parar(sonido.REPARAR)  # soltaste la E antes de terminar
            px, py = player.x, player.y
            player.update(luna_map)
            sonido.pasos(player.x != px or player.y != py)
        return

    # Secuencia final: celebrar -> subir a la nave -> volar a la Tierra
    tf = (ahora - fin_t0) / 1000.0
    if luna_fase == "celebrando" and tf >= T_CELEBRAR:
        luna_fase, fin_t0 = "subiendo", ahora
        sonido.iniciar_despegue()  # despegue de regreso: arranque y luego despegue
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


def caja_objeto(it, base):
    """Cartel al acercarte a una pieza: [E] Recoger + para qué sirve en el repetidor."""
    apodo, desc = OBJETOS_DESC.get(it["id"], ("", ""))
    titulo = f"[E]  Recoger {it['nombre']}" + (f"  -  {apodo}" if apodo else "")
    lineas = wrap(desc, font, 560) if desc else []
    ancho = max([font.size(titulo)[0]] + [font.size(l)[0] for l in lineas]) + 40
    alto = 16 + 26 + (len(lineas) * 22 + 6 if lineas else 0) + 8
    box = pygame.Rect(0, 0, ancho, alto)
    box.midbottom = base
    pygame.draw.rect(screen, (0, 0, 0), box, border_radius=8)
    pygame.draw.rect(screen, (255, 255, 0), box, 2, border_radius=8)
    screen.blit(font.render(titulo, True, (255, 255, 0)), (box.x + 20, box.y + 12))
    for k, l in enumerate(lineas):
        screen.blit(font.render(l, True, (220, 235, 255)), (box.x + 20, box.y + 44 + k * 22))


def hud_objetivo():
    """Mensaje arriba a la derecha: cuántos objetos llevas, o REGRESO A CASA."""
    if es_marte and not robot_reparado:
        lineas = [("Objetivo: expedición del dron", (255, 255, 0)),
                  ("[  ] Desplegar el dron", (200, 200, 200))]
    elif robot_reparado:
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
    rr = robot_img.get_rect(midbottom=robot_rect.midbottom) if robot_img is not None else robot_rect

    def pintar_robot():
        if dron is not None:
            dron.draw(luna_view, camera)
        else:
            luna_view.blit(robot_img, (rr.x - cam_x, rr.y - cam_y))

    def pintar_items():
        for it in luna_items:
            if it["ok"]:
                continue
            r = it["rect"]
            luna_view.blit(it["img"], (r.x - cam_x, r.y - cam_y))

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
    extra = ("Llegando a " + ("Marte" if es_marte else "la Luna") + "...") if luna_fase == "bajando" else "WASD o flechas: caminar   E: interactuar"
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
            caja_objeto(item_cerca, base)
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
        elif es_marte and not robot_reparado and prect.colliderect(robot_zona):
            caja_texto("[E]  Desplegar el dron", (255, 255, 0), midbottom=base)
        elif not robot_reparado and prect.colliderect(robot_zona):
            if todos:
                caja_texto(f"Mantén [E] {T_REPARAR:g} segundos para reparar el robot", (255, 255, 0), midbottom=base)
            else:
                caja_texto(f"Te faltan objetos para repararlo ({n_ok}/{len(luna_items)})", (255, 170, 90),
                           midbottom=base)
        elif robot_reparado and prect.colliderect(nave_zona):
            caja_texto("[E]  Volver a la Tierra", (90, 230, 120), midbottom=base)
        if robot_reparado and ahora - reparado_t < 4000:
            caja_texto("¡Expedición completada! Regresa a la nave" if es_marte
                       else "¡Robot reparado! Regresa a la nave", (90, 230, 120), midtop=(SCREEN_W // 2, 60))

    if luna_fase == "dron" and dron is not None:
        dron.dibujar_hud(screen, font, SCREEN_W, SCREEN_H)

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
    if ok_pagina == 1 and ultimo_reporte:
        draw_reporte()
        return
    ventana("RESULTADO DE LA MISIÓN", (100, 70, 600, 460))
    txt("MISIÓN EXITOSA", font_big, (90, 230, 120), (UI_W // 2, 160), center=True)
    txt(ultima_mision, font_title, (255, 255, 255), (UI_W // 2, 215), center=True)
    for k, l in enumerate(wrap(ultimo_exito, font, 520)[:2]):
        txt(l, font, (200, 220, 255), (UI_W // 2, 252 + k * 24), center=True)
    txt("RECOMPENSA", font, (255, 255, 0), (UI_W // 2, 315), center=True)
    txt(f"+${ultima_recompensa}M", font_big, (255, 255, 0), (UI_W // 2, 357), center=True)
    txt(f"Fondos totales: ${game['dinero']}M", font_title, (255, 255, 255), (UI_W // 2, 408), center=True)
    if len(game["completadas"]) >= len(MISIONES):
        msg = "¡Completaste todas las misiones! Eres un ingeniero espacial."
    elif ultimo_desbloqueo:
        msg = "¡Misión desbloqueada: " + ", ".join(ultimo_desbloqueo) + "!"
    else:
        msg = ""
    if msg:
        txt(msg, font, (90, 230, 120), (UI_W // 2, 444), center=True)
    if ultimo_reporte:
        button((120, 472, 270, 46), "Ver reporte científico", "reporte")
        button((410, 472, 270, 46), "Volver a la estación", "cerrar")
    else:
        button((300, 472, 200, 46), "Volver a la estación", "cerrar")


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
            elif estado == FINAL:
                final.tecla(event)
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
            elif event.key == pygame.K_h and estado in (ESTACION, PANEL_NAVE, PANEL_MISION, PANEL_TIENDA):
                glosario_volver = estado
                estado = GLOSARIO
            elif event.key == pygame.K_e and estado == ESTACION and cerca:
                estado = INTERACTIVOS[cerca][3]
                if estado == PANEL_MISION:
                    sel_m = mision_sugerida()
                elif estado == PANEL_TIENDA:
                    tienda_cat = categoria_tienda_inicial()
                keys_down.clear()
        elif event.type == pygame.KEYUP:
            keys_down.discard(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = (event.pos[0] - OFF_X, event.pos[1] - OFF_Y)
            if estado == OPCIONES and SLIDER.inflate(30, 34).collidepoint(pos):
                arrastrando_tamano = True
                fijar_altura(pos[0])
            elif estado == DESPEGUE:
                pulsar_despegue()
            elif estado == VIAJE:
                saltar_viaje()
            elif estado == FINAL:
                final.click()
            else:
                for rect, ident in list(clickables):
                    if rect.collidepoint(pos):
                        # comprar y vender ya suenan con compra.wav; los demás botones con opcion.wav
                        if not (isinstance(ident, tuple) and ident[0] in ("comprar", "vender")):
                            sonido.tocar(sonido.OPCION)
                        on_click(ident)
                        break

    # Barra de tamaño del personaje: sigue al mouse mientras está pulsado y guarda al soltar
    if arrastrando_tamano:
        if estado == OPCIONES and pygame.mouse.get_pressed()[0]:
            fijar_altura(mouse_ui[0])
        else:
            arrastrando_tamano = False
            guardar(solo_opciones=True)

    # Fuera de la estación y la Luna el astronauta siempre se ve en su sprite normal y no suenan pasos
    if estado not in (ESTACION, LUNA):
        player.reposo()
        sonido.pasos(False)
    if estado != LUNA:
        sonido.parar(sonido.REPARAR)

    if estado == ESTACION:
        px, py = player.x, player.y
        player.update(station_map)
        sonido.pasos(player.x != px or player.y != py)  # pasos solo si de verdad se movió

    # Música del menú: en bucle hasta salir o empezar a jugar
    if estado in (MENU, OPCIONES):
        sonido.loop(sonido.MENU)
    else:
        sonido.parar(sonido.MENU, 400)

    # Sonido de ambiente: SOLO en la base (con sus ventanas), la Luna y Marte
    if estado in (ESTACION, PANEL_MISION, PANEL_NAVE, PANEL_INFORME, PANEL_COHETE,
                  GLOSARIO, PANEL_TIENDA, PANEL_SIMULA, LUNA):
        sonido.loop(sonido.AMBIENTE)
    else:
        sonido.parar(sonido.AMBIENTE, 400)

    # Final.wav: en bucle desde la cinemática final hasta que se vuelve a la base
    if final_sonando:
        if estado in (FINAL, MISION_OK):
            sonido.loop(sonido.FINAL)
        else:
            sonido.parar(sonido.FINAL, 600)
            final_sonando = False

    sonido.actualizar()  # encadena despegue después de arranque

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
        if anim.terminado and not anim.fallida:
            iniciar_viaje()  # en vez del mensaje de "misión completada"
        else:
            anim.draw()  # si falló, se queda el cartel de MISIÓN FALLIDA hasta pulsar ESPACIO o clic
    elif estado == VIAJE:
        draw_viaje()
    elif estado == LUNA:
        update_luna()
        draw_luna()
    elif estado == FINAL:
        final.update()
        final.draw()
        if final.terminado:
            game["jugador"] = final.jugador
            guardar()
            final = None
            keys_down.clear()
            estado = MISION_OK
    elif estado == MISION_OK:
        draw_mision_ok()
    else:
        draw_world()
        if estado in (PANEL_MISION, PANEL_NAVE, PANEL_INFORME, PANEL_COHETE, GLOSARIO, PANEL_TIENDA, PANEL_SIMULA):
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            paneles = {
                PANEL_MISION: draw_panel_mision,
                PANEL_NAVE: draw_panel_nave,
                PANEL_INFORME: draw_informe,
                PANEL_COHETE: draw_panel_cohete,
                GLOSARIO: draw_glosario,
                PANEL_TIENDA: draw_panel_tienda,
                PANEL_SIMULA: draw_panel_simula,
            }
            paneles[estado]()

    screen.blit(ui, (OFF_X, OFF_Y))
    draw_toast()
    pygame.display.flip()
    clock.tick(60)

menu_bg.release()
guardar(solo_opciones=True)
pygame.quit()
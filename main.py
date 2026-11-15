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
pygame.display.set_caption("Space Mission Simulator - Estación Espacial")
clock = pygame.time.Clock()

# Los menús y paneles se dibujan en un lienzo de 800x600 centrado en pantalla
UI_W, UI_H = 800, 600
OFF_X, OFF_Y = (SCREEN_W - UI_W) // 2, (SCREEN_H - UI_H) // 2
ui = pygame.Surface((UI_W, UI_H), pygame.SRCALPHA)

font_s = pygame.font.SysFont(None, 20)
font = pygame.font.SysFont(None, 26)
font_title = pygame.font.SysFont(None, 40)
font_big = pygame.font.SysFont(None, 64)

BG = (15, 15, 30)
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.json")
menu_bg = FondoMenu("planeta rotando.mp4", (SCREEN_W, SCREEN_H), BG)

# Estados
MENU, OPCIONES, ESTACION, PANEL_MISION, PANEL_NAVE = range(5)
estado = MENU

# ======================================================================
#  DATOS DEL JUEGO
# ======================================================================
# (nombre, valor, costo en millones $)
MOTORES = [("Químico", 50, 40), ("Iónico", 70, 90), ("Nuclear térmico", 100, 180)]
CARGAS = [("Satélite", 20, 30), ("Sonda científica", 35, 60), ("Módulo habitable", 60, 140)]
BLINDAJES = [("Básico", 10, 10), ("Térmico", 30, 40), ("Reforzado", 50, 90)]
CATEGORIAS = [("Motor", "motor", MOTORES), ("Carga útil", "carga", CARGAS),
              ("Blindaje", "blind", BLINDAJES)]

MISIONES = [
    {"nombre": "Earth Watcher Alpha", "tipo": "Observación terrestre", "orbita": "LEO (500 km)",
     "presupuesto": 150, "empuje": 40, "carga": 20, "prot": 0,
     "desc": "Satélite para vigilar el clima, los océanos y el cambio climático."},
    {"nombre": "Comsat Horizonte", "tipo": "Comunicaciones", "orbita": "GEO (35,786 km)",
     "presupuesto": 320, "empuje": 70, "carga": 20, "prot": 10,
     "desc": "Satélite geoestacionario de telecomunicaciones para toda una región."},
    {"nombre": "Selene Pathfinder", "tipo": "Exploración lunar", "orbita": "Órbita lunar",
     "presupuesto": 400, "empuje": 70, "carga": 35, "prot": 30,
     "desc": "Sonda que mapeará la superficie de la Luna y buscará hielo en los polos."},
    {"nombre": "Estación Relevo", "tipo": "Reabastecimiento", "orbita": "LEO (400 km)",
     "presupuesto": 250, "empuje": 50, "carga": 60, "prot": 10,
     "desc": "Módulo de carga y relevo de tripulación para la estación orbital."},
    {"nombre": "Ares Explorer", "tipo": "Exploración de Marte", "orbita": "Marte",
     "presupuesto": 800, "empuje": 100, "carga": 35, "prot": 50,
     "desc": "Misión de larga duración para analizar la atmósfera y el suelo marciano."},
]

cfg = {"zoom_extra": 1.0, "velocidad": 3}
game = {"mision": None, "nave": {"motor": 0, "carga": 0, "blind": 0}}
player_start = (600, 450)

def nave_stats(n):
    m, c, b = MOTORES[n["motor"]], CARGAS[n["carga"]], BLINDAJES[n["blind"]]
    return {"empuje": m[1], "carga": c[1], "prot": b[1], "costo": m[2] + c[2] + b[2]}

def compatibilidad(mis, st):
    return [
        (f"Empuje {st['empuje']} / {mis['empuje']}", st["empuje"] >= mis["empuje"]),
        (f"Carga útil {st['carga']} / {mis['carga']}", st["carga"] >= mis["carga"]),
        (f"Protección {st['prot']} / {mis['prot']}", st["prot"] >= mis["prot"]),
        (f"Costo ${st['costo']}M / ${mis['presupuesto']}M", st["costo"] <= mis["presupuesto"]),
    ]

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
    """Guarda opciones y, salvo que solo_opciones=True, también la partida."""
    data = {"opciones": cfg, "partida": None}
    if solo_opciones:                      # conserva la partida que ya existía
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

# Zonas interactivas: (rect del objeto, rect de zona de acercamiento, texto, panel)
OBJ_NAVE = pygame.Rect(1488, 200, 720, 445)
OBJ_PC = pygame.Rect(130, 570, 320, 160)
INTERACTIVOS = {
    "nave": (OBJ_NAVE, OBJ_NAVE.inflate(160, 160), "Modificar la nave", PANEL_NAVE),
    "pc": (OBJ_PC, OBJ_PC.inflate(140, 140), "Usar la computadora de misiones", PANEL_MISION),
}
cerca = None   # clave del objeto interactivo cercano

def clamp_camera(c, view_size, map_size):
    if view_size >= map_size:
        return -(view_size - map_size) // 2
    return max(0, min(c, map_size - view_size))

def apply_zoom():
    """Calcula el zoom para que el mapa se ajuste a la pantalla."""
    global ZOOM, VIEW_W, VIEW_H, view
    fx, fy = SCREEN_W / station_map.width, SCREEN_H / station_map.height
    ZOOM = max(fx, fy) * cfg["zoom_extra"]
    VIEW_W, VIEW_H = int(SCREEN_W / ZOOM), int(SCREEN_H / ZOOM)
    view = pygame.Surface((VIEW_W, VIEW_H))

cargar_opciones()
apply_zoom()
player_mod.movement_speed = cfg["velocidad"]

# ======================================================================
#  AYUDAS DE INTERFAZ
# ======================================================================
clickables = []
mouse_ui = (0, 0)
aviso = ""
sel_m = 0

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
    txt(label, font, fg, r.center, center=True)
    if enabled:
        clickables.append((r, ident))

def ventana(titulo, rect=(80, 60, 640, 480)):
    r = pygame.Rect(rect)
    pygame.draw.rect(ui, (14, 22, 55), r, border_radius=10)
    pygame.draw.rect(ui, (0, 200, 255), r, 3, border_radius=10)
    txt(titulo, font_title, (255, 255, 0), (r.centerx, r.y + 32), center=True)
    pygame.draw.line(ui, (0, 200, 255), (r.x + 20, r.y + 58), (r.right - 20, r.y + 58), 1)
    return r

def barra(x, y, w, valor, maximo, color, etiqueta):
    txt(etiqueta, font_s, (200, 200, 200), (x, y))
    pygame.draw.rect(ui, (40, 45, 70), (x + 90, y, w, 14), border_radius=4)
    pygame.draw.rect(ui, color, (x + 90, y, int(w * min(valor, maximo) / maximo), 14), border_radius=4)
    txt(str(valor), font_s, (255, 255, 255), (x + 100 + w, y))

# ======================================================================
#  PANTALLAS
# ======================================================================
def draw_menu():
    txt("SPACE MISSION", font_big, (0, 255, 255), (UI_W // 2, 110), center=True)
    txt("SIMULATOR", font_big, (255, 255, 0), (UI_W // 2, 170), center=True)
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

    # ¿Hay algún objeto interactivo cerca?
    cerca = None
    prect = player.rect()
    for clave, (obj, zona, _, _) in INTERACTIVOS.items():
        if prect.colliderect(zona):
            cerca = clave
            break

    view.fill(BG)
    station_map.draw(view, camera)
    if cerca:   # resalta el objeto con el que se puede interactuar
        obj = INTERACTIVOS[cerca][0]
        pygame.draw.rect(view, (255, 255, 0), obj.move(-cam_x, -cam_y), 4)
    for s in sprites:
        s.draw(view, camera)
    if pygame.K_F1 in keys_down:
        station_map.draw_debug(view, camera)
    screen.blit(pygame.transform.smoothscale(view, (SCREEN_W, SCREEN_H)), (0, 0))

    # HUD
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

def draw_panel_mision():
    ventana("TERMINAL DE MISIONES")
    for i, m in enumerate(MISIONES):
        etiqueta = m["nombre"] + (" *" if game["mision"] == i else "")
        button((100, 140 + i * 58, 240, 48), etiqueta, ("mision", i), selected=(sel_m == i))
    m = MISIONES[sel_m]
    x = 365
    txt(m["nombre"], font, (255, 255, 0), (x, 135))
    txt(f"Tipo: {m['tipo']}", font_s, (200, 220, 255), (x, 165))
    txt(f"Órbita: {m['orbita']}", font_s, (200, 220, 255), (x, 187))
    txt(f"Presupuesto: ${m['presupuesto']}M", font_s, (200, 220, 255), (x, 209))
    for k, linea in enumerate(wrap(m["desc"], font_s, 330)):
        txt(linea, font_s, (170, 170, 190), (x, 238 + k * 20))
    txt("Compatibilidad con tu nave:", font_s, (255, 255, 255), (x, 305))
    st = nave_stats(game["nave"])
    todo_ok = True
    for k, (linea, ok) in enumerate(compatibilidad(m, st)):
        todo_ok &= ok
        txt(("[OK] " if ok else "[X]  ") + linea, font_s,
            (90, 230, 120) if ok else (255, 100, 100), (x, 330 + k * 22))
    if not todo_ok:
        txt("Modifica la nave en el hangar para cumplirla.", font_s, (255, 190, 90), (x, 425))
    button((365, 455, 200, 46), "Aceptar misión", "aceptar")
    button((580, 455, 120, 46), "Cerrar", "cerrar")
    if aviso:
        txt(aviso, font_s, (90, 230, 120), (100, 480))

def draw_panel_nave():
    ventana("TALLER DE LA NAVE")
    for i, (nombre, clave, lista) in enumerate(CATEGORIAS):
        y = 130 + i * 62
        txt(nombre, font, (255, 255, 255), (110, y + 12))
        button((260, y, 40, 44), "<", ("nave", clave, -1, len(lista)))
        pygame.draw.rect(ui, (20, 30, 70), (305, y, 250, 44), border_radius=6)
        txt(lista[game["nave"][clave]][0], font, (255, 255, 0), (430, y + 22), center=True)
        button((560, y, 40, 44), ">", ("nave", clave, 1, len(lista)))
    st = nave_stats(game["nave"])
    barra(110, 330, 280, st["empuje"], 100, (255, 150, 40), "Empuje")
    barra(110, 358, 280, st["carga"], 60, (80, 200, 255), "Carga útil")
    barra(110, 386, 280, st["prot"], 50, (120, 230, 120), "Protección")
    txt(f"Costo total: ${st['costo']}M", font, (255, 255, 255), (110, 420))
    if game["mision"] is not None:
        mis = MISIONES[game["mision"]]
        ok = all(o for _, o in compatibilidad(mis, st))
        txt(f"Misión activa: {mis['nombre']} -> " + ("COMPATIBLE" if ok else "NO compatible"),
            font_s, (90, 230, 120) if ok else (255, 100, 100), (110, 452))
    else:
        txt("Sin misión activa: elige una en la computadora.", font_s, (200, 200, 200), (110, 452))
    button((570, 470, 130, 46), "Cerrar", "cerrar")

# ======================================================================
#  ACCIONES
# ======================================================================
def iniciar(continuar):
    global estado
    keys_down.clear()
    game["mision"], game["nave"] = None, {"motor": 0, "carga": 0, "blind": 0}
    player.x, player.y = player_start
    if continuar:
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                p = json.load(f)["partida"]
            player.x, player.y = p["x"], p["y"]
            game["mision"], game["nave"] = p["mision"], p["nave"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
    estado = ESTACION

def on_click(ident):
    global estado, running, sel_m, aviso
    if isinstance(ident, tuple):
        if ident[0] == "mision":
            sel_m, aviso = ident[1], ""
        elif ident[0] == "nave":
            _, clave, delta, n = ident
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
    elif ident == "cerrar":
        estado = ESTACION
        aviso = ""

# ======================================================================
#  BUCLE PRINCIPAL
# ======================================================================
running = True
while running:
    if estado == MENU:
        OFF_X = SCREEN_W - UI_W - 40
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
                else:                       # cerrar panel
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

    # ---- Dibujo ----
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
        if estado in (PANEL_MISION, PANEL_NAVE):
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            (draw_panel_mision if estado == PANEL_MISION else draw_panel_nave)()

    screen.blit(ui, (OFF_X, OFF_Y))
    pygame.display.flip()
    clock.tick(60)

menu_bg.release()
guardar(solo_opciones=True)
pygame.quit()

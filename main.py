import pygame
from sprite import sprites
from player import Player
from input import keys_down
from map import ImageMap

# Inicialización de Pygame
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)   # pantalla completa
SCREEN_W, SCREEN_H = screen.get_size()
# Los menús están diseñados para 800x600: se dibujan ahí y se centran en la pantalla
UI_W, UI_H = 800, 600
OFF_X, OFF_Y = (SCREEN_W - UI_W) // 2, (SCREEN_H - UI_H) // 2
ui = pygame.Surface((UI_W, UI_H))
pygame.display.set_caption("Space Mission Simulator - Estación Espacial")
clock = pygame.time.Clock()

# --- ESTADOS DEL JUEGO ---
ESTADO_MENU = 1
ESTADO_SELECCION = 2
ESTADO_ESTACION = 3
estado_actual = ESTADO_MENU

# Fuentes
font = pygame.font.SysFont(None, 24)
font_title = pygame.font.SysFont(None, 36)

# --- MAPA DE LA ESTACIÓN (imagen + colisiones) ---
# Rectángulos (x, y, ancho, alto) sobre la imagen de 2400x1216.
# Mantén F1 dentro del juego para verlos en rojo y ajustarlos.
SOLIDOS = [
    # Bordes exteriores
    (0, 0, 2400, 45), (0, 0, 40, 1216), (2376, 0, 30, 1216), (0, 1190, 2400, 30),
    # Sala de operaciones
    (0, 0, 1210, 170),                  # pared superior + pizarras
    (1150, 0, 75, 880),                 # pared entre salas
    (40, 150, 100, 420),                # racks de computadoras
    (130, 570, 320, 160),               # escritorios
    (790, 570, 275, 190),               # mesa de planos
    (0, 850, 530, 32), (670, 850, 480, 32),      # pared inferior (hueco = puerta)
    # Hangar
    (1210, 0, 1190, 135),               # pared superior
    (1488, 200, 720, 445),              # transbordador
    (2248, 150, 90, 500),               # cohete
    (1225, 215, 90, 360),               # brazos robóticos
    (1255, 725, 295, 110),              # escritorios
    (2020, 725, 290, 115),              # mesa de mapa
    (1210, 868, 540, 14), (1852, 868, 525, 14),  # pared inferior (hueco = puerta)
]

station_map = ImageMap("images/mapa_completo.png", SOLIDOS)

# --- AJUSTE AUTOMÁTICO DEL MAPA A LA PANTALLA ---
# "cover"   : el mapa llena toda la pantalla (sin barras negras), la cámara se mueve
# "contain" : se ve el mapa completo, con barras oscuras si sobra espacio
MODO_AJUSTE = "cover"
ZOOM_EXTRA = 1.0     # >1 acerca la cámara, <1 la aleja
fx, fy = SCREEN_W / station_map.width, SCREEN_H / station_map.height
ZOOM = (max(fx, fy) if MODO_AJUSTE == "cover" else min(fx, fy)) * ZOOM_EXTRA
VIEW_W, VIEW_H = int(SCREEN_W / ZOOM), int(SCREEN_H / ZOOM)
view = pygame.Surface((VIEW_W, VIEW_H))

def clamp_camera(c, view_size, map_size):
    if view_size >= map_size:            # sobra espacio: centrar el mapa
        return -(view_size - map_size) // 2
    return max(0, min(c, map_size - view_size))

# Jugador: aparece en el centro de la sala de operaciones
player = Player("images/player.png", 600, 450)

# Bucle principal del juego
running = True
while running:
    # 1. Eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            keys_down.add(event.key)
            if event.key == pygame.K_ESCAPE:
                if estado_actual == ESTADO_MENU:
                    running = False          # ESC en el menú = salir del juego
                elif estado_actual == ESTADO_SELECCION:
                    estado_actual = ESTADO_MENU
                elif estado_actual == ESTADO_ESTACION:
                    estado_actual = ESTADO_SELECCION

        elif event.type == pygame.KEYUP:
            keys_down.discard(event.key)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos[0] - OFF_X, event.pos[1] - OFF_Y
            if estado_actual == ESTADO_MENU:
                if 250 <= x <= 550 and 350 <= y <= 430:
                    estado_actual = ESTADO_SELECCION
            elif estado_actual == ESTADO_SELECCION:
                if 100 <= x <= 700 and 180 <= y <= 280:
                    print("¡Misión confirmada! Entrando a la estación espacial...")
                    estado_actual = ESTADO_ESTACION

    # 2. Lógica
    if estado_actual == ESTADO_ESTACION:
        player.update(station_map)

    # 3. Dibujo
    screen.fill((15, 15, 30))

    if estado_actual != ESTADO_ESTACION:
        ui.fill((15, 15, 30))
    if estado_actual == ESTADO_MENU:
        title = font_title.render("SPACE MISSION SIMULATOR", True, (0, 255, 255))
        ui.blit(title, (220, 180))
        pygame.draw.rect(ui, (0, 50, 150), (250, 350, 300, 60), border_radius=6)
        pygame.draw.rect(ui, (255, 255, 0), (250, 350, 300, 60), 2, border_radius=6)
        btn_text = font.render("INICIAR SIMULACIÓN", True, (255, 255, 255))
        ui.blit(btn_text, (305, 368))

    elif estado_actual == ESTADO_SELECCION:
        header = font_title.render("SELECCIONA UN CONTRATO DE MISIÓN", True, (255, 255, 255))
        ui.blit(header, (170, 80))
        pygame.draw.rect(ui, (20, 30, 70), (100, 180, 600, 100), border_radius=6)
        pygame.draw.rect(ui, (0, 200, 255), (100, 180, 600, 100), 2, border_radius=6)
        t1 = font.render("Earth Watcher Alpha (Haz clic para aceptar)", True, (255, 255, 0))
        t2 = font.render("Órbita: LEO (500 km) | Presupuesto: $150M", True, (200, 200, 200))
        ui.blit(t1, (120, 200))
        ui.blit(t2, (120, 235))

    if estado_actual != ESTADO_ESTACION:
        screen.blit(ui, (OFF_X, OFF_Y))

    elif estado_actual == ESTADO_ESTACION:
        # Cámara centrada en el jugador, limitada a los bordes del mapa
        cam_x = int(player.x) + player.image.get_width() // 2 - VIEW_W // 2
        cam_y = int(player.y) + player.image.get_height() // 2 - VIEW_H // 2
        cam_x = clamp_camera(cam_x, VIEW_W, station_map.width)
        cam_y = clamp_camera(cam_y, VIEW_H, station_map.height)
        camera = (cam_x, cam_y)

        # Dibujamos el mundo en una superficie grande y luego la reducimos
        view.fill((15, 15, 30))
        station_map.draw(view, camera)
        for s in sprites:          # incluye al jugador
            s.draw(view, camera)
        if pygame.K_F1 in keys_down:
            station_map.draw_debug(view, camera)
        screen.blit(pygame.transform.smoothscale(view, (SCREEN_W, SCREEN_H)), (0, 0))

        info = font.render("W A S D para caminar | F1: ver colisiones | ESC: volver",
                           True, (255, 255, 255))
        pygame.draw.rect(screen, (0, 0, 0), (10, 10, info.get_width() + 20, 30))
        screen.blit(info, (20, 16))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

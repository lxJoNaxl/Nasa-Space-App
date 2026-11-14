import pygame
from sprite import sprites, Sprite
from player import Player
from input import keys_down
from map import Map, TileKind

# Inicialización de Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Space Mission Simulator - Estación Espacial")
clock = pygame.time.Clock()

# --- ESTADOS DEL JUEGO ---
ESTADO_MENU = 1
ESTADO_SELECCION = 2
ESTADO_ESTACION = 3  # <- Aquí el personaje se moverá libremente
estado_actual = ESTADO_MENU

# Fuentes
font = pygame.font.SysFont(None, 24)
font_title = pygame.font.SysFont(None, 36)

# --- CONFIGURACIÓN DE LOS TILES Y EL MAPA DE LA ESTACIÓN ---
tile_kinds = [
    TileKind("dirt", "images/dirt.png", False),     # 0: Tierra / Suelo
    TileKind("grass", "images/grass.png", False),  # 1: Pasto / Consola
    TileKind("water", "images/water.png", False),  # 2: Agua / Vacío
    TileKind("wood", "images/wood.png", True)      # 3: Madera / Pared
]

# Creamos el mapa de la estación (puedes crear un archivo 'station.map' o usar start.map)
# Asegúrate de tener un archivo de mapa en la carpeta 'maps/'
try:
    station_map = Map("maps/start.map", tile_kinds, 32)
except:
    station_map = None

# Inicializamos al jugador (lo ubicamos en el centro de la estación)
player = Player("images/player.png", 32 * 11, 32 * 7)

# Bucle principal del juego
running = True
while running:
    # 1. Gestión de Eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            keys_down.add(event.key)
            
            # Acciones según la tecla ESC en los menús
            if event.key == pygame.K_ESCAPE:
                if estado_actual == ESTADO_SELECCION:
                    estado_actual = ESTADO_MENU
                elif estado_actual == ESTADO_ESTACION:
                    estado_actual = ESTADO_SELECCION

        elif event.type == pygame.KEYUP:
            keys_down.remove(event.key)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            
            # --- CLICS EN EL MENÚ PRINCIPAL ---
            if estado_actual == ESTADO_MENU:
                # Botón "Iniciar"
                if 250 <= x <= 550 and 350 <= y <= 430:
                    estado_actual = ESTADO_SELECCION
                    
            # --- CLICS EN LA SELECCIÓN DE MISIÓN ---
            elif estado_actual == ESTADO_SELECCION:
                # Clic en la Tarjeta de Misión (Ej: Earth Watcher Alpha)
                if 100 <= x <= 700 and 180 <= y <= 280:
                    print("¡Misión confirmada! Entrando a la estación espacial...")
                    estado_actual = ESTADO_ESTACION # Cambiamos al estado donde se mueve el personaje

    # 2. Actualización de Lógica según el Estado
    if estado_actual == ESTADO_ESTACION:
        player.update() # Mueve al personaje con WASD usando input.py y player.py[cite: 12, 15]

    # 3. Renderizado de Gráficos en Pantalla
    screen.fill((15, 15, 30)) # Fondo espacial oscuro por defecto

    if estado_actual == ESTADO_MENU:
        # Dibujar Menú Principal
        title = font_title.render("SPACE MISSION SIMULATOR", True, (0, 255, 255))
        screen.blit(title, (220, 180))
        
        # Botón de inicio
        pygame.draw.rect(screen, (0, 50, 150), (250, 350, 300, 60), border_radius=6)
        pygame.draw.rect(screen, (255, 255, 0), (250, 350, 300, 60), 2, border_radius=6)
        btn_text = font.render("INICIAR SIMULACIÓN", True, (255, 255, 255))
        screen.blit(btn_text, (305, 368))

    elif estado_actual == ESTADO_SELECCION:
        # Dibujar Pantalla de Contratos / Misiones
        header = font_title.render("SELECCIONA UN CONTRATO DE MISIÓN", True, (255, 255, 255))
        screen.blit(header, (170, 80))
        
        # Tarjeta de misión interactiva
        pygame.draw.rect(screen, (20, 30, 70), (100, 180, 600, 100), border_radius=6)
        pygame.draw.rect(screen, (0, 200, 255), (100, 180, 600, 100), 2, border_radius=6)
        
        t1 = font.render("🚀 Earth Watcher Alpha (Haz clic para aceptar)", True, (255, 255, 0))
        t2 = font.render("Órbita: LEO (500 km) | Presupuesto: $150M", True, (200, 200, 200))
        screen.blit(t1, (120, 200))
        screen.blit(t2, (120, 235))

    elif estado_actual == ESTADO_ESTACION:
        # --- DIBUJAR EL ESPACIO CONFIGURABLE (ESTACIÓN ESPACIAL) ---
        if station_map:
            station_map.draw(screen) # Dibuja los tiles del piso/paredes[cite: 14]
            
        # Dibuja los sprites estáticos adicionales (como consolas, equipos, etc.)
        for s in sprites:
            s.draw(screen)
            
        # Dibuja al personaje controlable encima
        player.draw(screen)
        
        # Indicador en pantalla
        info = font.render("Usa W, A, S, D para caminar por el laboratorio. (ESC para volver)", True, (255, 255, 255))
        screen.blit(info, (20, 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
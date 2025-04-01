import pygame
import sys
import math
import random
import numpy as np

# Parámetros del jugador
player_speed = 0.05
player_x = 1.5
player_y = 1.5
player_angle = 0.0
player_lives = 3

# Pre-inicialización del mezclador para sonido monofónico
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init(44100, -16, 1, 512)
        print("Mixer manualmente inicializado.")
    except pygame.error as e:
        print(f"Error al inicializar el mezclador: {e}")
        sys.exit("No se pudo inicializar el mezclador.")
else:
    print("Mixer ya está inicializado.")

# =====================================================
# A. CONFIGURACIÓN INICIAL Y CONSTANTES
# =====================================================

WIDTH, HEIGHT = 800, 600
FOV = math.pi / 3           # 60° de campo de visión
HALF_FOV = FOV / 2
NUM_RAYS = 400              # Número de rayos a proyectar
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 20
SCALE = WIDTH / NUM_RAYS

# Colores
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Parámetros del laberinto (debe ser impar para generar pasillos)
MAZE_WIDTH = 91
MAZE_HEIGHT = 81

CALIZ_SIZE = 0.8 / 3.0  # Un tercio del tamaño base del enemigo (se asume 0.8)
CALIZ_COLOR = (0, 0, 255)  # Azul (puedes ajustar el tono si lo deseas)

def win_screen(screen):
    """
    Muestra la pantalla de victoria.
    
    Se muestra un mensaje en dos líneas:
      "Saliste del universo de ENTropia,"
      "felicidades, supongo..."
      
    Y las opciones:
      "Presiona Esc para salir"
      "o Enter para la pantalla de inicio"
      
    El texto se centra en pantalla para evitar que se corte.
    """
    # Usamos una fuente adecuada para que todo el texto quepa sin problemas
    font = pygame.font.SysFont("Arial", 30)
    text_color = (255, 255, 255)
    
    win_lines = [
        "Saliste del universo de ENTropia,",
        "felicidades, supongo..."
    ]
    option_lines = [
        "Presiona Esc para salir",
        "o Enter para la pantalla de inicio"
    ]
    
    # Calcula el espaciado total para centrar verticalmente
    line_height = font.get_linesize()
    total_lines = len(win_lines) + len(option_lines)
    total_height = total_lines * line_height + 20  # 20 píxeles de margen extra entre grupos
    start_y = (screen.get_height() - total_height) // 2

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_RETURN:
                    return  # Al pulsar Enter, se regresa (por ejemplo, para volver a la pantalla de inicio)
        
        # Rellena la pantalla con negro
        screen.fill((0, 0, 0))
        
        # Dibuja las líneas de mensaje de victoria
        for i, line in enumerate(win_lines):
            surface = font.render(line, True, text_color)
            rect = surface.get_rect(center=(screen.get_width() // 2, start_y + i * line_height))
            screen.blit(surface, rect)
        
        # Desplaza hacia abajo para dibujar las opciones de control
        offset = len(win_lines) * line_height + 20
        for i, line in enumerate(option_lines):
            surface = font.render(line, True, text_color)
            rect = surface.get_rect(center=(screen.get_width() // 2, start_y + offset + i * line_height))
            screen.blit(surface, rect)
        
        pygame.display.flip()
        pygame.time.delay(100)


def place_caliz():
    """
    Coloca el objeto 'caliz' en una posición aleatoria del mapa.
    Se selecciona una celda aleatoria; si esa celda no es un muro,
    se retorna un diccionario con las coordenadas centradas en la celda.
    """
    while True:
        celda_x = random.randint(0, MAP_WIDTH - 1)
        celda_y = random.randint(0, MAP_HEIGHT - 1)
        if game_map[celda_y][celda_x] != "1":  # Suponiendo que "1" es muro
            return {"x": celda_x + 0.5, "y": celda_y + 0.5}

def draw_caliz(screen, caliz, scale=6):
    """
    Dibuja el objeto 'caliz' en la pantalla.
    
    Se representa como un cuadrado azul centrado en (caliz["x"], caliz["y"]).
    El tamaño en píxeles se calcula multiplicando CALIZ_SIZE por el factor scale.
    """
    # Convierte las coordenadas del mundo a píxeles
    caliz_screen_x = int(caliz["x"] * scale)
    caliz_screen_y = int(caliz["y"] * scale)
    # Calcula el tamaño en píxeles
    caliz_tamaño = int(CALIZ_SIZE * scale)
    # Crea el rectángulo centrado
    rect_caliz = pygame.Rect(
        caliz_screen_x - caliz_tamaño // 2,
        caliz_screen_y - caliz_tamaño // 2,
        caliz_tamaño,
        caliz_tamaño
    )
    pygame.draw.rect(screen, CALIZ_COLOR, rect_caliz)

def game_over_screen(screen):
    """
    Muestra la pantalla de Game Over.
    Cuando se pulsa Esc, el juego se cierra; al pulsar Enter se retorna para reiniciar.
    Se muestran dos líneas para el mensaje de Game Over y dos líneas con las opciones,
    de modo que todo el texto quepa en la pantalla.
    """
    # Usamos una fuente suficientemente pequeña para que tepa quepan ambas líneas
    font = pygame.font.SysFont("Arial", 30)
    text_color = (255, 255, 255)
    
    # Dividimos el mensaje en dos líneas y también las opciones en dos líneas
    game_over_lines = [
        "El universo de ENTropia te ha absorbido,",
        "ahora eres parte de él"
    ]
    option_lines = [
        "Presiona Esc para salir",
        "o Enter para la pantalla de inicio"
    ]
    
    # Calculamos el espaciado vertical total
    line_height = font.get_linesize()
    total_lines = len(game_over_lines) + len(option_lines)
    total_height = total_lines * line_height + 20  # 20 píxeles de margen entre grupos
    
    start_y = (screen.get_height() - total_height) // 2
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_RETURN:
                    return  # Al pulsar Enter se termina esta pantalla
        
        screen.fill((0, 0, 0))
        
        # Renderizamos las líneas del mensaje de Game Over
        for i, line in enumerate(game_over_lines):
            surface = font.render(line, True, text_color)
            rect = surface.get_rect(center=(screen.get_width() // 2, start_y + i * line_height))
            screen.blit(surface, rect)
        
        # Renderizamos las líneas con las opciones, con un offset adicional
        offset = len(game_over_lines) * line_height + 20
        for i, line in enumerate(option_lines):
            surface = font.render(line, True, text_color)
            rect = surface.get_rect(center=(screen.get_width() // 2, start_y + offset + i * line_height))
            screen.blit(surface, rect)
        
        pygame.display.flip()
        pygame.time.delay(100)



def draw_lives(screen, lives, square_size=20, gap=10, margin=10):
    """
    Dibuja cuadrados rojos en la esquina superior derecha para representar las vidas.
    
    Parámetros:
      screen: superficie en la que se dibuja.
      lives: número de vidas actuales.
      square_size: tamaño (ancho y alto) de cada cuadrado.
      gap: espacio entre cada cuadrado.
      margin: margen desde el borde superior y derecho.
    """
    # La posición inicial se calcula desde la esquina superior derecha.
    for i in range(lives):
        # Se dibujan los cuadrados de derecha a izquierda.
        x = screen.get_width() - margin - (square_size + gap) * (i + 1) + gap
        y = margin
        pygame.draw.rect(screen, RED, (x, y, square_size, square_size))


def transition_effect(screen, duration_ms=4000):
    """
    Realiza un efecto de transición en la pantalla con fade-out y fade-in, 
    reduciendo y luego restaurando el volumen de la música al mismo tiempo.
    duration_ms: duración en milisegundos de cada fase (fade-out y fade-in)
    """
    steps = 60  # Puedes aumentar este valor para un efecto más suave.
    delay = duration_ms / steps / 1000.0  # Tiempo entre pasos (en segundos)
    original_volume = pygame.mixer.music.get_volume()
    
    # Captura de la pantalla actual (por ejemplo, la pantalla de inicio)
    snapshot = screen.copy()
    
    # FADE-OUT: aumentar gradualmente la opacidad del overlay negro
    for i in range(steps):
        alpha = int(i / steps * 255)
        new_volume = original_volume * (1 - i / steps)
        pygame.mixer.music.set_volume(new_volume)
        
        # Primera fase: dibuja la imagen actual (capturada)
        screen.blit(snapshot, (0, 0))
        
        # Crea un overlay negro con canal alpha
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        
        pygame.display.flip()
        pygame.time.delay(int(delay * 1000))
    
    # Aquí la pantalla está casi completamente negra y el audio casi silenciado.
    # Podrías agregar un breve "hold" si lo consideras necesario.
    
    # FADE-IN: suponiendo que en este punto se va a mostrar la escena del juego.
    # Preparamos la nueva escena. Se recomienda capturarla o, si se va a redibujar,
    # realizar el dibujo correspondiente antes del efecto.
    # Para este ejemplo, simularemos un fondo gris (puedes sustituirlo por tu escena).
    new_scene = pygame.Surface(screen.get_size())
    new_scene.fill((50, 50, 50))  # Fondo gris de ejemplo
    
    for i in range(steps):
        alpha = int((1 - i / steps) * 255)
        new_volume = original_volume * (i / steps)
        pygame.mixer.music.set_volume(new_volume)
        
        # Dibuja la nueva escena
        screen.blit(new_scene, (0, 0))
        # Crea nuevamente el overlay, pero ahora con opacidad decreciente
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        
        pygame.display.flip()
        pygame.time.delay(int(delay * 1000))
    
    # Finalmente, se restablece el volumen original
    pygame.mixer.music.set_volume(original_volume)

def play_background_music():
    # Asegurarse de que el mezclador esté inicializado
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    try:
        # Carga el archivo de audio (asegúrate de que el nombre y la extensión coincidan)
        pygame.mixer.music.load("Metamorphosis One.mp3")
        # Reproduce la música en bucle (-1 indica reproducción infinita)
        pygame.mixer.music.play(-1)
        # Opcional: ajustar el volumen (valor entre 0.0 y 1.0)
        pygame.mixer.music.set_volume(0.5)
    except Exception as e:
        print(f"Error al reproducir la música: {e}")


def start_screen(screen):
    font_title = pygame.font.SysFont("Arial", 60)
    font_instructions = pygame.font.SysFont("Arial", 30)
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                # Puedes especificar que solo se avance con ENTER o cualquier otra tecla:
                if event.key == pygame.K_RETURN:
                    waiting = False

        # Rellena la pantalla con un color de fondo (por ejemplo, negro)
        screen.fill(BLACK)

        # Renderiza el título y las instrucciones
        title_text = font_title.render("ENTropia 3D", True, WHITE)
        instructions_text = font_instructions.render("KXdw wvd2B 3D1 LH7JRO SRTYFFHW p", True, WHITE)

        # Centra el título y el mensaje en la pantalla
        screen.blit(title_text, ((WIDTH - title_text.get_width()) // 2, HEIGHT // 3))
        screen.blit(instructions_text, ((WIDTH - instructions_text.get_width()) // 2, HEIGHT // 2))

        # Actualiza la pantalla
        pygame.display.flip()


def generate_maze(width, height):
    """
    Genera un laberinto aleatorio usando backtracking recursivo.
    Cada celda es '1' (muro) o ' ' (pasillo).
    """
    maze = [['1' for _ in range(width)] for _ in range(height)]
    
    def carve(x, y):
        maze[y][x] = ' '  # Marca la celda actual como pasillo
        directions = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(directions)
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 1 <= nx < width - 1 and 1 <= ny < height - 1 and maze[ny][nx] == '1':
                maze[y + dy // 2][x + dx // 2] = ' '  # Abre el muro intermedio
                carve(nx, ny)
    
    carve(1, 1)
    return ["".join(row) for row in maze]

game_map = generate_maze(MAZE_WIDTH, MAZE_HEIGHT)
MAP_WIDTH = len(game_map[0])
MAP_HEIGHT = len(game_map)

# Se utiliza un z-buffer global para almacenar la distancia de cada rayo.
z_buffer = [0.0 for _ in range(NUM_RAYS)]

# Variable para controlar la visualización del minimapa.
show_map = False

def draw_minimap(screen, scale=6):
    """
    Dibuja un minimapa en la esquina superior izquierda mostrando el laberinto,
    la posición del jugador y otros objetos a escala.
    """
    if not show_map:
        return
    
    for y, row in enumerate(game_map):
        for x, cell in enumerate(row):
            color = GRAY if cell == '1' else WHITE
            rect = pygame.Rect(x * scale, y * scale, scale, scale)
            pygame.draw.rect(screen, color, rect)
    
    player_pos = (int(player_x * scale), int(player_y * scale))
    pygame.draw.circle(screen, RED, player_pos, 3)

# =====================================================
# B. MANEJO DE ENEMIGOS
# =====================================================

def spawn_enemy():
    """
    Genera un enemigo de forma aleatoria en el mapa.
    El enemigo se genera en una celda abierta y se posiciona en el centro de ella.
    Se verifica que esté en frente del jugador.
    """
    attempts = 0
    while attempts < 100:
        rx = random.randint(1, MAP_WIDTH - 2)
        ry = random.randint(1, MAP_HEIGHT - 2)
        if game_map[ry][rx] == ' ':
            ex = rx + 0.5
            ey = ry + 0.5
            dx = ex - player_x
            dy = ey - player_y
            angle_to_candidate = math.atan2(dy, dx)
            angle_diff = angle_to_candidate - player_angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            if abs(angle_diff) < math.pi / 2:  # Debe estar en frente del jugador
                return {"x": ex, "y": ey, "timer": 0.0}
        attempts += 1
    return None

enemies = []
enemy_spawn_interval = 15.0  # Intervalo en segundos para el spawn
enemy_spawn_timer = 0.0

# Listas para proyectiles
enemy_projectiles = []  
player_shots = []  

enemy_projectile_speed = 3.0
player_shot_speed = 4.0

# =====================================================
# C. SÍNTESIS DE SONIDOS MONOFÓNICOS
# =====================================================

def create_tone(frequency, duration, volume=0.5, sample_rate=44100):
    """
    Genera un tono monofónico a la frecuencia y duración especificadas.
    Devuelve un objeto Sound de pygame.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    waveform = np.sin(2 * math.pi * frequency * t) * volume
    waveform = (waveform * 32767).astype(np.int16)

    mixer_info = pygame.mixer.get_init()  # (frecuencia, tamaño, canales)
    if mixer_info is not None and mixer_info[2] == 2:
        waveform = np.column_stack((waveform, waveform))
    sound = pygame.sndarray.make_sound(waveform)
    return sound

ray_sound = create_tone(600, 0.1, volume=0.5)       # Sonido del disparo del jugador
enemy_hit_sound = create_tone(800, 0.2, volume=0.5)   # Sonido de impacto en el enemigo
player_hit_sound = create_tone(400, 0.2, volume=0.5)  # Sonido de impacto en el jugador
wall_hit_sound = create_tone(1000, 0.05, volume=0.5)  # Sonido al impactar un muro

# =====================================================
# D. FUNCIONES DE MOVIMIENTO Y RAYCASTING
# =====================================================

def move_player():
    """Actualiza la posición y el ángulo del jugador según las teclas y las colisiones."""
    global player_x, player_y, player_angle
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_angle -= 0.03
    if keys[pygame.K_RIGHT]:
        player_angle += 0.03
    if keys[pygame.K_UP]:
        next_x = player_x + math.cos(player_angle) * player_speed
        next_y = player_y + math.sin(player_angle) * player_speed
        if game_map[int(next_y)][int(next_x)] != '1':
            player_x = next_x
            player_y = next_y
    if keys[pygame.K_DOWN]:
        next_x = player_x - math.cos(player_angle) * player_speed
        next_y = player_y - math.sin(player_angle) * player_speed
        if game_map[int(next_y)][int(next_x)] != '1':
            player_x = next_x
            player_y = next_y

def draw_walls(screen):
    """Renderiza las paredes utilizando el algoritmo DDA y actualiza el z-buffer."""
    global z_buffer
    z_buffer = [0.0 for _ in range(NUM_RAYS)]
    for ray in range(NUM_RAYS):
        ray_angle = player_angle - HALF_FOV + ray * DELTA_ANGLE
        ray_dir_x = math.cos(ray_angle)
        ray_dir_y = math.sin(ray_angle)

        map_x = int(player_x)
        map_y = int(player_y)

        delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else 1e30
        delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else 1e30

        if ray_dir_x < 0:
            step_x = -1
            side_dist_x = (player_x - map_x) * delta_dist_x
        else:
            step_x = 1
            side_dist_x = (map_x + 1.0 - player_x) * delta_dist_x

        if ray_dir_y < 0:
            step_y = -1
            side_dist_y = (player_y - map_y) * delta_dist_y
        else:
            step_y = 1
            side_dist_y = (map_y + 1.0 - player_y) * delta_dist_y

        hit = False
        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0  # Impacto en un borde vertical
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1  # Impacto en un borde horizontal

            if map_x < 0 or map_x >= MAP_WIDTH or map_y < 0 or map_y >= MAP_HEIGHT:
                hit = True
                distance = MAX_DEPTH
            elif game_map[map_y][map_x] == '1':
                hit = True

        if side == 0:
            distance = (map_x - player_x + (1 - step_x) / 2) / ray_dir_x
        else:
            distance = (map_y - player_y + (1 - step_y) / 2) / ray_dir_y

        distance *= math.cos(player_angle - ray_angle)
        if distance == 0:
            distance = 0.0001

        z_buffer[ray] = distance

        wall_height = int(HEIGHT / distance)
        shade = 255 / (1 + distance * distance * 0.1)
        color = (shade, shade, shade)
        pygame.draw.rect(screen, color, (ray * SCALE, (HEIGHT - wall_height) // 2, SCALE, wall_height))

# =====================================================
# E. PROYECTILES: DISPAROS DEL JUGADOR
# (Mejoras en la detección de impactos y visibilidad)
# =====================================================

def draw_player_shots(screen):
    """
    Dibuja los disparos del jugador en la vista 3D.
    Cada disparo se proyecta según su ángulo y distancia al jugador.
    Se asegura que el tamaño del disparo tenga un valor mínimo para mejorar su visibilidad.
    """
    for shot in player_shots:
        dx = shot["x"] - player_x
        dy = shot["y"] - player_y
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        angle_to_shot = math.atan2(dy, dx)
        angle_diff = angle_to_shot - player_angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        if abs(angle_diff) < HALF_FOV:
            proj_x = (angle_diff + HALF_FOV) / FOV * WIDTH
            # Se impone un tamaño mínimo para garantizar la visibilidad del proyectil
            shot_size = max(int(HEIGHT / distance), 5)
            proj_y = (HEIGHT - shot_size) // 2
            pygame.draw.rect(screen, YELLOW, (proj_x - shot_size // 4, proj_y, shot_size // 2, shot_size))

def update_player_shots():
    """
    Actualiza la posición de los disparos del jugador y comprueba
    la colisión con los enemigos usando el rectángulo completo de cada enemigo como hitbox.
    Si el disparo toca el rectángulo, se elimina el enemigo y el disparo.
    """
    global player_shots, enemies
    new_shots = []
    enemy_size = 0.8  # Tamaño del rectángulo de colisión del enemigo (ancho y alto)
    half_size = enemy_size / 2.0

    for shot in player_shots:
        # Actualiza la posición del disparo
        shot["x"] += math.cos(shot["angle"]) * player_shot_speed
        shot["y"] += math.sin(shot["angle"]) * player_shot_speed
        
        xi = int(shot["x"])
        yi = int(shot["y"])
        
        # Comprobación de límites y colisión con muros
        if xi < 0 or xi >= MAP_WIDTH or yi < 0 or yi >= MAP_HEIGHT or game_map[yi][xi] == "1":
            wall_hit_sound.play()
            continue

        # Colisión con enemigos: se define el rectángulo de colisión del enemigo
        hit_enemy = None
        for enemy in enemies:
            left   = enemy["x"] - half_size
            right  = enemy["x"] + half_size
            top    = enemy["y"] - half_size
            bottom = enemy["y"] + half_size
            if left <= shot["x"] <= right and top <= shot["y"] <= bottom:
                hit_enemy = enemy
                break

        if hit_enemy:
            enemy_hit_sound.play()
            enemies.remove(hit_enemy)
            continue  # Descartamos el disparo que impactó

        new_shots.append(shot)
    
    player_shots[:] = new_shots

# =====================================================
# E. PROYECTILES Y COMPORTAMIENTO DE ENEMIGOS
# =====================================================

def enemy_sees_player(enemy):
    """
    Determina si el enemigo tiene línea de visión hacia el jugador usando un algoritmo DDA.
    Se traza una línea desde el enemigo al jugador y si en algún punto se encuentra un muro ('1'),
    se considera que la vista está bloqueada.
    """
    ex, ey = enemy["x"], enemy["y"]
    dx = player_x - ex
    dy = player_y - ey
    distance = math.hypot(dx, dy)
    if distance == 0:
        return True
    step = 0.1  # Resolución de la comprobación
    steps = int(distance / step)
    for i in range(steps):
        check_x = ex + dx * (i / steps)
        check_y = ey + dy * (i / steps)
        ix = int(check_x)
        iy = int(check_y)
        if ix < 0 or ix >= MAP_WIDTH or iy < 0 or iy >= MAP_HEIGHT:
            continue
        if game_map[iy][ix] == "1":
            return False
    return True

def update_enemy_projectiles():
    """
    Actualiza la posición de los disparos de los enemigos y comprueba colisiones.
    - Se incrementa la posición según su ángulo y velocidad.
    - Si el proyectil toca un muro o sale de los límites, se reproduce 'wall_hit_sound' y se elimina.
    - Si el proyectil impacta al jugador (umbral aumentado a 0.5), se reproduce 'player_hit_sound'
      y se reduce la vida del jugador.
    """
    global enemy_projectiles, player_x, player_y, player_lives
    new_projectiles = []
    for proj in enemy_projectiles:
        proj["x"] += math.cos(proj["angle"]) * enemy_projectile_speed
        proj["y"] += math.sin(proj["angle"]) * enemy_projectile_speed
        xi = int(proj["x"])
        yi = int(proj["y"])
        if xi < 0 or xi >= MAP_WIDTH or yi < 0 or yi >= MAP_HEIGHT or game_map[yi][xi] == "1":
            wall_hit_sound.play()
            continue
        if math.hypot(proj["x"] - player_x, proj["y"] - player_y) < 0.5:
            player_hit_sound.play()
            player_lives -= 1
            continue
        new_projectiles.append(proj)
    enemy_projectiles[:] = new_projectiles

def update_enemies(dt):
    """
    Actualiza el temporizador de visión de cada enemigo.
    - Si el enemigo tiene línea de visión hacia el jugador (según enemy_sees_player), se incrementa su temporizador.
    - Al alcanzar 3 segundos de visión continua, el enemigo dispara un proyectil dirigido al jugador y el temporizador se reinicia.
    """
    global enemies, enemy_projectiles
    for enemy in enemies:
        if enemy_sees_player(enemy):
            enemy["timer"] += dt
        else:
            enemy["timer"] = 0.0

        if enemy["timer"] >= 3.0:
            enemy["timer"] = 0.0
            dx = player_x - enemy["x"]
            dy = player_y - enemy["y"]
            angle = math.atan2(dy, dx)
            enemy_projectiles.append({"x": enemy["x"], "y": enemy["y"], "angle": angle})
            # Se reproduce el sonido del disparo al generar el proyectil del enemigo
            ray_sound.play()

def draw_enemies(screen):
    """
    Renderiza a los enemigos en la vista 3D como rectángulos rojos.
    Se calcula la proyección en función de la distancia y del ángulo relativo al jugador.
    Se utiliza el z-buffer para evitar que se dibujen sobre paredes (si están detrás de ellas).
    """
    for enemy in enemies:
        dx = enemy["x"] - player_x
        dy = enemy["y"] - player_y
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        angle_to_enemy = math.atan2(dy, dx)
        angle_diff = angle_to_enemy - player_angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        if abs(angle_diff) < HALF_FOV:
            proj_x = (angle_diff + HALF_FOV) / FOV * WIDTH
            enemy_height = int(HEIGHT / distance)
            proj_y = (HEIGHT - enemy_height) // 2
            ray_index = int((angle_diff + HALF_FOV) / FOV * NUM_RAYS)
            ray_index = max(0, min(NUM_RAYS - 1, ray_index))
            if distance < z_buffer[ray_index]:
                pygame.draw.rect(screen, RED, (proj_x - enemy_height // 4, proj_y, enemy_height // 2, enemy_height))

def draw_enemy_projectiles(screen):
    """
    Dibuja los disparos de los enemigos en la vista 3D como pequeños rectángulos púrpuras.
    Se utiliza el z-buffer para verificar que el proyectil no se dibuje si está oculto tras una pared.
    Se impone un tamaño mínimo para asegurar la visibilidad.
    """
    enemy_proj_color = (128, 0, 128)  # Color púrpura
    for proj in enemy_projectiles:
        dx = proj["x"] - player_x
        dy = proj["y"] - player_y
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        angle_to_proj = math.atan2(dy, dx)
        angle_diff = angle_to_proj - player_angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        if abs(angle_diff) < HALF_FOV:
            proj_x = (angle_diff + HALF_FOV) / FOV * WIDTH
            proj_size = max(int(HEIGHT / distance), 5)  # Tamaño mínimo para buena visibilidad
            proj_y = (HEIGHT - proj_size) // 2
            ray_index = int((angle_diff + HALF_FOV) / FOV * NUM_RAYS)
            ray_index = max(0, min(NUM_RAYS - 1, ray_index))
            if distance < z_buffer[ray_index]:
                pygame.draw.rect(screen, enemy_proj_color, (proj_x - proj_size // 4, proj_y, proj_size // 2, proj_size))
# =====================================================
# G. BUCLE PRINCIPAL DEL JUEGO
# =====================================================

def main():
    global enemy_spawn_timer, player_lives, player_x, player_y, player_angle, show_map, player_shots, enemies, caliz, caliz_timer
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("ENTropia 3D")
    
    # Inicia la música de fondo
    play_background_music()
    
    # Pantalla de inicio y efecto de transición
    start_screen(screen)
    transition_effect(screen)
    
    # Reinicia las variables para comenzar una nueva partida
    enemy_spawn_timer = 0.0
    player_lives = 3
    player_x, player_y = 1.5, 1.5  # Posición inicial (ajusta según tu mapa)
    player_angle = 0.0
    show_map = False
    player_shots = []
    enemies = []
    
    # Coloca el caliz en el mapa y reinicia su timer
    caliz = place_caliz()
    caliz_timer = 0.0
    
    clock = pygame.time.Clock()
    running = True
    input_buffer = ""
    
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time en segundos
        
        # Actualiza el timer del caliz y reposiciónalo cada 60 segundos
        caliz_timer += dt
        if caliz_timer >= 60:
            caliz = place_caliz()
            caliz_timer = 0.0
        
        # Detección de victoria: si el jugador pasa por encima del caliz
        # Se compara la posición del jugador y el centro del caliz usando la mitad del tamaño del caliz
        if (abs(player_x - caliz["x"]) < (CALIZ_SIZE / 2)) and (abs(player_y - caliz["y"]) < (CALIZ_SIZE / 2)):
            print("¡Has ganado!")
            win_screen(screen)
            # Reiniciamos el juego completamente para comenzar una nueva partida
            main()
            return
        
        # Procesamiento de eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Agrega un disparo del jugador
                    player_shots.append({
                        "x": player_x,
                        "y": player_y,
                        "angle": player_angle
                    })
                    ray_sound.play()
                elif event.key == pygame.K_BACKSPACE:
                    input_buffer = input_buffer[:-1]
                elif event.key == pygame.K_RETURN:
                    # Activa o desactiva el minimapa al escribir "mapa"
                    if input_buffer.lower() == "mapa":
                        show_map = not show_map
                    input_buffer = ""
                else:
                    if event.unicode.isalpha():
                        input_buffer += event.unicode
        
        # Actualización de estados
        move_player()
        update_enemies(dt)
        update_player_shots()
        update_enemy_projectiles()
        
        # Generación controlada de enemigos: se generan tres enemigos por cada ciclo de spawn
        enemy_spawn_timer += dt
        if enemy_spawn_timer >= enemy_spawn_interval:
            for _ in range(3):
                new_enemy = spawn_enemy()
                if new_enemy:
                    new_enemy["timer"] = 0.0
                    enemies.append(new_enemy)
            enemy_spawn_timer = 0.0
        
        # Renderizado de la escena 3D
        screen.fill(BLACK)
        draw_walls(screen)
        draw_enemies(screen)
        draw_player_shots(screen)      # Disparos del jugador
        draw_enemy_projectiles(screen) # Disparos de los enemigos
        
        if show_map:
            draw_minimap(screen, scale=6)
        
        # HUD: muestra las vidas como cuadrados rojos en la esquina superior derecha
        draw_lives(screen, player_lives)
        
        # Dibuja el caliz (con el mismo factor de escala usado en el minimapa)
        draw_caliz(screen, caliz, scale=6)
        
        pygame.display.flip()
        
        # Condición de Game Over: si se agotan las vidas
        if player_lives <= 0:
            print("Game Over")
            game_over_screen(screen)
            # Reiniciamos el juego completamente; llamamos recursivamente a main()
            main()
            return
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()




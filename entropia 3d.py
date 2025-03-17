import pygame
import sys
import math
import random
import numpy as np

player_speed = 0.05
player_x = 1.5
player_y = 1.5
player_angle = 0.0
player_lives = 3


# Pre-inicializamos el mezclador para sonido monofónico (1 canal)
# Nota: Para que esta configuración se aplique correctamente,
#       pygame.mixer.pre_init() DEBE llamarse antes de pygame.init()
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Verificamos la inicialización del mezclador; si no está activo, lo inicializamos manualmente
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
NUM_RAYS = 400       # Número de rayos a proyectar
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 20
SCALE = WIDTH / NUM_RAYS

# Colores
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Parámetros del laberinto (tamaño ampliado y debe ser impar para generar pasillos)
MAZE_WIDTH = 41   # número de columnas (impar)
MAZE_HEIGHT = 31  # número de filas (impar)

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

# Se utiliza un z-buffer global para almacenar la distancia de cada rayo,
# lo que servirá para comprobar la oclusión de objetos (enemigos, proyectiles, etc.).
z_buffer = [0.0 for _ in range(NUM_RAYS)]

# Variable global para controlar la visualización del minimapa.
# El minimapa se mostrará únicamente si el jugador pulsa la palabra "mapa" dentro del juego.
show_map = False

# =====================================================
# Función para dibujar el minimapa (opcional)
# =====================================================
def draw_minimap(screen, scale=6):
    """
    Dibuja un minimapa en la esquina superior izquierda mostrando el laberinto,
    la posición del jugador y otros objetos a escala.
    Solo se ejecuta si 'show_map' es True.
    """
    # Solo dibuja el minimapa si se ha activado la visualización
    if not show_map:
        return

    # Asumimos que game_map es una lista de cadenas donde '1' representa un muro
    for y, row in enumerate(game_map):
        for x, cell in enumerate(row):
            color = GRAY if cell == '1' else WHITE
            rect = pygame.Rect(x * scale, y * scale, scale, scale)
            pygame.draw.rect(screen, color, rect)
    
    # Dibuja la posición del jugador en el minimapa
    player_pos = (int(player_x * scale), int(player_y * scale))
    pygame.draw.circle(screen, RED, player_pos, 3)

# =====================================================
# B. MANEJO DE ENEMIGOS
# =====================================================

def spawn_enemy():
    """
    Genera un enemigo de forma aleatoria en el mapa.
    Se escoge una celda abierta (espacio) y se verifica que esté en frente del jugador.
    Devuelve un diccionario con posición y un temporizador (inicializado en 0).
    """
    attempts = 0
    while attempts < 100:
        rx = random.randint(1, MAP_WIDTH - 2)
        ry = random.randint(1, MAP_HEIGHT - 2)
        if game_map[ry][rx] == ' ':
            ex = rx + 0.5
            ey = ry + 0.5
            # Se verifica que el enemigo no se genere detrás del jugador:
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

# La lista de enemigos se inicializa vacía; se agregarán nuevos enemigos periódicamente.
enemies = []
enemy_spawn_interval = 15.0  # intervalo en segundos para el spawn
enemy_spawn_timer = 0.0

# Listas para proyectiles (disparos del jugador y de los enemigos)
enemy_projectiles = []  
player_shots = []  

enemy_projectile_speed = 3.0
player_shot_speed = 4.0

# =====================================================
# C. SÍNTESIS DE SONIDOS MONOFÓNICOS
# =====================================================

def create_tone(frequency, duration, volume=0.5, sample_rate=44100):
    """
    Genera un tono monofónico simple a la frecuencia y duración especificadas.
    Devuelve un objeto Sound de pygame.
    """
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    waveform = np.sin(2 * math.pi * frequency * t) * volume
    waveform = (waveform * 32767).astype(np.int16)  # Conversión a 16 bits

    # Verificamos cuántos canales usa el mixer:
    mixer_info = pygame.mixer.get_init()  # Retorna (frecuencia, tamaño, canales)
    if mixer_info is not None and mixer_info[2] == 2:
        # Si el mixer está en modo estéreo, duplicamos el arreglo mono
        waveform = np.column_stack((waveform, waveform))
    # Si el mixer es monofónico, no es necesario transformar el arreglo

    sound = pygame.sndarray.make_sound(waveform)
    return sound

# Sonidos para distintos eventos:
ray_sound = create_tone(600, 0.1, volume=0.5)       # Disparo del jugador (rayo amarillo)
enemy_hit_sound = create_tone(800, 0.2, volume=0.5)   # Impacto en el enemigo
player_hit_sound = create_tone(400, 0.2, volume=0.5)  # Impacto en el jugador
wall_hit_sound = create_tone(1000, 0.05, volume=0.5)  # Impacto en las paredes

# =====================================================
# D. FUNCIONES DE MOVIMIENTO Y RAYCASTING
# =====================================================

def move_player():
    """Actualiza la posición y el ángulo del jugador según las teclas y la colisión con muros."""
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
    """Renderiza las paredes utilizando el algoritmo DDA optimizado y actualiza el z-buffer."""
    global z_buffer
    z_buffer = [0.0] * NUM_RAYS  # Reinicializa el z-buffer para cada fotograma
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

        # Corrección para evitar el efecto "fisheye"
        distance *= math.cos(player_angle - ray_angle)
        if distance == 0:
            distance = 0.0001

        # Guardamos la distancia de este rayo en el z-buffer
        z_buffer[ray] = distance

        wall_height = int(HEIGHT / distance)
        shade = 255 / (1 + distance * distance * 0.1)
        color = (shade, shade, shade)
        pygame.draw.rect(screen, color, (ray * SCALE, (HEIGHT - wall_height) // 2, SCALE, wall_height))

def draw_player_shots(screen):
    """
    Dibuja los disparos del jugador en la vista 3D.
    Cada disparo se proyecta según su ángulo y distancia respecto al jugador,
    y se representa como un rectángulo amarillo.
    """
    for shot in player_shots:
        dx = shot["x"] - player_x
        dy = shot["y"] - player_y
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        angle_to_shot = math.atan2(dy, dx)
        angle_diff = angle_to_shot - player_angle
        # Normalizamos el ángulo
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        # Solo se dibujan los disparos que están dentro del campo de visión
        if abs(angle_diff) < HALF_FOV:
            proj_x = (angle_diff + HALF_FOV) / FOV * WIDTH
            shot_size = int(HEIGHT / distance)
            proj_y = (HEIGHT - shot_size) // 2
            pygame.draw.rect(screen, YELLOW, (proj_x - shot_size // 4, proj_y, shot_size // 2, shot_size))

# =====================================================
# Hasta aquí finaliza la primera mitad del código.
# =====================================================
# E. FUNCIONES DE ACTUALIZACIÓN DE PROYECTILES Y ENEMIGOS
# =====================================================

def enemy_sees_player(enemy):
    """
    Determina si el enemigo tiene línea de visión hacia el jugador utilizando un sencillo algoritmo DDA.
    Se recorre la línea entre la posición del enemigo y la del jugador; si en algún punto se encuentra un muro ('1'),
    se considera que la línea de visión está bloqueada.
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
        # Comprobamos los límites antes de acceder al mapa:
        ix = int(check_x)
        iy = int(check_y)
        if ix < 0 or ix >= MAP_WIDTH or iy < 0 or iy >= MAP_HEIGHT:
            continue
        if game_map[iy][ix] == "1":
            return False
    return True

def update_player_shots():
    """
    Actualiza la posición de los disparos del jugador, comprobando colisiones con muros y enemigos.
    Si un disparo impacta contra un muro o sale del rango del mapa, se reproduce el sonido y se elimina.
    Si colisiona con un enemigo, se reproduce el impacto y se elimina dicho enemigo.
    """
    global player_shots, enemies
    new_shots = []
    for shot in player_shots:
        shot["x"] += math.cos(shot["angle"]) * player_shot_speed
        shot["y"] += math.sin(shot["angle"]) * player_shot_speed
        xi = int(shot["x"])
        yi = int(shot["y"])
        # Comprobamos que las coordenadas estén dentro del mapa
        if xi < 0 or xi >= MAP_WIDTH or yi < 0 or yi >= MAP_HEIGHT or game_map[yi][xi] == "1":
            wall_hit_sound.play()
            continue
        # Comprobamos colisión con enemigos (umbral de distancia)
        hit_enemy = None
        for enemy in enemies:
            if math.hypot(enemy["x"] - shot["x"], enemy["y"] - shot["y"]) < 0.3:
                hit_enemy = enemy
                break
        if hit_enemy:
            enemy_hit_sound.play()
            enemies.remove(hit_enemy)
            continue
        new_shots.append(shot)
    player_shots[:] = new_shots

def update_enemy_projectiles():
    """
    Actualiza la posición de los disparos de los enemigos, comprobando colisiones contra muros o contra el jugador.
    Si un disparo impacta contra un muro o sale de los límites, se elimina (con efecto de sonido).
    Si impacta al jugador, se reduce una vida.
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
        if math.hypot(proj["x"] - player_x, proj["y"] - player_y) < 0.3:
            player_hit_sound.play()
            player_lives -= 1
            continue
        new_projectiles.append(proj)
    enemy_projectiles[:] = new_projectiles

def update_enemies(dt):
    """
    Actualiza el temporizador de cada enemigo. Si el enemigo tiene línea de visión del jugador
    (determinada por enemy_sees_player), se incrementa su temporizador; de lo contrario, se reinicia.
    Al alcanzar 3 segundos de visión continua, el enemigo dispara un proyectil apuntando al jugador y
    el temporizador se restablece.
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
            ray_sound.play()  # Se reutiliza el sonido del disparo

# =====================================================
# F. DIBUJO DE ENEMIGOS Y DISPAROS DE ENEMIGOS
# =====================================================

def draw_enemies(screen):
    """
    Renderiza a los enemigos en la vista 3D proyectada, representándolos como un rectángulo rojo.
    Se calcula la proyección en función de la distancia y del ángulo relativo al jugador.
    Se utiliza el z-buffer para evitar que se dibujen sobre paredes.
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
    Dibuja los disparos de los enemigos en la vista 3D, representándolos como pequeños rectángulos púrpuras.
    Se utiliza el z-buffer para comprobar su visibilidad (oclusión por paredes).
    """
    enemy_proj_color = (128, 0, 128)
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
            proj_size = int(HEIGHT / distance)
            proj_y = (HEIGHT - proj_size) // 2
            ray_index = int((angle_diff + HALF_FOV) / FOV * NUM_RAYS)
            ray_index = max(0, min(NUM_RAYS - 1, ray_index))
            if distance < z_buffer[ray_index]:
                pygame.draw.rect(screen, enemy_proj_color, (proj_x - proj_size // 4, proj_y, proj_size // 2, proj_size))

# =====================================================
# G. BUCLE PRINCIPAL DEL JUEGO
# =====================================================

def main():
    global enemy_spawn_timer, player_lives, player_x, player_y, player_angle, show_map
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("ENTropia 3D")
    clock = pygame.time.Clock()
    
    font = pygame.font.SysFont("Arial", 20)
    running = True

    # Buffer para capturar la entrada de texto para activar el minimapa
    input_buffer = ""
    
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time en segundos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Disparo del jugador
                    player_shots.append({"x": player_x, "y": player_y, "angle": player_angle})
                    ray_sound.play()
                elif event.key == pygame.K_BACKSPACE:
                    input_buffer = input_buffer[:-1]
                elif event.key == pygame.K_RETURN:
                    # Si se escribe la palabra "mapa", se alterna la visualización del minimapa
                    if input_buffer.lower() == "mapa":
                        show_map = not show_map
                    input_buffer = ""
                else:
                    # Se acumulan las letras 
                    if event.unicode.isalpha():
                        input_buffer += event.unicode

        # Actualización de estados
        move_player()
        update_enemies(dt)
        update_player_shots()
        update_enemy_projectiles()
        
        # Generación enemigos
        enemy_spawn_timer += dt
        if enemy_spawn_timer >= enemy_spawn_interval:
            new_enemy = spawn_enemy()
            if new_enemy:
                new_enemy["timer"] = 0.0
                enemies.append(new_enemy)
            enemy_spawn_timer = 0.0
        enemy_spawn_timer += dt
        if enemy_spawn_timer >= enemy_spawn_interval:
            new_enemy = spawn_enemy()
            if new_enemy:
                new_enemy["timer"] = 0.0
                enemies.append(new_enemy)
            enemy_spawn_timer = 0.0
            
        # Renderizado de la escena
        screen.fill(BLACK)
        draw_walls(screen)
        draw_enemies(screen)
        draw_player_shots(screen)      # Disparos del jugador (amarillo)
        draw_enemy_projectiles(screen) # Disparos de los enemigos (púrpura)
        
        # Si se ha activado el minimapa, se dibuja en la esquina superior izquierda
        if show_map:
            draw_minimap(screen, scale=6)
        
        lives_text = font.render("Vidas: " + str(player_lives), True, WHITE)
        screen.blit(lives_text, (10, HEIGHT - 30))
        
        pygame.display.flip()
        
        if player_lives <= 0:
            print("Game Over")
            running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()




import pygame
import math
import random
import time

# Configuración inicial
ANCHO, ALTO = 800, 400
FOV = math.pi / 3  # Campo de visión
NUM_RAYOS = 120  # Número de rayos lanzados
DIST_MAX = 300    # Distancia máxima de visión
TAMANIO_BLOQUE = 25  # Tamaño reducido para pasillos más estrechos
VELOCIDAD_JUGADOR = 1.5  # Velocidad ajustada
VELOCIDAD_ENEMIGO = 0.5  # Velocidad lenta de los enemigos
VELOCIDAD_PROYECTILES = 2  # Velocidad de proyectiles enemigos
TIEMPO_DISPARO_ENEMIGO = 5  # Tiempo entre disparos enemigos (segundos)

pygame.init()
pantalla = pygame.display.set_mode((ANCHO, ALTO))
clock = pygame.time.Clock()
fuente = pygame.font.Font(None, 74)

# Mapa 2D (1 = pared, 0 = vacío)
mapa = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1],
    [1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1],
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]

# Posición y ángulo del jugador
jugador_x, jugador_y = 100, 100
angulo = math.pi / 4
vivo = True

# Lista de enemigos y proyectiles
enemigos = []
proyectiles_jugador = []
proyectiles_enemigo = []

# Tiempos de disparo de los enemigos
ultimo_disparo_enemigos = {}

# Tiempo inicial para controlar aparición de enemigos
tiempo_inicio = time.time()

# Generar enemigos en posiciones aleatorias del mapa
def generar_enemigos(cantidad=3):
    for _ in range(cantidad):
        while True:
            x = random.randint(0, len(mapa[0]) - 1) * TAMANIO_BLOQUE + TAMANIO_BLOQUE // 2
            y = random.randint(0, len(mapa) - 1) * TAMANIO_BLOQUE + TAMANIO_BLOQUE // 2
            if mapa[y // TAMANIO_BLOQUE][x // TAMANIO_BLOQUE] == 0 and math.hypot(jugador_x - x, jugador_y - y) > 100:
                enemigos.append([x, y])
                # Asignar tiempo inicial para controlar disparos
                ultimo_disparo_enemigos[(x, y)] = time.time()
                break

# Dibujar enemigos al estilo Wolfenstein 3D
def dibujar_enemigos():
    for enemigo in enemigos:
        # Calcular distancia al jugador
        distancia = math.hypot(jugador_x - enemigo[0], jugador_y - enemigo[1])
        if distancia < DIST_MAX and tiene_linea_vision(enemigo[0], enemigo[1], jugador_x, jugador_y):
            # Ajustar tamaño del enemigo según la distancia
            altura_enemigo = (ALTO / (distancia + 0.1)) * 0.75  # 75% de la altura de las paredes
            ancho_enemigo = altura_enemigo / 2  # Proporción de ancho

            # Posición en pantalla centrada
            x_pantalla = ANCHO // 2 - ancho_enemigo // 2
            y_pantalla = (ALTO - altura_enemigo) // 2

            # Dibujar al enemigo
            pygame.draw.rect(
                pantalla,
                (255, 0, 0),
                (x_pantalla, y_pantalla, ancho_enemigo, altura_enemigo)
            )

# Trazado de rayos para comprobar línea de visión
def tiene_linea_vision(x1, y1, x2, y2):
    angulo_rayo = math.atan2(y2 - y1, x2 - x1)  # Calcular el ángulo del rayo
    distancia_total = int(math.hypot(x2 - x1, y2 - y1))  # Distancia entre los puntos

    for distancia in range(distancia_total):
        # Calcular la posición actual del rayo
        x = x1 + math.cos(angulo_rayo) * distancia
        y = y1 + math.sin(angulo_rayo) * distancia

        # Convertir a coordenadas del mapa
        col = int(x / TAMANIO_BLOQUE)
        fila = int(y / TAMANIO_BLOQUE)

        # Si el rayo golpea una pared, no hay línea de visión
        if mapa[fila][col] == 1:
            return False
    return True  # Si el rayo no golpea paredes, hay línea de visión
# Mover proyectiles y detectar colisiones
def mover_proyectiles():
    global proyectiles_jugador, proyectiles_enemigo, vivo
    # Mover proyectiles del jugador
    for p in proyectiles_jugador[:]:
        p[0] += math.cos(p[2]) * 5
        p[1] += math.sin(p[2]) * 5
        # Detectar colisión con enemigos
        for enemigo in enemigos[:]:
            if math.hypot(p[0] - enemigo[0], p[1] - enemigo[1]) < 10:
                enemigos.remove(enemigo)
                proyectiles_jugador.remove(p)
                break
        # Eliminar proyectiles fuera del mapa
        if p[0] < 0 or p[0] > ANCHO or p[1] < 0 or p[1] > ALTO:
            proyectiles_jugador.remove(p)

    # Mover proyectiles de los enemigos
    for p in proyectiles_enemigo[:]:
        p[0] += math.cos(p[2]) * VELOCIDAD_PROYECTILES
        p[1] += math.sin(p[2]) * VELOCIDAD_PROYECTILES
        # Dibujar proyectiles enemigos
        pygame.draw.rect(pantalla, (255, 255, 0), (p[0] - 5, p[1] - 5, 10, 10))
        # Detectar colisión con el jugador
        if math.hypot(p[0] - jugador_x, p[1] - jugador_y) < 10:
            vivo = False  # El jugador muere si lo alcanzan
            break
        # Eliminar proyectiles fuera del mapa
        if p[0] < 0 or p[0] > ANCHO or p[1] < 0 or p[1] > ALTO:
            proyectiles_enemigo.remove(p)

# Mover enemigos hacia el jugador
def mover_enemigos():
    for enemigo in enemigos:
        dx = jugador_x - enemigo[0]  # Diferencia en la posición X
        dy = jugador_y - enemigo[1]  # Diferencia en la posición Y
        distancia = math.hypot(dx, dy)  # Calcular la distancia al jugador

        if distancia > 0:  # Asegurarse de que la distancia no sea 0
            # Calcular el movimiento en cada eje
            movimiento_x = VELOCIDAD_ENEMIGO * (dx / distancia)
            movimiento_y = VELOCIDAD_ENEMIGO * (dy / distancia)

            # Nueva posición tentativa del enemigo
            nuevo_x = enemigo[0] + movimiento_x
            nuevo_y = enemigo[1] + movimiento_y

            # Comprobar colisiones con paredes antes de mover al enemigo
            if mapa[int(nuevo_y // TAMANIO_BLOQUE)][int(enemigo[0] // TAMANIO_BLOQUE)] == 0:
                enemigo[1] = nuevo_y  # Actualizar posición en Y si es seguro
            if mapa[int(enemigo[1] // TAMANIO_BLOQUE)][int(nuevo_x // TAMANIO_BLOQUE)] == 0:
                enemigo[0] = nuevo_x  # Actualizar posición en X si es seguro

# Mover al jugador
def mover_jugador():
    global jugador_x, jugador_y, angulo
    teclas = pygame.key.get_pressed()
    if teclas[pygame.K_w]:  # Avanzar
        nuevo_x = jugador_x + math.cos(angulo) * VELOCIDAD_JUGADOR
        nuevo_y = jugador_y + math.sin(angulo) * VELOCIDAD_JUGADOR
        if mapa[int(nuevo_y // TAMANIO_BLOQUE)][int(jugador_x // TAMANIO_BLOQUE)] == 0:
            jugador_y = nuevo_y
        if mapa[int(jugador_y // TAMANIO_BLOQUE)][int(nuevo_x // TAMANIO_BLOQUE)] == 0:
            jugador_x = nuevo_x
    if teclas[pygame.K_s]:  # Retroceder
        nuevo_x = jugador_x - math.cos(angulo) * VELOCIDAD_JUGADOR
        nuevo_y = jugador_y - math.sin(angulo) * VELOCIDAD_JUGADOR
        if mapa[int(nuevo_y // TAMANIO_BLOQUE)][int(jugador_x // TAMANIO_BLOQUE)] == 0:
            jugador_y = nuevo_y
        if mapa[int(jugador_y // TAMANIO_BLOQUE)][int(nuevo_x // TAMANIO_BLOQUE)] == 0:
            jugador_x = nuevo_x
    if teclas[pygame.K_a]:  # Girar a la izquierda
        angulo -= 0.05
    if teclas[pygame.K_d]:  # Girar a la derecha
        angulo += 0.05

# Disparar proyectiles
def disparar_proyectiles():
    teclas = pygame.key.get_pressed()
    # Disparo del jugador
    if teclas[pygame.K_SPACE]:
        proyectiles_jugador.append([jugador_x, jugador_y, angulo])

    # Disparos de los enemigos
    for enemigo in enemigos:
        tiempo_actual = time.time()
        distancia = math.hypot(jugador_x - enemigo[0], jugador_y - enemigo[1])
        if distancia < 100 and tiene_linea_vision(enemigo[0], enemigo[1], jugador_x, jugador_y):
            if tiempo_actual - ultimo_disparo_enemigos.get((enemigo[0], enemigo[1]), 0) >= TIEMPO_DISPARO_ENEMIGO:
                angulo_proyectil = math.atan2(jugador_y - enemigo[1], jugador_x - enemigo[0])
                proyectiles_enemigo.append([enemigo[0], enemigo[1], angulo_proyectil])
                # Actualizar el tiempo del último disparo
                ultimo_disparo_enemigos[(enemigo[0], enemigo[1])] = tiempo_actual

# Trazado de rayos
def trazado_rayos():
    for rayo in range(NUM_RAYOS):
        angulo_rayo = angulo - FOV / 2 + (rayo / NUM_RAYOS) * FOV
        for distancia in range(DIST_MAX):
            x = jugador_x + math.cos(angulo_rayo) * distancia
            y = jugador_y + math.sin(angulo_rayo) * distancia
            col = int(x / TAMANIO_BLOQUE)
            fila = int(y / TAMANIO_BLOQUE)
            if mapa[fila][col] == 1:
                altura_pared = ALTO / (distancia + 0.1)
                color = 255 / (1 + distancia * 0.01)
                pygame.draw.rect(
                    pantalla,
                    (color, color, color),
                    (rayo * (ANCHO // NUM_RAYOS), (ALTO - altura_pared) // 2, ANCHO // NUM_RAYOS, altura_pared)
                )
                break

# Bucle principal del juego
while vivo:
    # Generar enemigos después de 10 segundos
    if time.time() - tiempo_inicio > 10 and not enemigos:
        generar_enemigos(5)

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            quit()

    pantalla.fill((0, 0, 0))  # Limpiar la pantalla
    trazado_rayos()  # Dibujar el mapa con raycasting
    dibujar_enemigos()  # Dibujar a los enemigos
    mover_enemigos()  # Mover enemigos hacia el jugador
    disparar_proyectiles()  # Gestionar disparos
    mover_proyectiles()  # Mover proyectiles
    mover_jugador()  # Mover al jugador

    pygame.display.flip()  # Actualizar la pantalla
    clock.tick(60)  # Establecer la tasa de refresco a 60 FPS

# Mostrar pantalla de "Game Over"
pantalla.fill((0, 0, 0))
texto = fuente.render("¡Has muerto!", True, (255, 0, 0))
pantalla.blit(texto, (ANCHO // 2 - texto.get_width() // 2, ALTO // 2 - texto.get_height() // 2))
pygame.display.flip()
pygame.time.wait(3000)
pygame.quit()







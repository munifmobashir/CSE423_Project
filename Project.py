from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import time
import random


# -----------------------
# Global constants/state
# -----------------------
WINDOW_W, WINDOW_H = 1000, 800

# Camera
fovY = 70
camera_mode_third = True

# World / road
LANE_OFFSET = 120
NUM_LANES = 3
SEGMENT_LENGTH = 600
NUM_SEGMENTS = 15
LANE_MARKING_LENGTH = 50
LANE_MARKING_GAP = 40

# Player
player_lane = 1  # 0,1,2
player_z = 0.0
BASE_SPEED = 1.2
BOOST_SPEED = 3.0
player_speed = BASE_SPEED

# Score / state
score = 0
game_over = False

# Obstacles / traffic
# kind: "car", "cube", "barrier"
obstacles = []  # each: {"lane": int, "z": float, "kind": str}
spawn_timer = 0.0
spawn_interval = 1.2
start_time = time.time()

# Time
_last_time = time.time()


# -----------------------
# Utility
# -----------------------
def lane_x(idx):
    """Mirror lanes so lower index is visually left when camera is behind car."""
    center = 0.0
    return center - (idx - 1) * LANE_OFFSET


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    # Set up 2D orthographic projection for text
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(1, 1, 1)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# AABB collision in X/Z plane [web:111][web:230]
def has_collided(x1, z1, w1, h1, x2, z2, w2, h2):
    # centers (x,z) and half-sizes (w,h)
    return (
        x1 - w1 < x2 + w2 and
        x1 + w1 > x2 - w2 and
        z1 - h1 < z2 + h2 and
        z1 + h1 > z2 - h2
    )


# -----------------------
# Car / obstacle models
# -----------------------
def draw_player_car():
    glPushMatrix()

    # main body
    glColor3f(1.0, 0.8, 0.0)
    glPushMatrix()
    glScalef(2.1, 0.35, 4.2)
    glutSolidCube(20)
    glPopMatrix()

    # front hood
    glPushMatrix()
    glColor3f(1.0, 0.78, 0.0)
    glTranslatef(0, 6, 22)
    glScalef(1.9, 0.15, 1.4)
    glutSolidCube(20)
    glPopMatrix()

    # roof block
    glPushMatrix()
    glColor3f(0.95, 0.75, 0.0)
    glTranslatef(0, 9, -5)
    glScalef(1.5, 0.4, 1.6)
    glutSolidCube(20)
    glPopMatrix()

    # glass
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor4f(0.08, 0.08, 0.1, 0.85)
    glBegin(GL_QUADS)
    glVertex3f(-16, 8, 10)
    glVertex3f(16, 8, 10)
    glVertex3f(10, 16, -2)
    glVertex3f(-10, 16, -2)
    glVertex3f(-12, 8, -8)
    glVertex3f(12, 8, -8)
    glVertex3f(8, 14, -22)
    glVertex3f(-8, 14, -22)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # side skirts
    glColor3f(0.8, 0.6, 0.0)
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(20 * sx, -2, 0)
        glScalef(0.2, 0.2, 3.8)
        glutSolidCube(20)
        glPopMatrix()

    # headlights
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 0.85)
    glBegin(GL_QUADS)
    for sx in (-1, 1):
        glVertex3f(12 * sx, 2, 42)
        glVertex3f(20 * sx, 2, 42)
        glVertex3f(18 * sx, 5, 35)
        glVertex3f(10 * sx, 5, 35)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # side air intakes
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(0.05, 0.05, 0.05)
    for sx in (-1, 1):
        glBegin(GL_QUADS)
        glVertex3f(21 * sx, 2, 5)
        glVertex3f(21 * sx, 8, 5)
        glVertex3f(21 * sx, 6, -8)
        glVertex3f(21 * sx, 0, -8)
        glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # wheels: rear visible, front mostly hidden
    wheel_offsets = [
        (11, -4, -13),   # rear right
        (-11, -4, -13),  # rear left
        (11, -2, 8),     # front right
        (-11, -2, 8),    # front left
    ]

    glColor3f(0.2, 0.2, 0.2)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glScalef(0.8, 0.8, 0.8)
        glutSolidTorus(2.5, 7.5, 24, 24)
        glPopMatrix()

    # rear rims only
    glColor3f(0.8, 0.8, 0.8)
    for wx, wy, wz in wheel_offsets[:2]:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        gluDisk(gluNewQuadric(), 0, 5, 16, 1)
        glPopMatrix()

    glPopMatrix()


def draw_enemy_car():
    glPushMatrix()

    glPushMatrix()
    glColor3f(0.9, 0.15, 0.15)
    glScalef(2.0, 0.35, 3.8)
    glutSolidCube(20)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.85, 0.1, 0.1)
    glTranslatef(0, 6, 18)
    glScalef(1.8, 0.15, 1.3)
    glutSolidCube(20)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.7, 0.05, 0.08)
    glTranslatef(0, 9, -4)
    glScalef(1.4, 0.4, 1.5)
    glutSolidCube(20)
    glPopMatrix()

    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor4f(0.07, 0.07, 0.1, 0.85)
    glBegin(GL_QUADS)
    glVertex3f(-15, 8, 8)
    glVertex3f(15, 8, 8)
    glVertex3f(9, 15, -3)
    glVertex3f(-9, 15, -3)
    glVertex3f(-11, 8, -7)
    glVertex3f(11, 8, -7)
    glVertex3f(7, 13, -18)
    glVertex3f(-7, 13, -18)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 0.95, 0.7)
    glBegin(GL_QUADS)
    for sx in (-1, 1):
        glVertex3f(11 * sx, 2, 38)
        glVertex3f(18 * sx, 2, 38)
        glVertex3f(16 * sx, 5, 33)
        glVertex3f(9 * sx, 5, 33)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(0.05, 0.05, 0.05)
    for sx in (-1, 1):
        glBegin(GL_QUADS)
        glVertex3f(20 * sx, 1, 4)
        glVertex3f(20 * sx, 7, 4)
        glVertex3f(20 * sx, 5, -7)
        glVertex3f(20 * sx, -1, -7)
        glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    glColor3f(0.05, 0.05, 0.05)
    wheel_offsets = [
        (21, -7, 20),
        (-21, -7, 20),
        (21, -7, -18),
        (-21, -7, -18),
    ]
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glutSolidTorus(2.3, 7.2, 24, 24)
        glPopMatrix()

    glColor3f(0.78, 0.78, 0.78)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        gluDisk(gluNewQuadric(), 0, 4.6, 16, 1)
        glPopMatrix()

    glPopMatrix()


def draw_collectible_cube():
    glColor3f(0.2, 1.0, 0.2)  # bright green
    glPushMatrix()
    glScalef(0.7, 0.7, 0.7)
    glutSolidCube(20)
    glPopMatrix()


def draw_barrier():
    glColor3f(1.0, 1.0, 1.0)
    glPushMatrix()
    glScalef(3.0, 0.8, 0.6)
    glutSolidCube(20)
    glPopMatrix()


# -----------------------
# Road / environment
# -----------------------
def draw_road_segment(z_start):
    road_width = LANE_OFFSET * (NUM_LANES + 1)

    glColor3f(0.05, 0.05, 0.05)
    glBegin(GL_QUADS)
    glVertex3f(-road_width / 2, 0, z_start)
    glVertex3f(road_width / 2, 0, z_start)
    glVertex3f(road_width / 2, 0, z_start - SEGMENT_LENGTH)
    glVertex3f(-road_width / 2, 0, z_start - SEGMENT_LENGTH)
    glEnd()

    glColor3f(1.0, 1.0, 1.0)
    for x in (-LANE_OFFSET / 2, LANE_OFFSET / 2):
        z = z_start
        end_z = z_start - SEGMENT_LENGTH
        draw = True
        while z > end_z:
            if draw:
                z2 = max(z - LANE_MARKING_LENGTH, end_z)
                glBegin(GL_QUADS)
                glVertex3f(x - 2, 0.1, z)
                glVertex3f(x + 2, 0.1, z)
                glVertex3f(x + 2, 0.1, z2)
                glVertex3f(x - 2, 0.1, z2)
                glEnd()
                z = z2
            else:
                z -= LANE_MARKING_GAP
            draw = not draw

    rail_x_offset = road_width / 2 + 12
    z_mid = z_start - SEGMENT_LENGTH / 2

    glColor3f(0.75, 0.75, 0.75)
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(side * rail_x_offset, 18, z_mid)
        glScalef(0.25, 1.2, (SEGMENT_LENGTH + 10) / 20.0)
        glutSolidCube(20)
        glPopMatrix()

        post_gap = 80
        pz = z_start
        end_z = z_start - SEGMENT_LENGTH
        while pz > end_z:
            glPushMatrix()
            glTranslatef(side * rail_x_offset, 10, pz)
            glScalef(0.22, 1.0, 0.22)
            glutSolidCube(20)
            glPopMatrix()
            pz -= post_gap


def draw_environment():
    glClearColor(0.5, 0.8, 1.0, 1.0)

    glDepthMask(GL_FALSE)
    glDisable(GL_LIGHTING)

    glColor3f(0.1, 0.5, 0.1)
    gy = -6.0
    grass_half = 2500
    z_far = player_z + grass_half
    z_near = player_z - grass_half

    glBegin(GL_QUADS)
    glVertex3f(-2000, gy, z_far)
    glVertex3f(2000, gy, z_far)
    glVertex3f(2000, gy, z_near)
    glVertex3f(-2000, gy, z_near)
    glEnd()

    glEnable(GL_LIGHTING)
    glDepthMask(GL_TRUE)

    first_seg_index = int(player_z // SEGMENT_LENGTH)
    first_z = first_seg_index * SEGMENT_LENGTH
    last_z = player_z + SEGMENT_LENGTH * (NUM_SEGMENTS - 1)

    z = first_z
    while z <= last_z:
        draw_road_segment(z)
        z += SEGMENT_LENGTH


# -----------------------
# Obstacles / traffic
# -----------------------
def spawn_obstacle():
    global spawn_interval
    lane = random.randint(0, NUM_LANES - 1)

    # higher chance for cubes so they appear often
    kind = random.choice(["cube", "cube", "car", "barrier"])

    # spawn closer so you see them sooner
    z = player_z + 800
    obstacles.append({"lane": lane, "z": z, "kind": kind})

    elapsed = time.time() - start_time
    spawn_interval = max(0.4, 1.2 - elapsed * 0.02)


def update_obstacles(dt):
    global obstacles, spawn_timer, score, game_over

    if game_over:
        return

    # move obstacles
    for o in obstacles:
        o["z"] -= player_speed * 60 * dt

    # player AABB
    px = lane_x(player_lane)
    pz = player_z
    pw = 25  # half-width
    ph = 40  # half-length

    new_obs = []
    for o in obstacles:
        if o["z"] <= player_z - 150:
            continue

        ox = lane_x(o["lane"])
        oz = o["z"]

        if o["kind"] == "cube":
            # smaller cube box to avoid auto-collect far away
            if has_collided(px, pz, 15, 30, ox, oz, 8, 8):
                score += 10
                continue
        else:
            # car or barrier → deadly
            if has_collided(px, pz, pw, ph, ox, oz, 25, 40):
                game_over = True
                new_obs.append(o)
                break

        new_obs.append(o)

    obstacles = new_obs

    if game_over:
        return

    spawn_timer += dt
    if spawn_timer >= spawn_interval:
        spawn_timer = 0.0
        spawn_obstacle()


def draw_obstacles():
    for o in obstacles:
        x = lane_x(o["lane"])
        glPushMatrix()
        glTranslatef(x, 10, o["z"])
        if o["kind"] == "car":
            draw_enemy_car()
        elif o["kind"] == "cube":
            draw_collectible_cube()
        else:
            draw_barrier()
        glPopMatrix()


# -----------------------
# Camera
# -----------------------
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WINDOW_W / float(WINDOW_H), 0.1, 5000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    px = lane_x(player_lane)
    pz = player_z

    if camera_mode_third:
        cx, cy, cz = px, 120, pz - 250
        lx, ly, lz = px, 30, pz + 200
    else:
        cx, cy, cz = px, 40, pz + 10
        lx, ly, lz = px, 40, pz + 300

    gluLookAt(cx, cy, cz,
              lx, ly, lz,
              0, 1, 0)


# -----------------------
# Input
# -----------------------
def keyboardListener(key, x, y):
    global player_lane, player_speed
    if key in (b'a', b'A'):
        if player_lane > 0:
            player_lane -= 1
    if key in (b'd', b'D'):
        if player_lane < NUM_LANES - 1:
            player_lane += 1

    if key in (b'w', b'W'):
        player_speed = BOOST_SPEED
    if key in (b's', b'S'):
        player_speed = BASE_SPEED

    if key == b'\x1b':
        glutLeaveMainLoop()


def specialKeyListener(key, x, y):
    global player_lane
    if key == GLUT_KEY_LEFT:
        if player_lane > 0:
            player_lane -= 1
    elif key == GLUT_KEY_RIGHT:
        if player_lane < NUM_LANES - 1:
            player_lane += 1


def mouseListener(button, state, x, y):
    global camera_mode_third
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode_third = not camera_mode_third


# -----------------------
# Loop / rendering
# -----------------------
def idle():
    global player_z, _last_time
    now = time.time()
    dt = now - _last_time
    _last_time = now

    if not game_over:
        player_z += player_speed * 60 * dt

    update_obstacles(dt)
    glutPostRedisplay()


def showScreen():
    glEnable(GL_DEPTH_TEST)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WINDOW_W, WINDOW_H)

    setupCamera()
    draw_environment()
    draw_obstacles()

    glPushMatrix()
    glTranslatef(lane_x(player_lane), 20, player_z)
    draw_player_car()
    glPopMatrix()

    glDisable(GL_LIGHTING)
    draw_text(
        10, WINDOW_H - 80,
        f"Speed: {player_speed:.1f}  Lane: {player_lane}  Score: {score}  Cam: {'3rd' if camera_mode_third else '1st'}"
    )
    draw_text(
        10, WINDOW_H - 110,
        "A/D or <-/->: lane | W: boost | S: normal | Right click: toggle view"
    )

    if game_over:
        draw_text(WINDOW_W // 2 - 80, WINDOW_H // 2 + 10, "GAME OVER")
        draw_text(WINDOW_W // 2 - 120, WINDOW_H // 2 - 20, "Press ESC to quit")

    glEnable(GL_LIGHTING)

    glutSwapBuffers()


# -----------------------
# Main
# -----------------------
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 50)
    glutCreateWindow(b"3D Endless Lamborghini Highway")

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    light_diffuse = [0.9, 0.9, 0.9, 1.0]
    light_ambient = [0.2, 0.2, 0.25, 1.0]
    light_specular = [0.8, 0.8, 0.8, 1.0]
    light_pos = [0.0, 300.0, 200.0, 1.0]

    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    mat_specular = [1.0, 1.0, 1.0, 1.0]
    mat_shininess = [64.0]
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, mat_specular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, mat_shininess)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()


if __name__ == "__main__":
    main()

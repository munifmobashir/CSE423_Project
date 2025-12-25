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
player_lane = 1     # 0,1,2
player_z = 0.0
BASE_SPEED = 1.2
BOOST_SPEED = 3.0
player_speed = BASE_SPEED

# Obstacles / traffic
obstacles = []      # each: {"lane": int, "z": float, "kind": str}
spawn_timer = 0.0
spawn_interval = 1.2
start_time = time.time()

# Time
_last_time = time.time()


# -----------------------
# Utility
# -----------------------
def lane_x(idx):
    center = 0.0
    return center + (idx - 1) * LANE_OFFSET


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
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


# -----------------------
# Car / obstacle models
# -----------------------
def draw_player_car():
    glPushMatrix()

    # main body (low and wide)
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

    # cabin / roof
    glPushMatrix()
    glColor3f(0.95, 0.75, 0.0)
    glTranslatef(0, 9, -5)
    glScalef(1.5, 0.4, 1.6)
    glutSolidCube(20)
    glPopMatrix()

    # glass (front and rear)
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor4f(0.08, 0.08, 0.1, 0.85)
    glBegin(GL_QUADS)
    # front windshield
    glVertex3f(-16, 8, 10)
    glVertex3f(16, 8, 10)
    glVertex3f(10, 16, -2)
    glVertex3f(-10, 16, -2)
    # rear glass
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

    # wheels
    glColor3f(0.05, 0.05, 0.05)
    wheel_offsets = [
        (22, -7, 22),
        (-22, -7, 22),
        (22, -7, -20),
        (-22, -7, -20),
    ]
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glutSolidTorus(2.5, 7.5, 24, 24)
        glPopMatrix()

    # rims
    glColor3f(0.8, 0.8, 0.8)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        gluDisk(gluNewQuadric(), 0, 5, 16, 1)
        glPopMatrix()

    glPopMatrix()


def draw_enemy_car():
    glPushMatrix()

    # main body
    glPushMatrix()
    glColor3f(0.9, 0.15, 0.15)
    glScalef(2.0, 0.35, 3.8)
    glutSolidCube(20)
    glPopMatrix()

    # front hood
    glPushMatrix()
    glColor3f(0.85, 0.1, 0.1)
    glTranslatef(0, 6, 18)
    glScalef(1.8, 0.15, 1.3)
    glutSolidCube(20)
    glPopMatrix()

    # cabin
    glPushMatrix()
    glColor3f(0.7, 0.05, 0.08)
    glTranslatef(0, 9, -4)
    glScalef(1.4, 0.4, 1.5)
    glutSolidCube(20)
    glPopMatrix()

    # glass
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor4f(0.07, 0.07, 0.1, 0.85)
    glBegin(GL_QUADS)
    # front windshield
    glVertex3f(-15, 8, 8)
    glVertex3f(15, 8, 8)
    glVertex3f(9, 15, -3)
    glVertex3f(-9, 15, -3)
    # rear
    glVertex3f(-11, 8, -7)
    glVertex3f(11, 8, -7)
    glVertex3f(7, 13, -18)
    glVertex3f(-7, 13, -18)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # headlights
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

    # side intake
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

    # wheels
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

    # rims
    glColor3f(0.78, 0.78, 0.78)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        gluDisk(gluNewQuadric(), 0, 4.6, 16, 1)
        glPopMatrix()

    glPopMatrix()


def draw_cone():
    glColor3f(1.0, 0.5, 0.0)
    q = gluNewQuadric()
    gluCylinder(q, 8, 0, 25, 16, 4)


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

    # asphalt
    glColor3f(0.05, 0.05, 0.05)
    glBegin(GL_QUADS)
    glVertex3f(-road_width / 2, 0, z_start)
    glVertex3f( road_width / 2, 0, z_start)
    glVertex3f( road_width / 2, 0, z_start - SEGMENT_LENGTH)
    glVertex3f(-road_width / 2, 0, z_start - SEGMENT_LENGTH)
    glEnd()

    # lane markings (move because z_start is in world space)
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


def draw_environment():
    glClearColor(0.5, 0.8, 1.0, 1.0)

    # grass
    glColor3f(0.1, 0.5, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(-2000, -0.1, 2000)
    glVertex3f(2000, -0.1, 2000)
    glVertex3f(2000, -0.1, -2000)
    glVertex3f(-2000, -0.1, -2000)
    glEnd()

    # road segments in front of player, in world space
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
    kind = random.choice(["car", "cone", "barrier"])
    z = player_z + 1200
    obstacles.append({"lane": lane, "z": z, "kind": kind})

    elapsed = time.time() - start_time
    spawn_interval = max(0.4, 1.2 - elapsed * 0.02)


def update_obstacles(dt):
    global obstacles, spawn_timer
    for o in obstacles:
        o["z"] -= player_speed * 60 * dt

    obstacles = [o for o in obstacles if o["z"] > player_z - 300]

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
        elif o["kind"] == "cone":
            draw_cone()
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

    # player car
    glPushMatrix()
    glTranslatef(lane_x(player_lane), 20, player_z)
    draw_player_car()
    glPopMatrix()

    # HUD
    draw_text(10, WINDOW_H - 30,
              f"Speed: {player_speed:.1f}  Lane: {player_lane}  Cam: {'3rd' if camera_mode_third else '1st'}")
    draw_text(10, WINDOW_H - 60,
              "A/D or ←/→: lane | W: boost | S: normal | Right click: toggle view")

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

    # lighting
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

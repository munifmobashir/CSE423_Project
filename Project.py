from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18

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
LANE_OFFSET = 150  # increased for more space between lanes
NUM_LANES = 3
SEGMENT_LENGTH = 600
NUM_SEGMENTS = 15
LANE_MARKING_LENGTH = 50
LANE_MARKING_GAP = 40

# Player
player_lane = 1  # target lane: 0,1,2
player_z = 0.0
player_x = 0.0   # smooth position along X

BASE_SPEED = 5.0
player_speed = BASE_SPEED

# Smooth lane movement (Feature 2.1)
LANE_LERP_SPEED = 10.0  # bigger = snappier, smaller = smoother

# Feature-7: difficulty/speed progression
SPEED_RAMP_PER_SEC = 0.025
SPEED_RAMP_PER_100_POINTS = 0.3  # speed increase per 100 points
MAX_BASE_SPEED = 20.0  # increased max speed
BOOST_ADD = 1.8
is_boosting = False

# Feature-8: pause
is_paused = False

# Feature-8: power-up (Shield)
shield_active = False
shield_timer = 0.0
SHIELD_DURATION = 8.0

# Feature-7: bonus for destroying enemy vehicles
ENEMY_DESTROY_BONUS = 50

# Feature-4: crash visual effect
CRASH_DURATION = 0.6
crash_timer = 0.0

# Score / state
collect_score = 0
distance_score = 0
total_score = 0
game_over = False

# Obstacles / traffic
# kind: "car", "cube", "barrier", "shield"
obstacles = []  # each: {"lane": int, "z": float, "kind": str}
spawn_timer = 0.0
spawn_interval = 0.8
start_time = time.time()

# Time
_last_time = time.time()

# Cheat mode - Gun
cheat_mode = False
bullets = []  # each: {"x": float, "z": float}
BULLET_SPEED = 25.0
SHOOT_INTERVAL = 0.15
shoot_timer = 0.0


# -----------------------
# Utility
# -----------------------
def lane_x(idx):
    """Mirror lanes so lower index is visually left when camera is behind car."""
    center = 0.0
    return center - (idx - 1) * LANE_OFFSET


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


def has_collided(x1, z1, w1, h1, x2, z2, w2, h2):
    return (
        x1 - w1 < x2 + w2 and
        x1 + w1 > x2 - w2 and
        z1 - h1 < z2 + h2 and
        z1 + h1 > z2 - h2
    )


def draw_crash_flash():
    global crash_timer
    if crash_timer <= 0.0:
        return

    t = crash_timer / CRASH_DURATION
    if t < 0.0:
        t = 0.0
    if t > 1.0:
        t = 1.0

    alpha = 0.6 * t

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glColor4f(1.0, 0.2, 0.0, alpha)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(WINDOW_W, 0)
    glVertex2f(WINDOW_W, WINDOW_H)
    glVertex2f(0, WINDOW_H)
    glEnd()

    glDisable(GL_BLEND)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def restart_game():
    global player_lane, player_z, player_speed, is_boosting
    global collect_score, distance_score, total_score, game_over
    global obstacles, spawn_timer, spawn_interval, start_time
    global _last_time, is_paused
    global shield_active, shield_timer
    global player_x
    global crash_timer

    player_lane = 1
    player_z = 0.0
    player_speed = BASE_SPEED
    is_boosting = False

    player_x = lane_x(player_lane)

    collect_score = 0
    distance_score = 0
    total_score = 0
    game_over = False

    obstacles = []
    spawn_timer = 0.0
    spawn_interval = 0.8
    start_time = time.time()

    is_paused = False

    shield_active = False
    shield_timer = 0.0

    crash_timer = 0.0

    _last_time = time.time()
    
    # Reset cheat mode
    global cheat_mode, bullets, shoot_timer
    cheat_mode = False
    bullets = []
    shoot_timer = 0.0


# -----------------------
# Car / obstacle models
# -----------------------
def draw_player_car():
    glPushMatrix()

    glColor3f(1.0, 0.8, 0.0)
    glPushMatrix()
    glScalef(2.1, 0.35, 4.2)
    glutSolidCube(20)
    glPopMatrix()

    glPushMatrix()
    glColor3f(1.0, 0.78, 0.0)
    glTranslatef(0, 6, 22)
    glScalef(1.9, 0.15, 1.4)
    glutSolidCube(20)
    glPopMatrix()

    glPushMatrix()
    glColor3f(0.95, 0.75, 0.0)
    glTranslatef(0, 9, -5)
    glScalef(1.5, 0.4, 1.6)
    glutSolidCube(20)
    glPopMatrix()

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

    glColor3f(0.8, 0.6, 0.0)
    for sx in (-1, 1):
        glPushMatrix()
        glTranslatef(20 * sx, -2, 0)
        glScalef(0.2, 0.2, 3.8)
        glutSolidCube(20)
        glPopMatrix()

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

    wheel_offsets = [
        (18, -5, -28),   # rear right
        (-18, -5, -28),  # rear left
        (18, -5, 22),    # front right
        (-18, -5, 22),   # front left
    ]

    glColor3f(0.2, 0.2, 0.2)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)  # rotate to align with car
        glScalef(0.3, 0.5, 0.5)  # smaller wheel
        glutSolidCube(20)
        glPopMatrix()

    # wheel rims (lighter rectangles)
    glColor3f(0.7, 0.7, 0.7)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        glScalef(0.22, 0.35, 0.35)  # smaller inner rim
        glutSolidCube(20)
        glPopMatrix()

    # ---------- ADDED (small, non-advanced): rear + tail lights ----------
    # rear bumper block
    glPushMatrix()
    glColor3f(0.85, 0.65, 0.0)
    glTranslatef(0, 2, -42)
    glScalef(1.9, 0.12, 0.7)
    glutSolidCube(20)
    glPopMatrix()

    # tail lights (2 small red quads)
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 0.2, 0.2)
    glBegin(GL_QUADS)
    # left
    glVertex3f(-18, 2, -40)
    glVertex3f(-10, 2, -40)
    glVertex3f(-10, 6, -40)
    glVertex3f(-18, 6, -40)
    # right
    glVertex3f(10, 2, -40)
    glVertex3f(18, 2, -40)
    glVertex3f(18, 6, -40)
    glVertex3f(10, 6, -40)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()
    # -------------------------------------------------------------------

    glPopMatrix()


def draw_enemy_car():
    glPushMatrix()

    # ---------- FIXED: enemy car shape (course-level), wheels aligned ----------
    # body
    glColor3f(0.9, 0.15, 0.15)
    glPushMatrix()
    glScalef(2.0, 0.32, 3.6)
    glutSolidCube(20)
    glPopMatrix()

    # hood/front
    glPushMatrix()
    glColor3f(0.85, 0.12, 0.12)
    glTranslatef(0, 5.5, 18)
    glScalef(1.7, 0.14, 1.2)
    glutSolidCube(20)
    glPopMatrix()

    # cabin
    glPushMatrix()
    glColor3f(0.75, 0.08, 0.1)
    glTranslatef(0, 8.5, -4)
    glScalef(1.35, 0.35, 1.35)
    glutSolidCube(20)
    glPopMatrix()

    # simple windshield (dark quad)
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor4f(0.08, 0.08, 0.1, 0.85)
    glBegin(GL_QUADS)
    glVertex3f(-12, 7, 10)
    glVertex3f(12, 7, 10)
    glVertex3f(8, 13, 0)
    glVertex3f(-8, 13, 0)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # headlights (small bright quads)
    glPushMatrix()
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 0.95, 0.75)
    glBegin(GL_QUADS)
    for sx in (-1, 1):
        glVertex3f(10 * sx, 2, 38)
        glVertex3f(16 * sx, 2, 38)
        glVertex3f(14 * sx, 5, 33)
        glVertex3f(8 * sx, 5, 33)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

    # wheels (rectangular cube shape)
    wheel_offsets = [
        (17, -5, -24),   # rear right
        (-17, -5, -24),  # rear left
        (17, -5, 18),    # front right
        (-17, -5, 18),   # front left
    ]

    glColor3f(0.12, 0.12, 0.12)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)  # rotate to align with car
        glScalef(0.28, 0.48, 0.48)  # smaller wheel
        glutSolidCube(20)
        glPopMatrix()

    # wheel rims (lighter rectangles)
    glColor3f(0.75, 0.75, 0.75)
    for wx, wy, wz in wheel_offsets:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        glScalef(0.2, 0.34, 0.34)  # smaller inner rim
        glutSolidCube(20)
        glPopMatrix()
    # ------------------------------------------------------------------------

    glPopMatrix()


def draw_collectible_cube():
    glPushMatrix()
    glDisable(GL_LIGHTING)
    
    # Animation based on time
    t = time.time()
    rotation_angle = (t * 100) % 360  # continuous rotation
    pulse = 1.0 + 0.15 * abs(((t * 2) % 2) - 1)  # pulsing effect
    
    # Yellow/gold coin cube - rotating and pulsing
    glColor3f(1.0, 0.85, 0.0)
    glRotatef(rotation_angle, 0, 1, 0)  # rotate around Y axis
    glRotatef(rotation_angle * 0.7, 1, 0, 0)  # rotate around X axis
    glScalef(pulse, pulse, pulse)  # pulsing scale
    glutSolidCube(14)
    
    # Wireframe outline for sparkle effect
    glColor3f(1.0, 0.95, 0.3)
    glLineWidth(2.0)
    glutWireCube(15)
    
    glEnable(GL_LIGHTING)
    glPopMatrix()


def draw_barrier():
    glPushMatrix()
    glDisable(GL_LIGHTING)
    
    # Zebra crossing style barrier - alternating white and red stripes
    stripe_width = 10
    num_stripes = 6
    total_width = stripe_width * num_stripes
    
    for i in range(num_stripes):
        x_offset = -total_width / 2 + stripe_width / 2 + i * stripe_width
        
        # Alternate between white and red
        if i % 2 == 0:
            glColor3f(1.0, 1.0, 1.0)  # white
        else:
            glColor3f(0.9, 0.1, 0.1)  # red
        
        glPushMatrix()
        glTranslatef(x_offset, 0, 0)
        glScalef(0.5, 0.8, 0.6)
        glutSolidCube(20)
        glPopMatrix()
    
    glEnable(GL_LIGHTING)
    glPopMatrix()


def draw_shield_powerup():
    glPushMatrix()
    glDisable(GL_LIGHTING)
    
    # Animation based on time
    t = time.time()
    rotation_angle = (t * 80) % 360  # continuous rotation
    pulse = 1.0 + 0.2 * abs(((t * 1.5) % 2) - 1)  # pulsing effect
    
    # Blue shield cube - rotating and pulsing
    glColor3f(0.2, 0.7, 1.0)
    glRotatef(rotation_angle, 0, 1, 0)  # rotate around Y axis
    glRotatef(rotation_angle * 0.5, 1, 0, 1)  # diagonal rotation
    glScalef(pulse, pulse, pulse)  # pulsing scale
    glutSolidCube(16)
    
    # Outer wireframe layers for shield effect
    glColor3f(0.4, 0.85, 1.0)
    glLineWidth(2.5)
    glutWireCube(18)
    
    # Second wireframe layer
    glColor3f(0.6, 0.95, 1.0)
    glRotatef(45, 0, 0, 1)  # rotate second layer differently
    glLineWidth(2.0)
    glutWireCube(20)
    
    # Inner glowing core
    glColor3f(0.8, 1.0, 1.0)
    glutSolidCube(10)
    
    glEnable(GL_LIGHTING)
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

    # Draw grass ground first - extends to horizon
    glColor3f(0.1, 0.5, 0.1)
    gy = -6.0
    z_far = player_z + 4000  # extend grass all the way to mountains
    z_near = player_z - 2500

    glBegin(GL_QUADS)
    glVertex3f(-3000, gy, z_far)
    glVertex3f(3000, gy, z_far)
    glVertex3f(3000, gy, z_near)
    glVertex3f(-3000, gy, z_near)
    glEnd()

    # Draw distant mountains ON TOP of grass at the far edge
    # Mountains at same Z as grass far edge so they sit right on it
    mountain_base_z = z_far
    mountain_base_y = gy  # exactly same Y as grass
    
    # Draw overlapping mountains to cover full width
    for i in range(30):
        x_pos = -2800 + i * 190  # spread across full view
        height = 120 + ((i * 37) % 80)  # increased heights
        width = 240  # wide base for overlap
        
        # Mountain body - darker to blend with distance
        glColor3f(0.18, 0.28, 0.22)
        glBegin(GL_TRIANGLES)
        # Triangle base sits exactly on grass level at grass far edge
        glVertex3f(x_pos - width, mountain_base_y, mountain_base_z)
        glVertex3f(x_pos, mountain_base_y + height, mountain_base_z)
        glVertex3f(x_pos + width, mountain_base_y, mountain_base_z)
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
    
    # Don't spawn if there's already an obstacle too close in any lane
    min_distance_between = 400  # minimum Z distance between consecutive obstacles
    
    # Check if we can spawn
    can_spawn = True
    z_spawn = player_z + 800
    
    for o in obstacles:
        if abs(o["z"] - z_spawn) < min_distance_between:
            can_spawn = False
            break
    
    if not can_spawn:
        return
    
    # Equal probability for all lanes
    lane = random.randint(0, NUM_LANES - 1)

    r = random.random()
    if r < 0.12:
        kind = "cube"
    elif r < 0.16:
        kind = "shield"
    else:
        kind = random.choice(["car", "barrier"])

    z = player_z + 800
    obstacles.append({"lane": lane, "z": z, "kind": kind})

    elapsed = time.time() - start_time
    spawn_interval = max(0.35, 1.0 - elapsed * 0.02)  # reduced spawn delay


def update_obstacles(dt):
    global obstacles, spawn_timer, collect_score, game_over
    global shield_active, shield_timer
    global crash_timer

    if game_over or is_paused:
        return

    for o in obstacles:
        o["z"] -= player_speed * 60 * dt

    px = player_x
    pz = player_z
    pw = 20  # reduced for tighter player hitbox
    ph = 35  # reduced for tighter player hitbox

    new_obs = []
    for o in obstacles:
        if o["z"] <= player_z - 150:
            continue

        ox = lane_x(o["lane"])
        oz = o["z"]

        if o["kind"] == "cube":
            if has_collided(px, pz, 12, 25, ox, oz, 8, 8):  # tighter collection box
                collect_score += 10
                continue

        elif o["kind"] == "shield":
            if has_collided(px, pz, 12, 25, ox, oz, 10, 10):  # tighter collection box
                shield_active = True
                shield_timer = SHIELD_DURATION
                continue

        else:
            # Skip collision damage in cheat mode
            if cheat_mode:
                new_obs.append(o)
                continue
                
            if has_collided(px, pz, pw, ph, ox, oz, 22, 35):  # reduced obstacle hitbox
                if shield_active:
                    shield_active = False
                    shield_timer = 0.0
                    collect_score += ENEMY_DESTROY_BONUS
                    continue
                else:
                    game_over = True
                    crash_timer = CRASH_DURATION
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
        elif o["kind"] == "shield":
            draw_shield_powerup()
        else:
            draw_barrier()
        glPopMatrix()


# -----------------------
# Cheat Mode - Gun & Bullets
# -----------------------
def draw_gun():
    """Draw gun mounted on player car"""
    glPushMatrix()
    glDisable(GL_LIGHTING)
    
    # Gun barrel - dark gray
    glColor3f(0.3, 0.3, 0.35)
    glPushMatrix()
    glTranslatef(0, 12, 30)  # on top of car, front
    glScalef(0.3, 0.3, 1.5)
    glutSolidCube(20)
    glPopMatrix()
    
    # Gun base
    glColor3f(0.25, 0.25, 0.3)
    glPushMatrix()
    glTranslatef(0, 10, 20)
    glScalef(0.5, 0.4, 0.5)
    glutSolidCube(20)
    glPopMatrix()
    
    glEnable(GL_LIGHTING)
    glPopMatrix()


def draw_bullet(x, z):
    """Draw a single bullet"""
    glPushMatrix()
    glDisable(GL_LIGHTING)
    
    glTranslatef(x, 15, z)
    
    # Bullet body - bright yellow/orange
    glColor3f(1.0, 0.8, 0.0)
    glPushMatrix()
    glScalef(0.15, 0.15, 0.5)
    glutSolidCube(20)
    glPopMatrix()
    
    # Bullet trail
    glColor3f(1.0, 0.5, 0.0)
    glPushMatrix()
    glTranslatef(0, 0, -8)
    glScalef(0.1, 0.1, 0.3)
    glutSolidCube(20)
    glPopMatrix()
    
    glEnable(GL_LIGHTING)
    glPopMatrix()


def draw_bullets():
    """Draw all active bullets"""
    for b in bullets:
        draw_bullet(b["x"], b["z"])


def update_bullets(dt):
    """Update bullet positions and check collisions with obstacles"""
    global bullets, obstacles, collect_score
    
    if not cheat_mode:
        return
    
    # Move bullets forward
    new_bullets = []
    for b in bullets:
        b["z"] += BULLET_SPEED * 60 * dt
        
        # Remove bullets that are too far ahead
        if b["z"] < player_z + 1000:
            new_bullets.append(b)
    
    bullets = new_bullets
    
    # Check bullet-obstacle collisions
    bullets_to_remove = []
    obstacles_to_remove = []
    
    for b in bullets:
        for o in obstacles:
            # Only shoot cars and barriers, not collectibles
            if o["kind"] in ("car", "barrier"):
                ox = lane_x(o["lane"])
                oz = o["z"]
                
                # Simple collision check
                if abs(b["x"] - ox) < 30 and abs(b["z"] - oz) < 40:
                    if b not in bullets_to_remove:
                        bullets_to_remove.append(b)
                    if o not in obstacles_to_remove:
                        obstacles_to_remove.append(o)
                        collect_score += 25  # bonus for destroying with gun
    
    # Remove hit bullets and obstacles
    bullets = [b for b in bullets if b not in bullets_to_remove]
    obstacles = [o for o in obstacles if o not in obstacles_to_remove]


def auto_shoot(dt):
    """Automatically shoot bullets when cheat mode is active"""
    global shoot_timer, bullets
    
    if not cheat_mode or game_over or is_paused:
        return
    
    shoot_timer += dt
    if shoot_timer >= SHOOT_INTERVAL:
        shoot_timer = 0.0
        # Create new bullet at player position
        bullets.append({"x": player_x, "z": player_z + 50})


# -----------------------
# Camera
# -----------------------
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WINDOW_W / float(WINDOW_H), 0.1, 5000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    px = player_x
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
    global player_lane, is_boosting, is_paused, _last_time

    if key in (b'r', b'R'):
        restart_game()
        return

    if key in (b'p', b'P'):
        if not game_over:
            is_paused = not is_paused
            _last_time = time.time()
        return

    if is_paused:
        if key == b'\x1b':
            glutLeaveMainLoop()
        return

    if key in (b'a', b'A'):
        if player_lane > 0:
            player_lane -= 1
    if key in (b'd', b'D'):
        if player_lane < NUM_LANES - 1:
            player_lane += 1

    if key in (b'w', b'W'):
        is_boosting = True
    if key in (b's', b'S'):
        is_boosting = False

    # Cheat mode toggle
    if key in (b'u', b'U'):
        global cheat_mode
        cheat_mode = not cheat_mode

    if key == b'\x1b':
        glutLeaveMainLoop()


def specialKeyListener(key, x, y):
    global player_lane
    if game_over or is_paused:
        return
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
    global player_speed, distance_score, total_score
    global shield_active, shield_timer
    global player_x
    global crash_timer

    now = time.time()
    dt = now - _last_time
    _last_time = now

    if crash_timer > 0.0:
        crash_timer -= dt
        if crash_timer < 0.0:
            crash_timer = 0.0

    if not game_over and not is_paused:
        target_x = lane_x(player_lane)
        t = LANE_LERP_SPEED * dt
        if t > 1.0:
            t = 1.0
        player_x = player_x + (target_x - player_x) * t

        elapsed = time.time() - start_time
        time_bonus = elapsed * SPEED_RAMP_PER_SEC
        points_bonus = (total_score / 100.0) * SPEED_RAMP_PER_100_POINTS
        base_now = BASE_SPEED + time_bonus + points_bonus
        if base_now > MAX_BASE_SPEED:
            base_now = MAX_BASE_SPEED

        if is_boosting:
            player_speed = base_now + BOOST_ADD
        else:
            player_speed = base_now

        player_z += player_speed * 60 * dt

        distance_score = int(player_z / 35.0)
        total_score = distance_score + collect_score

        if shield_active:
            shield_timer -= dt
            if shield_timer <= 0.0:
                shield_timer = 0.0
                shield_active = False

    update_obstacles(dt)
    
    # Cheat mode updates
    auto_shoot(dt)
    update_bullets(dt)
    
    glutPostRedisplay()


def showScreen():
    glEnable(GL_DEPTH_TEST)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, WINDOW_W, WINDOW_H)

    setupCamera()
    draw_environment()
    draw_obstacles()

    glPushMatrix()
    glTranslatef(player_x, 20, player_z)
    draw_player_car()
    # Draw gun if cheat mode is active
    if cheat_mode:
        draw_gun()
    glPopMatrix()
    
    # Draw bullets if cheat mode is active
    if cheat_mode:
        draw_bullets()

    glDisable(GL_LIGHTING)

    if cheat_mode:
        power_text = "Power: GUN MODE (CHEAT)"
    elif shield_active:
        power_text = f"Power: SHIELD ({shield_timer:.1f}s)"
    else:
        power_text = "Power: None"

    draw_text(
        10, WINDOW_H - 80,
        f"Speed: {player_speed:.2f}  Lane: {player_lane}  Distance: {distance_score}  Collect: {collect_score}  Total: {total_score}"
    )
    draw_text(
        10, WINDOW_H - 110,
        f"{power_text}   |   Spawn: {spawn_interval:.2f}   |   Cam: {'3rd' if camera_mode_third else '1st'}"
    )
    draw_text(
        10, WINDOW_H - 140,
        "A/D: lane | W/S: boost | P: pause | R: restart | U: cheat gun | Right click: camera"
    )

    if is_paused and not game_over:
        draw_text(WINDOW_W // 2 - 55, WINDOW_H // 2 + 10, "PAUSED")
        draw_text(WINDOW_W // 2 - 140, WINDOW_H // 2 - 20, "Press P to resume")

    if game_over:
        draw_text(WINDOW_W // 2 - 90, WINDOW_H // 2 + 10, "GAME OVER")
        draw_text(WINDOW_W // 2 - 170, WINDOW_H // 2 - 20, "Press R to restart or ESC to quit")

    draw_crash_flash()

    glEnable(GL_LIGHTING)
    glutSwapBuffers()


# -----------------------
# Main
# -----------------------
def main():
    global player_x
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 50)
    glutCreateWindow(b"3D Endless Lamborghini Highway")

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    light_diffuse = [0.9, 0.9, 0.9, 1.0]
    light_ambient = [0.2, 0.2, 0.25, 1.0]
    light_pos = [0.0, 300.0, 200.0, 1.0]

    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)

    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    player_x = lane_x(player_lane)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()


if __name__ == "__main__":
    main()

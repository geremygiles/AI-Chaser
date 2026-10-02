import math
import random
import sys
import pygame



pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Chaser/Runner Sim")


clock = pygame.time.Clock()

# Colors
BG_COLOR = (30, 30, 30)
CHASER_COLOR = (231, 76, 60)  # Red
RUNNER_COLOR = (52, 152, 219)  # Blue

# Sim Constants
RUNNER_COUNT = 3


class Agent(pygame.sprite.Sprite):
  #Base class? Base class!

  def __init__(self, x, y, speed, radius, color):
    super().__init__()

    self.speed = speed
    self.radius = radius
    self.color = color
    self.wander_angle = random.uniform(0, math.pi * 2)
    self.turn_speed = 0.2 #basically interpolation rate for sprite

    # Create a clean base image (pointing right)
    self.original_image = pygame.Surface((50, 30), pygame.SRCALPHA)
    pygame.draw.polygon(
      self.original_image, self.color, [(0, 0), (50, 15), (0, 30)]
    )

    # Maintain positions internally
    self.pos_x = float(x)
    self.pos_y = float(y)

    self.dx_moved = math.cos(self.wander_angle)
    self.dy_moved = math.sin(self.wander_angle)

    # Initialize the continuous facing angle to match starting motion direction
    self.facing_angle = math.atan2(self.dy_moved, self.dx_moved)

    # Create the surface for this sprite
    diameter = int(self.radius * 2.5)
    self.image = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    self.rect = self.image.get_rect()

    self.redraw_arrow()
    self.update_rect_position()

  def redraw_arrow(self):
    """Draws the rotated arrow polygon onto the sprite's local surface."""

    pygame.draw.polygon(
          self.original_image, self.color, [(0, 0), (50, 15), (0, 30)]
        )
    target_angle_radians = math.atan2(self.dy_moved, self.dx_moved)

    # Shortest path angle interpolation (handles wrapping across the -PI to +PI seam smoothly)
    angle_diff = target_angle_radians - self.facing_angle
    angle_diff = (angle_diff + math.pi) % (math.pi * 2) - math.pi

    # LERP the image angle
    self.facing_angle += angle_diff * self.turn_speed

    angle_degrees = -math.degrees(self.facing_angle)

    # rotate the surface
    self.image = pygame.transform.rotate(self.original_image, angle_degrees)

    # Store old center position to prevent sprite translation displacement jitter during sizing changes
    old_center = self.rect.center
    self.rect = self.image.get_rect()
    self.rect.center = old_center

  def get_vector_to_wrapped(self, target_x, target_y, width, height):
    #Calculates shortest distance and vector accounting for screen wrapping
    #Important for chasing/fleeing across screen edges
    dx = target_x - self.pos_x
    dy = target_y - self.pos_y

    if dx > width / 2:
      dx -= width
    elif dx < -width / 2:
      dx += width

    if dy > height / 2:
      dy -= height
    elif dy < -height / 2:
      dy += height

    distance = math.hypot(dx, dy)
    if distance == 0:
      return 0, 0, 0

    return dx / distance, dy / distance, distance

  def wander(self, speed_modifier=0.6):
  #wander around randomly (but not too randomly)
    self.wander_angle += random.uniform(-0.05, 0.05)
    wander_speed = self.speed * speed_modifier

    self.dx_moved = math.cos(self.wander_angle) * wander_speed
    self.dy_moved = math.sin(self.wander_angle) * wander_speed

    self.pos_x += self.dx_moved
    self.pos_y += self.dy_moved

  def handle_wrapping(self, width, height):
    #actually handle the wrapping around the screen
    self.pos_x = self.pos_x % width
    self.pos_y = self.pos_y % height

  def update_rect_position(self):
    #make sure rect and stored position are in line with each other
    self.rect.centerx = int(self.pos_x)
    self.rect.centery = int(self.pos_y)


class Chaser(Agent):
  #Chases the closest Runner

  current_target = None # Current target to chase
  retarget_timer = 0 # Immediately get a target

  def __init__(self, x, y, speed, radius, color, detection_radius=200):
    super().__init__(x, y, speed, radius, color)
    self.detection_radius = detection_radius

  # Update
  def update(self, targets, dt_milliseconds=0):
    self.retarget_timer -= dt_milliseconds
    # Find a new target
    if self.retarget_timer <= 0 or self.current_target == None:
      self.retarget_timer = 1000 # Wait for 1 sec
      self.current_target = None # Clear current target
      self.color = CHASER_COLOR
      self.wander_angle = self.facing_angle # Set new wander angle
      current_closest_dist = 1000 # Give a very large radius to find any closer target

      # Iterate through the targets to find the closest
      for target in targets:
        dir_x, dir_y, dist = self.get_vector_to_wrapped(target.pos_x, target.pos_y, WIDTH, HEIGHT)

        if dist < current_closest_dist:
          current_closest_dist = dist
          if dist <= self.detection_radius:
            self.current_target = target
            

    if self.current_target != None: # Check if there is a target
      dir_x, dir_y, dist = self.get_vector_to_wrapped(
        self.current_target.pos_x,self.current_target.pos_y, WIDTH, HEIGHT
      )
      self.dx_moved = dir_x * self.speed
      self.dy_moved = dir_y * self.speed
      self.pos_x += self.dx_moved
      self.pos_y += self.dy_moved
    else:
      self.wander(speed_modifier=0.6)

    self.handle_wrapping(WIDTH, HEIGHT)
    self.redraw_arrow()  # Update rotation of sprite image
    self.update_rect_position()


class Runner(Agent):
#Runs from the chaser

  def __init__(self, x, y, speed, radius, color, detection_radius=150):
    super().__init__(x, y, speed, radius, color)
    self.detection_radius = detection_radius
    self.flee_timer = 0
    self.current_panic_offset = random.uniform(-math.pi / 6, math.pi / 6)

  def update(self, threat_x, threat_y, dt_milliseconds):
    dir_x, dir_y, dist = self.get_vector_to_wrapped(
        threat_x, threat_y, WIDTH, HEIGHT
    )

    #  Fleeing (Chaser is within 150px)
    if dist <= self.detection_radius:
      self.flee_timer += dt_milliseconds
      if self.flee_timer >= 1000:
        self.current_panic_offset = random.uniform(-math.pi / 6, math.pi / 6)
        self.flee_timer = 0

      flee_x = -(dir_x * math.cos(self.current_panic_offset) - dir_y * math.sin(self.current_panic_offset))
      flee_y = -(dir_x * math.sin(self.current_panic_offset) + dir_y * math.cos(self.current_panic_offset))

      self.dx_moved = flee_x * self.speed
      self.dy_moved = flee_y * self.speed
      self.pos_x += self.dx_moved
      self.pos_y += self.dy_moved
    else: #random wandering
      self.wander(speed_modifier=1)
      self.flee_timer = 1000

    self.handle_wrapping(WIDTH, HEIGHT)
    self.redraw_arrow()
    self.update_rect_position()


# Sim Setup
all_sprites = pygame.sprite.Group()
runners = pygame.sprite.Group()

# Create Chaser
chaser = Chaser(
    x=100, y=100, speed=5, radius=16, color=CHASER_COLOR, detection_radius=200
)

# Create Runners
for _ in range(RUNNER_COUNT):
  runner = Runner(
      x=400, y=300, speed=7, radius=14, color=RUNNER_COLOR, detection_radius=150
  )
  runners.add(runner)



all_sprites.add(chaser)
all_sprites.add(runners)

#Start the game loop
running = True
while running:
  dt = clock.tick(60)

  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False

  runners.update(chaser.pos_x, chaser.pos_y, dt)
  chaser.update(runners, dt)

  # clear background image
  screen.fill(BG_COLOR)

  #draw all sprites
  all_sprites.draw(screen)

  pygame.display.flip()

pygame.quit()
sys.exit()
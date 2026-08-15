# --- HUD.PY ---
# Pygame particle ring and UI drawing logic

import math
import pygame
from modules.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    FONT_NAME,
    FONT_SIZE,
    FPS,
    NUM_PARTICLES,
    BASE_RADIUS,
)

# HUD state
status_text = "Listening... Speak into your mic, Sir!"
user_text = ""
ai_response_text = ""

# Pygame objects
screen = None
clock = None
font = None
CENTER = None


def initialize_pygame():
    """Initialize pygame and create the display window."""
    global screen, clock, font, CENTER

    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
    CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)


def update_status(text):
    """Update the status text displayed on the HUD."""
    global status_text
    status_text = text


def update_user_text(text):
    """Update the user input text displayed on the HUD."""
    global user_text
    user_text = text


def update_response_text(text):
    """Update the AI response text displayed on the HUD."""
    global ai_response_text
    ai_response_text = text


def draw_multiline_text(surface, text, x, y, font, color, max_width=760):
    """Draw text wrapped across multiple lines."""
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    for i, line in enumerate(lines[:3]):
        line_surface = font.render(line, True, color)
        surface.blit(line_surface, (x, y + (i * 20)))


def render_frame(current_volume):
    """Render a single frame of the HUD with continuous particle animation."""
    gain = min(current_volume * 15.0, 1.5)
    screen.fill((5, 10, 20))

    # Status HUD
    status_surf = font.render(status_text, True, (0, 220, 255))
    screen.blit(status_surf, (20, WINDOW_HEIGHT - 110))

    # User Text
    if user_text:
        user_surf = font.render(user_text, True, (255, 255, 255))
        screen.blit(user_surf, (20, WINDOW_HEIGHT - 85))

    # JARVIS Response Text
    if ai_response_text:
        draw_multiline_text(
            screen,
            f"JARVIS: {ai_response_text}",
            20,
            WINDOW_HEIGHT - 60,
            font,
            (100, 255, 100),
        )

    # Particle Ring HUD with continuous rotation and shape morphing
    current_time = pygame.time.get_ticks() * 0.002  # Continuous rotation speed
    current_radius = BASE_RADIUS + (gain * 80)
    
    # Morph between different polygon shapes (circle -> star -> circle)
    shape_morph = (math.sin(pygame.time.get_ticks() * 0.001) + 1) / 2  # 0 to 1
    num_particles_display = NUM_PARTICLES
    
    for i in range(NUM_PARTICLES):
        # Continuous rotation
        base_angle = (2 * math.pi / NUM_PARTICLES) * i + current_time
        
        # Add radial pulsing
        radial_pulse = math.sin(i * 0.5 + pygame.time.get_ticks() * 0.005) * 15
        
        # Shape morphing: create star points
        is_star_point = i % 3 == 0  # Every 3rd particle is a star point
        star_radius_mult = 1.0 + (shape_morph * 0.3) if is_star_point else 1.0 - (shape_morph * 0.2)
        
        r = (current_radius * star_radius_mult) + radial_pulse
        x = int(CENTER[0] + r * math.cos(base_angle))
        y = int(CENTER[1] + r * math.sin(base_angle))

        # Vary particle size based on position
        particle_size = int(2 + gain * 5 + math.sin(i + pygame.time.get_ticks() * 0.003) * 2)
        
        # Color gradient based on position
        hue_offset = (i / NUM_PARTICLES + pygame.time.get_ticks() * 0.0001) % 1.0
        if hue_offset < 0.5:
            color = (int(hue_offset * 500), 220, 255)
        else:
            color = (0, int(220 - hue_offset * 100), 255)
        
        pygame.draw.circle(screen, color, (x, y), max(1, particle_size))

    # Inner Core Glow with pulsing
    core_glow = 1.0 + 0.3 * math.sin(pygame.time.get_ticks() * 0.003)
    core_size = int((25 + gain * 30) * core_glow)
    pygame.draw.circle(screen, (0, 150, 255), CENTER, core_size)
    
    # Outer glow ring
    glow_size = int((60 + gain * 40) * (0.8 + 0.2 * math.cos(pygame.time.get_ticks() * 0.002)))
    pygame.draw.circle(screen, (0, 100, 200), CENTER, glow_size, 2)

    pygame.display.flip()
    clock.tick(FPS)


def check_quit_event():
    """Check if user requested to quit the application."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
    return False


def cleanup():
    """Clean up pygame resources."""
    pygame.quit()

# --- HUD.PY ---
# High-fidelity Pygame HUD with animated backgrounds and Task Side-Bar
import math
import pygame
import random
from modules import config
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
status_text = f"Listening... Speak into your mic, {config.ADDRESS_AS}!"
user_text = ""
ai_response_text = ""
is_muted = False
chat_input = ""
MEMORY_COMMANDS = [
    "remember this: ...",
    "forget that: ...",
    "show my memory",
    "show my work memory",
    "show my personal memory",
    "show my developer memory",
]

# Task Side-Bar State
task_panel_x = WINDOW_WIDTH  # Start off-screen (right)
task_panel_target_x = WINDOW_WIDTH
task_panel_width = 300
current_task_name = ""
current_task_steps = [] # List of {"title": str, "status": "pending"|"running"|"done"}
task_active = False
settings_panel_open = False
settings_values = [config.USER_NAME, config.ASSISTANT_NAME, config.ADDRESS_AS]
settings_active_field = None
settings_field_rects = []
settings_save_rect = None
settings_error = ""

# Pygame objects
screen = None
clock = None
font = None
CENTER = None
grid_offset = 0

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
    global status_text
    status_text = text

def update_user_text(text):
    global user_text
    user_text = text

def update_response_text(text):
    global ai_response_text
    ai_response_text = text

def set_muted(value):
    global is_muted
    is_muted = bool(value)

def update_task_progress(name, steps, active=True):
    """Updates the side-bar with current task progress."""
    global current_task_name, current_task_steps, task_panel_target_x, task_active
    current_task_name = name
    current_task_steps = steps
    task_panel_target_x = WINDOW_WIDTH - task_panel_width
    task_active = active

def draw_glass_panel(surface, x, y, w, h, title=""):
    """Draws a semi-transparent 'glass' panel with a neon border."""
    # Panel background
    bg_rect = pygame.Rect(x, y, w, h)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((10, 20, 40, 180)) # Dark blue, semi-transparent
    surface.blit(s, (x, y))
    
    # Neon border
    pygame.draw.rect(surface, (0, 150, 255), bg_rect, 1, border_radius=5)
    
    if title:
        title_surf = font.render(title, True, (0, 200, 255))
        surface.blit(title_surf, (x + 10, y + 5))

def draw_multiline_text(surface, text, x, y, font, color, max_width=760):
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
    global grid_offset, task_panel_x
    gain = min(current_volume * 15.0, 1.5)
    screen.fill((5, 10, 20))

    # --- Background Animated Grid ---
    grid_offset = (grid_offset + 1) % 40
    for x in range(0, WINDOW_WIDTH, 40):
        pygame.draw.line(screen, (10, 30, 60), (x, 0), (x, WINDOW_HEIGHT))
    for y in range(grid_offset, WINDOW_HEIGHT, 40):
        pygame.draw.line(screen, (10, 30, 60), (0, y), (WINDOW_WIDTH, y))

    # --- Mute and Settings Buttons ---
    mute_color = (255, 50, 50) if is_muted else (50, 200, 50)
    mute_text = "MUTED" if is_muted else "MIC ON"
    mute_surf = font.render(mute_text, True, mute_color)
    screen.blit(mute_surf, (WINDOW_WIDTH - 100, 20))
    settings_surf = font.render("SETTINGS", True, (100, 200, 255))
    screen.blit(settings_surf, (WINDOW_WIDTH - 205, 20))

    if settings_panel_open:
        draw_glass_panel(screen, WINDOW_WIDTH - 355, 55, 345, 205, "Identity Settings")
        labels = ["User name", "Assistant name", "Address as"]
        settings_field_rects.clear()
        for index, (label, value) in enumerate(zip(labels, settings_values)):
            field_y = 90 + index * 42
            label_surface = font.render(label, True, (200, 220, 255))
            screen.blit(label_surface, (WINDOW_WIDTH - 345, field_y))
            field_rect = pygame.Rect(WINDOW_WIDTH - 225, field_y - 3, 205, 28)
            settings_field_rects.append(field_rect)
            border = (0, 220, 255) if settings_active_field == index else (70, 100, 140)
            pygame.draw.rect(screen, (15, 25, 45), field_rect, border_radius=4)
            pygame.draw.rect(screen, border, field_rect, 1, border_radius=4)
            value_surface = font.render(value[:22], True, (255, 255, 255))
            screen.blit(value_surface, (field_rect.x + 5, field_rect.y + 4))
        settings_save_rect = pygame.Rect(WINDOW_WIDTH - 140, 220, 110, 28)
        pygame.draw.rect(screen, (0, 90, 130), settings_save_rect, border_radius=5)
        pygame.draw.rect(screen, (0, 200, 255), settings_save_rect, 1, border_radius=5)
        screen.blit(font.render("SAVE", True, (255, 255, 255)), (settings_save_rect.x + 35, settings_save_rect.y + 4))
        if settings_error:
            screen.blit(font.render(settings_error[:38], True, (255, 100, 100)), (WINDOW_WIDTH - 345, 235))

    # --- Status HUD ---
    status_text_val = f"[{'MUTED' if is_muted else 'LISTENING'}] {status_text}"
    status_surf = font.render(status_text_val, True, (0, 220, 255))
    screen.blit(status_surf, (20, WINDOW_HEIGHT - 110))

    if not settings_panel_open:
        # --- Memory Command Panel (Glass) ---
        draw_glass_panel(screen, WINDOW_WIDTH - 295, 40, 285, 150, "Memory Commands")
        for i, command in enumerate(MEMORY_COMMANDS[:6]):
            label = font.render(f"- {command}", True, (200, 220, 255))
            screen.blit(label, (WINDOW_WIDTH - 285, 72 + (i * 18)))

    # --- Chat Bar ---
    chat_bg = pygame.Rect(20, WINDOW_HEIGHT - 40, WINDOW_WIDTH - 40, 30)
    pygame.draw.rect(screen, (20, 30, 50), chat_bg, border_radius=10)
    pygame.draw.rect(screen, (0, 150, 255), chat_bg, 2, border_radius=10)
    chat_text_surf = font.render(f"Type request: {chat_input}_", True, (200, 200, 200))
    screen.blit(chat_text_surf, (30, WINDOW_HEIGHT - 35))

    if user_text:
        user_surf = font.render(user_text, True, (255, 255, 255))
        screen.blit(user_surf, (20, WINDOW_HEIGHT - 85))

    if ai_response_text:
        draw_multiline_text(
            screen,
            f"{config.ASSISTANT_NAME}: {ai_response_text}",
            20,
            WINDOW_HEIGHT - 60,
            font,
            (100, 255, 100),
        )

    # --- Task Side-Bar Animation ---
    # Smooth sliding interpolation
    task_panel_x += (task_panel_target_x - task_panel_x) * 0.1
    if task_panel_x < WINDOW_WIDTH - 5:
        draw_glass_panel(screen, task_panel_x, 40, task_panel_width, WINDOW_HEIGHT - 80, "Task Execution")
        
        # Draw Task Content
        step_y = 70
        task_title = font.render(current_task_name, True, (255, 255, 100))
        screen.blit(task_title, (task_panel_x + 10, step_y))
        step_y += 30
        
        for step in current_task_steps:
            status_color = (100, 100, 100) # pending
            if step["status"] == "running": status_color = (0, 255, 255)
            if step["status"] == "done": status_color = (50, 255, 50)
            
            indicator = "▶" if step["status"] == "running" else "✓" if step["status"] == "done" else "○"
            step_surf = font.render(f"{indicator} {step['title']}", True, status_color)
            screen.blit(step_surf, (task_panel_x + 20, step_y))
            step_y += 25

        # Data Stream Effect (random noise)
        for _ in range(5):
            rand_x = random.randint(task_panel_x + 10, task_panel_x + task_panel_width - 10)
            rand_y = random.randint(step_y, WINDOW_HEIGHT - 100)
            noise = font.render(f"{random.randint(0, 255):02X}", True, (0, 100, 200))
            screen.blit(noise, (rand_x, rand_y))

    # --- Particle Ring (Enhanced) ---
    current_time = pygame.time.get_ticks() * 0.002
    current_radius = BASE_RADIUS + (gain * 80)
    shape_morph = (math.sin(pygame.time.get_ticks() * 0.001) + 1) / 2
    
    for i in range(NUM_PARTICLES):
        base_angle = (2 * math.pi / NUM_PARTICLES) * i + current_time
        radial_pulse = math.sin(i * 0.5 + pygame.time.get_ticks() * 0.005) * 15
        is_star_point = i % 3 == 0
        star_radius_mult = 1.0 + (shape_morph * 0.3) if is_star_point else 1.0 - (shape_morph * 0.2)
        r = (current_radius * star_radius_mult) + radial_pulse
        x = int(CENTER[0] + r * math.cos(base_angle))
        y = int(CENTER[1] + r * math.sin(base_angle))
        particle_size = int(2 + gain * 5 + math.sin(i + pygame.time.get_ticks() * 0.003) * 2)
        hue_offset = (i / NUM_PARTICLES + pygame.time.get_ticks() * 0.0001) % 1.0
        color = (int(hue_offset * 500), 220, 255) if hue_offset < 0.5 else (0, int(220 - hue_offset * 100), 255)
        pygame.draw.circle(screen, color, (x, y), max(1, particle_size))

    core_glow = 1.0 + 0.3 * math.sin(pygame.time.get_ticks() * 0.003)
    core_size = int((25 + gain * 30) * core_glow)
    pygame.draw.circle(screen, (0, 150, 255), CENTER, core_size)
    glow_size = int((60 + gain * 40) * (0.8 + 0.2 * math.cos(pygame.time.get_ticks() * 0.002)))
    pygame.draw.circle(screen, (0, 100, 200), CENTER, glow_size, 2)

    pygame.display.flip()
    clock.tick(FPS)

def handle_event(event):
    global is_muted, chat_input, settings_panel_open, settings_active_field, settings_error, status_text
    if event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = event.pos
        if WINDOW_WIDTH - 215 <= mouse_pos[0] <= WINDOW_WIDTH - 115 and 10 <= mouse_pos[1] <= 40:
            settings_panel_open = not settings_panel_open
            settings_active_field = None
            settings_error = ""
        elif settings_panel_open and settings_save_rect and settings_save_rect.collidepoint(mouse_pos):
            try:
                config.save_identity_settings(*settings_values)
                settings_values[:] = [
                    config.USER_NAME,
                    config.ASSISTANT_NAME,
                    config.ADDRESS_AS,
                ]
                status_text = f"Listening... Speak into your mic, {config.ADDRESS_AS}!"
                pygame.display.set_caption(config.WINDOW_TITLE)
                settings_error = "Saved"
            except (OSError, ValueError) as error:
                settings_error = str(error)
        elif settings_panel_open and any(rect.collidepoint(mouse_pos) for rect in settings_field_rects):
            settings_active_field = next(
                index for index, rect in enumerate(settings_field_rects) if rect.collidepoint(mouse_pos)
            )
            settings_error = ""
        elif settings_panel_open:
            settings_active_field = None
        elif WINDOW_WIDTH - 110 <= mouse_pos[0] <= WINDOW_WIDTH - 10 and 10 <= mouse_pos[1] <= 40:
            is_muted = not is_muted
            print(f"[HUD] Mute toggled: {is_muted}")
    elif event.type == pygame.KEYDOWN:
        if settings_panel_open and settings_active_field is not None:
            if event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
                settings_active_field = (settings_active_field + 1) % len(settings_values)
            elif event.key == pygame.K_BACKSPACE:
                settings_values[settings_active_field] = settings_values[settings_active_field][:-1]
            elif event.unicode and event.unicode.isprintable():
                settings_values[settings_active_field] += event.unicode
        elif settings_panel_open and event.key == pygame.K_ESCAPE:
            settings_panel_open = False
            settings_active_field = None
        elif event.key == pygame.K_RETURN:
            request = chat_input.strip()
            chat_input = ""
            return request
        elif event.key == pygame.K_BACKSPACE:
            chat_input = chat_input[:-1]
        else:
            chat_input += event.unicode
    return None

def cleanup():
    pygame.quit()

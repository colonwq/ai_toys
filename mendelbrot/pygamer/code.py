import board
import displayio
import time
import keypad
import terminalio
from adafruit_display_text import label # Import the label module

# --- Configuration ---
# Display dimensions for PyGamer
WIDTH = 160
HEIGHT = 128

MAX_ITER = 100
ZOOM_FACTOR = 0.9
PAN_SPEED = 0.1

# Initial view
center_x = -0.5
center_y = 0.0
range_x = 3.0
range_y = range_x * HEIGHT / WIDTH

# --- Buttons (using keypad.ShiftRegisterKeys) ---
# Define the button numbers for the PyGamer's ShiftRegisterKeys.
PYGAMER_BUTTON_A = 0
PYGAMER_BUTTON_B = 1
PYGAMER_BUTTON_SELECT = 2
PYGAMER_BUTTON_START = 3
PYGAMER_BUTTON_UP = 4
PYGAMER_BUTTON_LEFT = 5
PYGAMER_BUTTON_DOWN = 6
PYGAMER_BUTTON_RIGHT = 7

# Configure the PyGamer's ShiftRegisterKeys for button input
buttons = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8, # Total number of keys on the shift register
    value_when_pressed=False # Buttons are active low
)

# --- Display Setup ---
display = board.DISPLAY

# Create a Display Group
splash = displayio.Group()
display.root_group = splash

# Create a Bitmap for the Mandelbrot set
mandelbrot_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 256) # 256 colors for the palette

# Create a Palette for the colors
mandelbrot_palette = displayio.Palette(256)

# --- Color Palette (HSL to RGB conversion for smoother transitions) ---
def hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
        
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

# Generate a color palette with 256 colors
PALETTE_SIZE = 256
for i in range(PALETTE_SIZE):
    r, g, b = hsl_to_rgb(i * 360 / PALETTE_SIZE, 1, 0.5)
    mandelbrot_palette[i] = (r << 16) | (g << 8) | b # RGB to 24-bit color

# Create a TileGrid to display the Mandelbrot bitmap with the palette
mandelbrot_tile_grid = displayio.TileGrid(mandelbrot_bitmap, pixel_shader=mandelbrot_palette)
splash.append(mandelbrot_tile_grid)


# --- Status Message Setup (using adafruit_display_text.label) ---
status_label = label.Label(
    terminalio.FONT,
    color=0xFFFFFF, # White text
    text="",
    x=WIDTH // 2,
    y=HEIGHT // 2
)
status_label.anchor_point = (0.5, 0.5) # Center the text
status_label.anchored_position = (WIDTH // 2, HEIGHT // 2)

def set_text(text_string):
    status_label.text = text_string
    try:
        if status_label not in splash: # Only add if not already present
            splash.append(status_label)
    except ValueError:
        pass # Already added
    display.refresh() # Force update the display

def clear_text():
    if status_label in splash:
        splash.remove(status_label)
    display.refresh()


# --- Mandelbrot calculation function ---
def mandelbrot(c_real, c_imag):
    z_real, z_imag = 0.0, 0.0
    for i in range(MAX_ITER):
        z_real_new = z_real * z_real - z_imag * z_imag + c_real
        z_imag_new = 2 * z_real * z_imag + c_imag
        z_real, z_imag = z_real_new, z_imag_new
        if z_real * z_real + z_imag * z_imag > 4.0:
            return i
    return MAX_ITER - 1

# Function to draw the Mandelbrot set
def draw_mandelbrot(offset=0, show_status=False):
    if show_status:
        try:
            # Temporarily remove the fractal image to show the status message clearly
            if mandelbrot_tile_grid in splash:
                splash.remove(mandelbrot_tile_grid)
        except ValueError:
            pass # Already removed
        set_text("Calculating...")
        time.sleep(0.1) # Give time for message to appear before heavy calculation

    print("Drawing Mandelbrot...")
    for x in range(WIDTH):
        for y in range(HEIGHT):
            c_real = center_x - range_x / 2 + (x / WIDTH) * range_x
            c_imag = center_y - range_y / 2 + (y / HEIGHT) * range_y
            
            m = mandelbrot(c_real, c_imag)
            
            # Map iteration count to color index in palette with offset
            color_index = (m + offset) % PALETTE_SIZE
            mandelbrot_bitmap[x, y] = color_index
    print("Mandelbrot Drawn.")

    if show_status:
        clear_text() # Hide the status message
        try:
            if mandelbrot_tile_grid not in splash: # Add fractal back if not present
                splash.append(mandelbrot_tile_grid)
        except ValueError:
            pass # Already added
        display.refresh() # Force update the display to show the new fractal


# --- Game loop ---
panning_or_zooming = True # Set to True to trigger initial calculation and status
color_rotation_active = False
color_rotation_direction = 1  # 1 for forward, -1 for backward
color_offset = 0

draw_mandelbrot(color_offset, show_status=True) # Initial draw with status

while True:
    event = buttons.events.get() # Get button events
    if event:
        if event.pressed: # Only react to button presses (not releases)
            if event.key_number == PYGAMER_BUTTON_UP:
                center_y -= range_y * PAN_SPEED
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_DOWN:
                center_y += range_y * PAN_SPEED
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_LEFT:
                center_x -= range_x * PAN_SPEED
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_RIGHT:
                center_x += range_x * PAN_SPEED
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_A: # Zoom in
                range_x *= ZOOM_FACTOR
                range_y *= ZOOM_FACTOR
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_B: # Zoom out
                range_x /= ZOOM_FACTOR
                range_y /= ZOOM_FACTOR
                panning_or_zooming = True
            elif event.key_number == PYGAMER_BUTTON_SELECT:
                color_rotation_direction *= -1 # Reverse direction
                print(f"Color rotation direction changed to: {color_rotation_direction}")
            elif event.key_number == PYGAMER_BUTTON_START:
                color_rotation_active = not color_rotation_active # Toggle rotation
                print(f"Color rotation active: {color_rotation_active}")

    # Logic for drawing
    if panning_or_zooming:
        draw_mandelbrot(color_offset, show_status=True) # Redraw with status
        panning_or_zooming = False # Reset flag after redraw
    elif color_rotation_active:
        color_offset = (color_offset + color_rotation_direction) % PALETTE_SIZE
        draw_mandelbrot(color_offset, show_status=False) # No status for rotation (too fast)
    
    time.sleep(0.01) # Small delay to prevent excessive CPU usage
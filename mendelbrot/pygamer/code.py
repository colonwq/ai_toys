import board
import displayio
import terminalio # For the font to display text
from adafruit_display_text import label
import time
import analogio # Needed for joystick_x/y objects
import keypad

# --- Configuration ---
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

# Buffer size (1.5 times larger than screen, as in your original joystick code)
BUFFER_FACTOR = 1.5
BUFFER_WIDTH = int(WIDTH * BUFFER_FACTOR)
BUFFER_HEIGHT = int(HEIGHT * BUFFER_FACTOR)

MAX_ITER = 30 # Number of iterations. Lower = faster, less detail.
ZOOM_FACTOR = 1.1

# How many pixels to pan per joystick tick. This affects responsiveness.
# A higher value means faster panning across the buffer.
PAN_PIXEL_SPEED = 1 # Re-introducing this constant for joystick panning

# When to trigger a full buffer recalculation during panning
# (distance from buffer edge in pixels before redraw)
BUFFER_EDGE_THRESHOLD = int(min(WIDTH, HEIGHT) * 0.1) # 10% of screen size from edge

# Initial view for the *entire buffer*
initial_center_real = -0.5
initial_center_imag = 0.0
initial_screen_real_range = 3.0
initial_screen_imag_range = initial_screen_real_range * (HEIGHT / WIDTH)

# Calculate the initial buffer ranges based on the desired initial screen view
buffer_real_range = initial_screen_real_range * BUFFER_FACTOR
buffer_imag_range = initial_screen_imag_range * BUFFER_FACTOR

current_buffer_real_min = initial_center_real - buffer_real_range / 2
current_buffer_real_max = initial_center_real + buffer_real_range / 2
current_buffer_imag_min = initial_center_imag - buffer_imag_range / 2
current_buffer_imag_max = current_buffer_imag_min + buffer_imag_range

# Initial view offset within the buffer (start centered)
current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2

palette = displayio.Palette(MAX_ITER + 1)
for i in range(MAX_ITER):
    if i < 10:
        palette[i] = (i * 25, 0, 0)  # Reddish hues for lower iterations
    elif i < 30:
        palette[i] = (0, (i - 10) * 12, 0) # Greenish hues
    else:
        palette[i] = (0, 0, (i - 30) * 8 + 50) # Blueish hues
palette[MAX_ITER] = 0x000000  # Black for points inside the set

# Joystick deadzone (0-65535)
JOYSTICK_DEADZONE = 5000

# Define key numbers for the PyGamer's ShiftRegisterKeys
PYGAMER_BUTTON_A = 0
PYGAMER_BUTTON_B = 1


# --- Helper Functions ---

# OPTIMIZED MANDELBROT FUNCTION
def mandelbrot(c_real: float, c_imag: float, max_iter: int) -> int:
    z_real = 0.0
    z_imag = 0.0
    
    for i in range(max_iter):
        z_real_sq = z_real * z_real
        z_imag_sq = z_imag * z_imag
        
        if (z_real_sq + z_imag_sq) > 4.0:
            return i

        temp_z_real = z_real_sq - z_imag_sq + c_real
        z_imag = 2 * z_real * z_imag + c_imag
        z_real = temp_z_real
        
    return max_iter

# This function now calculates a bitmap of BUFFER_WIDTH x BUFFER_HEIGHT
def calculate_mandelbrot_buffer(real_min_buf, real_max_buf, imag_min_buf, imag_max_buf):
    image = displayio.Bitmap(BUFFER_WIDTH, BUFFER_HEIGHT, MAX_ITER + 1)
    real_step = (real_max_buf - real_min_buf) / BUFFER_WIDTH
    imag_step = (imag_max_buf - imag_min_buf) / BUFFER_HEIGHT
    for x in range(BUFFER_WIDTH):
        real_c = real_min_buf + x * real_step # Pre-calculate real part of c
        for y in range(BUFFER_HEIGHT):
            imag_c = imag_max_buf - y * imag_step # Pre-calculate imag part of c (Y-axis inverted)
            color = mandelbrot(real_c, imag_c, MAX_ITER) # Pass real and imag separately
            image[x, y] = color
    return image

# Function to get the complex coordinates of the center of the *currently displayed screen*
def get_screen_center_complex(buffer_real_min, buffer_real_max, buffer_imag_min, buffer_imag_max,
                              current_view_pixel_x, current_view_pixel_y):
    # Calculate real/imaginary step per pixel in the buffer
    real_per_pixel = (buffer_real_max - buffer_real_min) / BUFFER_WIDTH
    imag_per_pixel = (buffer_imag_max - buffer_imag_min) / BUFFER_HEIGHT

    # Calculate the top-left real/imaginary coordinates of the screen view
    screen_top_left_real = buffer_real_min + current_view_pixel_x * real_per_pixel
    screen_top_left_imag = buffer_imag_max - current_view_pixel_y * imag_per_pixel # Y-axis inverted

    # Calculate the center real/imaginary coordinates of the screen view
    center_real = screen_top_left_real + (WIDTH / 2) * real_per_pixel
    center_imag = screen_top_left_imag - (HEIGHT / 2) * imag_per_pixel # Subtract for center because positive Y is down
    return complex(center_real, center_imag)


# --- Setup ---
display = board.DISPLAY

# Main display group
group = displayio.Group()
board.DISPLAY.root_group = group

# Text display elements for "Calculating..." message
text_splash_group = displayio.Group()
status_label = label.Label(
    terminalio.FONT,
    text="Calculating initial image...",
    color=0xFFFFFF, # White text
    x=(WIDTH // 2) - 80, # Center roughly
    y=HEIGHT // 2
)
text_splash_group.append(status_label)

# PyGamer ShiftRegisterKeys setup
buttons = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8,
    value_when_pressed=False
)

# PyGamer Joystick (analog input) - now used for panning
joystick_x = analogio.AnalogIn(board.JOYSTICK_X)
joystick_y = analogio.AnalogIn(board.JOYSTICK_Y)

# --- Removed Accelerometer Initialization ---
# import busio
# import adafruit_lis3dh
# i2c = board.I2C()
# lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)


# --- Initial Mandelbrot Calculation ---
group.append(text_splash_group)
current_mandelbrot_buffer = calculate_mandelbrot_buffer(
    current_buffer_real_min, current_buffer_real_max,
    current_buffer_imag_min, current_buffer_imag_max
)

tile_grid = displayio.TileGrid(current_mandelbrot_buffer, pixel_shader=palette)
tile_grid.x = -current_view_pixel_x
tile_grid.y = -current_view_pixel_y

group.remove(text_splash_group)
group.append(tile_grid)


# --- Main Loop ---
while True:
    redraw_buffer_required = False

    event = buttons.events.get()
    if event:
        if event.pressed:
            if event.key_number == PYGAMER_BUTTON_A:  # Zoom In
                screen_center_complex = get_screen_center_complex(
                    current_buffer_real_min, current_buffer_real_max,
                    current_buffer_imag_min, current_buffer_imag_max,
                    current_view_pixel_x, current_view_pixel_y
                )

                screen_real_range = (current_buffer_real_max - current_buffer_real_min) * (WIDTH / BUFFER_WIDTH)
                screen_imag_range = (current_buffer_imag_max - current_buffer_imag_min) * (HEIGHT / BUFFER_HEIGHT)

                new_screen_real_range = screen_real_range / ZOOM_FACTOR
                new_screen_imag_range = screen_imag_range / ZOOM_FACTOR

                new_buffer_real_range = new_screen_real_range * BUFFER_FACTOR
                new_buffer_imag_range = new_screen_imag_range * BUFFER_FACTOR

                current_buffer_real_min = screen_center_complex.real - new_buffer_real_range / 2
                current_buffer_real_max = screen_center_complex.real + new_buffer_real_range / 2
                current_buffer_imag_min = screen_center_complex.imag - new_buffer_imag_range / 2
                current_buffer_imag_max = current_buffer_imag_min + new_buffer_imag_range

                current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
                current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2
                redraw_buffer_required = True

            elif event.key_number == PYGAMER_BUTTON_B:  # Zoom Out
                screen_center_complex = get_screen_center_complex(
                    current_buffer_real_min, current_buffer_real_max,
                    current_buffer_imag_min, current_buffer_imag_max,
                    current_view_pixel_x, current_view_pixel_y
                )

                screen_real_range = (current_buffer_real_max - current_buffer_real_min) * (WIDTH / BUFFER_WIDTH)
                screen_imag_range = (current_buffer_imag_max - current_buffer_imag_min) * (HEIGHT / BUFFER_HEIGHT)

                new_screen_real_range = screen_real_range * ZOOM_FACTOR
                new_screen_imag_range = screen_imag_range * ZOOM_FACTOR

                new_buffer_real_range = new_screen_real_range * BUFFER_FACTOR
                new_buffer_imag_range = new_screen_imag_range * BUFFER_FACTOR

                current_buffer_real_min = screen_center_complex.real - new_buffer_real_range / 2
                current_buffer_real_max = screen_center_complex.real + new_buffer_real_range / 2
                current_buffer_imag_min = screen_center_complex.imag - new_buffer_imag_range / 2
                current_buffer_imag_max = current_buffer_imag_min + new_buffer_imag_range

                current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
                current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2
                redraw_buffer_required = True

    # --- Handle Joystick Panning (re-implemented) ---
    joystick_x_value = joystick_x.value
    joystick_y_value = joystick_y.value

    moved_x = False
    moved_y = False

    # Pan left
    if joystick_x_value < 32768 - JOYSTICK_DEADZONE:
        current_view_pixel_x = max(0, current_view_pixel_x - PAN_PIXEL_SPEED)
        moved_x = True
    # Pan right
    elif joystick_x_value > 32768 + JOYSTICK_DEADZONE:
        current_view_pixel_x = min(BUFFER_WIDTH - WIDTH, current_view_pixel_x + PAN_PIXEL_SPEED)
        moved_x = True

    # Pan up (Y-axis inverted for "up" on many analog joysticks)
    if joystick_y_value < 32768 - JOYSTICK_DEADZONE:
        current_view_pixel_y = max(0, current_view_pixel_y - PAN_PIXEL_SPEED)
        moved_y = True
    # Pan down
    elif joystick_y_value > 32768 + JOYSTICK_DEADZONE:
        current_view_pixel_y = min(BUFFER_HEIGHT - HEIGHT, current_view_pixel_y + PAN_PIXEL_SPEED)
        moved_y = True

    # If the joystick moved, update the tilegrid position
    if moved_x or moved_y:
        tile_grid.x = -current_view_pixel_x
        tile_grid.y = -current_view_pixel_y

        # Check if we are near the buffer edge, triggering a full redraw
        if (current_view_pixel_x <= BUFFER_EDGE_THRESHOLD or
            current_view_pixel_x >= (BUFFER_WIDTH - WIDTH - BUFFER_EDGE_THRESHOLD) or
            current_view_pixel_y <= BUFFER_EDGE_THRESHOLD or
            current_view_pixel_y >= (BUFFER_HEIGHT - HEIGHT - BUFFER_EDGE_THRESHOLD)):

            screen_center_complex = get_screen_center_complex(
                current_buffer_real_min, current_buffer_real_max,
                current_buffer_imag_min, current_buffer_imag_max,
                current_view_pixel_x, current_view_pixel_y
            )

            screen_real_range = (current_buffer_real_max - current_buffer_real_min) * (WIDTH / BUFFER_WIDTH)
            screen_imag_range = (current_buffer_imag_max - current_buffer_imag_min) * (HEIGHT / BUFFER_HEIGHT)

            new_buffer_real_range = screen_real_range * BUFFER_FACTOR
            new_buffer_imag_range = screen_imag_range * BUFFER_FACTOR

            current_buffer_real_min = screen_center_complex.real - new_buffer_real_range / 2
            current_buffer_real_max = screen_center_complex.real + new_buffer_real_range / 2
            current_buffer_imag_min = screen_center_complex.imag - new_buffer_imag_range / 2
            current_buffer_imag_max = current_buffer_imag_min + new_buffer_imag_range

            current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
            current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2
            redraw_buffer_required = True


    if redraw_buffer_required:
        group.remove(tile_grid)
        status_label.text = "Calculating..."
        group.append(text_splash_group)

        current_mandelbrot_buffer = calculate_mandelbrot_buffer(
            current_buffer_real_min, current_buffer_real_max,
            current_buffer_imag_min, current_buffer_imag_max
        )
        tile_grid.bitmap = current_mandelbrot_buffer

        tile_grid.x = -current_view_pixel_x
        tile_grid.y = -current_view_pixel_y

        group.remove(text_splash_group)
        group.append(tile_grid)

    time.sleep(0.01)
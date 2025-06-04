import board
import displayio
import terminalio # For the font to display text
from adafruit_display_text import label
import time
import analogio
import keypad

# --- Configuration ---
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

MAX_ITER = 50
ZOOM_FACTOR = 1.5
PAN_SPEED = 0.1

# Initial view
real_min = -2.0
real_max = 1.0
imag_min = -1.5
imag_max = 1.5

palette = displayio.Palette(MAX_ITER + 1)
for i in range(MAX_ITER):
    if i < 10:
        palette[i] = (i * 25, 0, 0)  # Reddish hues for lower iterations
    elif i < 30:
        palette[i] = (0, (i - 10) * 12, 0) # Greenish hues
    else:
        palette[i] = (0, 0, (i - 30) * 8 + 50) # Blueish hues
palette[MAX_ITER] = 0x000000  # Black for points inside the set

# Joystick deadzone
JOYSTICK_DEADZONE = 5000  # Adjust as needed (0-65535)

# Define key numbers for the PyGamer's ShiftRegisterKeys
PYGAMER_BUTTON_A = 0
PYGAMER_BUTTON_B = 1


# --- Helper Functions ---
def mandelbrot(c: complex, max_iter: int) -> int:
    z = 0j
    for i in range(max_iter):
        z = z * z + c
        if abs(z) > 2.0:
            return i
    return max_iter

def calculate_mandelbrot(real_min, real_max, imag_min, imag_max):
    image = displayio.Bitmap(WIDTH, HEIGHT, MAX_ITER + 1)
    real_step = (real_max - real_min) / WIDTH
    imag_step = (imag_max - imag_min) / HEIGHT
    for x in range(WIDTH):
        real = real_min + x * real_step
        for y in range(HEIGHT):
            imag = imag_min + y * imag_step
            c = complex(real, imag)
            color = mandelbrot(c, MAX_ITER)
            image[x, y] = color
    return image

# --- Setup ---
display = board.DISPLAY

# Main display group
group = displayio.Group()
board.DISPLAY.root_group = group

# Text display elements
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

# PyGamer Joystick (still analog)
joystick_x = analogio.AnalogIn(board.JOYSTICK_X)
joystick_y = analogio.AnalogIn(board.JOYSTICK_Y)

# --- Initial Mandelbrot Calculation ---
# Display the "Calculating..." message
group.append(text_splash_group)
# To ensure the message is drawn before calculation starts,
# you might add a very tiny sleep or `display.refresh()` if it's available and blocking
# display.refresh() # Uncomment if you find the text doesn't show quickly enough on startup

mandelbrot_image = calculate_mandelbrot(real_min, real_max, imag_min, imag_max)
tile_grid = displayio.TileGrid(mandelbrot_image, pixel_shader=palette)

# Remove the text and show the fractal
group.remove(text_splash_group)
group.append(tile_grid)


# --- Main Loop ---
while True:
    redraw_required = False

    # Check for button events from the ShiftRegisterKeys
    event = buttons.events.get()
    if event:
        if event.pressed:
            if event.key_number == PYGAMER_BUTTON_A:  # Zoom In
                center_real = (real_min + real_max) / 2
                center_imag = (imag_min + imag_max) / 2
                real_range = (real_max - real_min) / ZOOM_FACTOR
                imag_range = (imag_max - imag_min) / ZOOM_FACTOR
                real_min = center_real - real_range / 2
                real_max = center_real + real_range / 2
                imag_min = center_imag - imag_range / 2
                imag_max = center_imag + imag_range / 2
                redraw_required = True
            elif event.key_number == PYGAMER_BUTTON_B:  # Zoom Out
                center_real = (real_min + real_max) / 2
                center_imag = (imag_min + imag_max) / 2
                real_range = (real_max - real_min) * ZOOM_FACTOR
                imag_range = (imag_max - imag_min) * ZOOM_FACTOR
                real_min = center_real - real_range / 2
                real_max = center_real + real_range / 2
                imag_min = center_imag - imag_range / 2
                imag_max = center_imag + imag_range / 2
                redraw_required = True

    # Check Joystick for panning
    joystick_x_value = joystick_x.value
    joystick_y_value = joystick_y.value

    # Pan left
    if joystick_x_value < 32768 - JOYSTICK_DEADZONE: # Center is approx 32768
        real_offset = (real_max - real_min) * PAN_SPEED
        real_min -= real_offset
        real_max -= real_offset
        redraw_required = True
    # Pan right
    elif joystick_x_value > 32768 + JOYSTICK_DEADZONE:
        real_offset = (real_max - real_min) * PAN_SPEED
        real_min += real_offset
        real_max += real_offset
        redraw_required = True

    # Pan up (Y-axis is usually inverted on joysticks, 0 is max, 65535 is min)
    if joystick_y_value < 32768 - JOYSTICK_DEADZONE:
        imag_offset = (imag_max - imag_min) * PAN_SPEED
        imag_min += imag_offset # Move positive imaginary direction (up on screen)
        imag_max += imag_offset
        redraw_required = True
    # Pan down
    elif joystick_y_value > 32768 + JOYSTICK_DEADZONE:
        imag_offset = (imag_max - imag_min) * PAN_SPEED
        imag_min -= imag_offset # Move negative imaginary direction (down on screen)
        imag_max -= imag_offset
        redraw_required = True

    if redraw_required:
        # Remove the fractal image
        group.remove(tile_grid)
        # Update text and show "Calculating..."
        status_label.text = "Calculating..."
        group.append(text_splash_group)
        # display.refresh() # Uncomment if you find the text doesn't show quickly enough

        # Recalculate the fractal
        mandelbrot_image = calculate_mandelbrot(real_min, real_max, imag_min, imag_max)
        tile_grid.bitmap = mandelbrot_image # Update the existing TileGrid's bitmap

        # Remove the text and show the new fractal
        group.remove(text_splash_group)
        group.append(tile_grid)

    time.sleep(0.02) # Small delay to debounce and save power, adjust if needed
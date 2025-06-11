import board
import displayio
import terminalio # For the font to display text
from adafruit_display_text import label
import time # Used for timing calculations
import analogio # Needed for joystick_x/y objects
import keypad # Needed for button inputs


# --- Configuration ---
# Define display dimensions (now directly used for rendered image)
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

# Buffer size (1.5 times larger than view for off-screen panning)
# A larger buffer allows for smoother, longer panning before a recalculation is needed.
BUFFER_FACTOR = 1.5
BUFFER_WIDTH = int(WIDTH * BUFFER_FACTOR)
BUFFER_HEIGHT = int(HEIGHT * BUFFER_FACTOR)

# Maximum iterations for the Mandelbrot calculation.
# Higher values produce more detail but significantly increase calculation time.
MAX_ITER = 30 

# Zoom factor for each zoom in/out operation.
# A value of 1.1 means the view will shrink/grow by 10% each time.
ZOOM_FACTOR = 1.1

# How many pixels the view pans per joystick tick.
# Higher values result in faster panning.
PAN_PIXEL_SPEED = 1 

# When to trigger a full buffer recalculation from the buffer edge.
# This prevents the displayed area from running out of pre-calculated pixels.
BUFFER_EDGE_THRESHOLD = int(min(WIDTH, HEIGHT) * 0.1) # 10% of screen size from edge

# Initial complex coordinates for the center of the Mandelbrot set.
# This defines the starting view for the fractal.
initial_center_real = -0.5
initial_center_imag = 0.0

# Initial range of real and imaginary values that fit on the screen.
# The `initial_screen_real_range` determines the initial zoom level.
initial_screen_real_range = 3.0 
initial_screen_imag_range = initial_screen_real_range * (HEIGHT / WIDTH)

# Calculate the initial complex ranges for the entire larger buffer.
# These ranges define the boundaries for the first Mandelbrot calculation.
buffer_real_range = initial_screen_real_range * BUFFER_FACTOR
buffer_imag_range = initial_screen_imag_range * BUFFER_FACTOR

# Determine the initial minimum and maximum real and imaginary values for the buffer.
current_buffer_real_min = initial_center_real - buffer_real_range / 2
current_buffer_real_max = initial_center_real + buffer_real_range / 2
current_buffer_imag_min = initial_center_imag - buffer_imag_range / 2
current_buffer_imag_max = current_buffer_imag_min + buffer_imag_range

# Initial pixel offset of the visible screen within the larger buffer.
# Starts centered to display the middle of the pre-calculated buffer.
current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2

palette = displayio.Palette(MAX_ITER + 1)
for i in range(MAX_ITER):
    if i < 10:
        palette[i] = (i * 25, 0, 0)  # Reddish hues
    elif i < 30:
        palette[i] = (0, (i - 10) * 12, 0) # Greenish hues
    else:
        palette[i] = (0, 0, (i - 30) * 8 + 50) # Blueish hues
palette[MAX_ITER] = 0x000000  # Black for points inside the set

# Joystick deadzone value. Input values within this range of the center are ignored.
# This prevents joystick drift from causing unwanted panning.
JOYSTICK_DEADZONE = 5000

# Define the button numbers for the PyGamer's ShiftRegisterKeys.
PYGAMER_BUTTON_A = 0
PYGAMER_BUTTON_B = 1

# --- Position Indicator Box Configuration ---
BOX_SIZE = 24 # Size of the position indicator box in pixels
BOX_LINE_COLOR = 0xFFFFFF # White for the box lines (palette index 1)

# Global variables to track the last drawn inner box coordinates for clearing
last_inner_box_x = -1
last_inner_box_y = -1
last_inner_box_width = -1
last_inner_box_height = -1


# --- Helper Functions ---

def draw_rectangle_perimeter(bitmap, x, y, width, height, color_index):
    """
    Draws a 1-pixel thick rectangle perimeter on a bitmap.
    Clips drawing to the bitmap's boundaries.
    """
    # Clamp coordinates and dimensions to bitmap bounds
    x_start = max(0, x)
    y_start = max(0, y)
    x_end = min(bitmap.width - 1, x + width - 1)
    y_end = min(bitmap.height - 1, y + height - 1)

    # Top line
    for i in range(x_start, x_end + 1):
        if y_start >= 0 and y_start < bitmap.height: # Ensure y is within bounds
            bitmap[i, y_start] = color_index
    # Bottom line
    for i in range(x_start, x_end + 1):
        if y_end >= 0 and y_end < bitmap.height: # Ensure y is within bounds
            bitmap[i, y_end] = color_index
    # Left line
    for i in range(y_start, y_end + 1):
        if x_start >= 0 and x_start < bitmap.width: # Ensure x is within bounds
            bitmap[x_start, i] = color_index
    # Right line
    for i in range(y_start, y_end + 1):
        if x_end >= 0 and x_end < bitmap.width: # Ensure x is within bounds
            bitmap[x_end, i] = color_index

def mandelbrot(c_real: float, c_imag: float, max_iter: int) -> int:
    """
    Calculates the iteration count for a given complex number in the Mandelbrot set.

    This optimized version avoids the computationally expensive square root
    by comparing squared magnitudes and works directly with float components
    to reduce object overhead.

    :param c_real: The real part of the complex number to test.
    :param c_imag: The imaginary part of the complex number to test.
    :param max_iter: The maximum number of iterations to perform.
    :return: The number of iterations before divergence, or `max_iter` if it converges.
    """
    z_real = 0.0
    z_imag = 0.0
    
    for i in range(max_iter):
        z_real_sq = z_real * z_real
        z_imag_sq = z_imag * z_imag
        
        # Check escape condition: if magnitude squared is greater than 4.0
        if (z_real_sq + z_imag_sq) > 4.0:
            return i

        # Apply the Mandelbrot iteration formula: z = z*z + c
        # Calculate new z_real and z_imag simultaneously using temporary variable
        temp_z_real = z_real_sq - z_imag_sq + c_real
        z_imag = 2 * z_real * z_imag + c_imag
        z_real = temp_z_real
        
    return max_iter

def calculate_mandelbrot_buffer(real_min_buf: float, real_max_buf: float, 
                                 imag_min_buf: float, imag_max_buf: float) -> displayio.Bitmap:
    """
    Calculates the Mandelbrot set for the entire buffer region and stores it in a Bitmap.

    This function iterates through every pixel in the defined buffer area,
    maps each pixel to its corresponding complex number, calculates its
    Mandelbrot iteration count, and assigns the appropriate color from the palette
    to that pixel in the `displayio.Bitmap`.

    :param real_min_buf: The minimum real value for the buffer.
    :param real_max_buf: The maximum real value for the buffer.
    :param imag_min_buf: The minimum imaginary value for the buffer.
    :param imag_max_buf: The maximum imaginary value for the buffer.
    :return: A `displayio.Bitmap` containing the rendered Mandelbrot fractal.
    """
    image = displayio.Bitmap(BUFFER_WIDTH, BUFFER_HEIGHT, MAX_ITER + 1)
    # Calculate the step size in the complex plane per pixel
    real_step = (real_max_buf - real_min_buf) / BUFFER_WIDTH
    imag_step = (imag_max_buf - imag_min_buf) / BUFFER_HEIGHT

    for x in range(BUFFER_WIDTH):
        real_c = real_min_buf + x * real_step # Real part of 'c' for this column
        for y in range(BUFFER_HEIGHT):
            # Imaginary part of 'c' (Y-axis is inverted: top of screen is max_imag, bottom is min_imag)
            imag_c = imag_max_buf - y * imag_step 
            color = mandelbrot(real_c, imag_c, MAX_ITER)
            image[x, y] = color
    return image

def get_screen_center_complex(buffer_real_min: float, buffer_real_max: float, 
                              buffer_imag_min: float, buffer_imag_max: float,
                              current_view_pixel_x: int, current_view_pixel_y: int) -> complex:
    """
    Calculates the complex coordinates of the center of the currently displayed screen view.

    This is crucial for recentering the fractal calculation when zooming or
    recalculating the buffer due to panning near the edge.

    :param buffer_real_min: The minimum real value of the entire buffer.
    :param buffer_real_max: The maximum real value of the entire buffer.
    :param imag_min_buf: The minimum imaginary value of the entire buffer.
    :param imag_max_buf: The maximum imaginary value of the entire buffer.
    :param current_view_pixel_x: The X-pixel offset of the top-left corner of the view within the buffer.
    :param current_view_pixel_y: The Y-pixel offset of the top-left corner of the view within the buffer.
    :return: A complex number representing the center of the current screen view.
    """
    # Calculate real/imaginary step per pixel within the buffer
    real_per_pixel = (buffer_real_max - buffer_real_min) / BUFFER_WIDTH
    imag_per_pixel = (buffer_imag_max - buffer_imag_min) / BUFFER_HEIGHT

    # Calculate the top-left real/imaginary coordinates of the current screen view
    screen_top_left_real = buffer_real_min + current_view_pixel_x * real_per_pixel
    screen_top_left_imag = buffer_imag_max - current_view_pixel_y * imag_per_pixel 

    # Calculate the center real/imaginary coordinates of the screen view
    center_real = screen_top_left_real + (WIDTH / 2) * real_per_pixel
    # For imaginary, positive Y pixels move downwards, so subtract for center
    center_imag = screen_top_left_imag - (HEIGHT / 2) * imag_per_pixel 
    return complex(center_real, center_imag)


# --- Setup Display and Input Devices ---
display = board.DISPLAY

# Main display group to hold all visual elements
group = displayio.Group()
board.DISPLAY.root_group = group

# Setup for displaying the "Calculating..." message
text_splash_group = displayio.Group()
status_label = label.Label(
    terminalio.FONT,
    text="Calculating initial image...",
    color=0xFFFFFF, # White text
    x=(WIDTH // 2) - (len("Calculating initial image...") * 6 // 2), # Centered horizontally
    y=HEIGHT // 2 # Centered vertically
)
text_splash_group.append(status_label)

# Configure the PyGamer's ShiftRegisterKeys for button input
buttons = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8, # Total number of keys on the shift register
    value_when_pressed=False # Buttons are active low
)

# Configure the PyGamer's analog joystick inputs
joystick_x = analogio.AnalogIn(board.JOYSTICK_X)
joystick_y = analogio.AnalogIn(board.JOYSTICK_Y)

# --- Setup Position Indicator Box ---
# Create the bitmap for the BOX_SIZE x BOX_SIZE box
# Using bit_depth=1 allows values 0 or 1.
indicator_box_bitmap = displayio.Bitmap(BOX_SIZE, BOX_SIZE, 1) 
indicator_box_palette = displayio.Palette(2) # Only 2 colors in the palette
indicator_box_palette[0] = 0x000000 # Black for background/empty inside box
indicator_box_palette[1] = BOX_LINE_COLOR # White for the box lines

# Draw the OUTER white box lines on the bitmap (using palette index 1)
# This box represents the entire buffer
for i in range(BOX_SIZE):
    indicator_box_bitmap[i, 0] = 1              # Top border
    indicator_box_bitmap[i, BOX_SIZE - 1] = 1   # Bottom border
    indicator_box_bitmap[0, i] = 1              # Left border
    indicator_box_bitmap[BOX_SIZE - 1, i] = 1   # Right border

# Create the TileGrid for the indicator box, placed in the upper-left corner
indicator_box_tile_grid = displayio.TileGrid(
    indicator_box_bitmap,
    pixel_shader=indicator_box_palette,
    x=0, y=0, # Position fixed in the upper-left corner
    tile_width=BOX_SIZE, tile_height=BOX_SIZE # Use full bitmap as one tile
)


# --- Initial Mandelbrot Calculation and Display Setup ---
# Display the "Calculating..." message while the initial fractal is computed.
group.append(text_splash_group)

# Record time before calculation for performance measurement
start_time = time.monotonic()
current_mandelbrot_buffer = calculate_mandelbrot_buffer(
    current_buffer_real_min, current_buffer_real_max,
    current_buffer_imag_min, current_buffer_imag_max
)
end_time = time.monotonic()
calculation_duration = end_time - start_time
print(f"Initial image calculated in {calculation_duration:.2f} seconds.") # Output calculation time

# Create a TileGrid to display the calculated Mandelbrot buffer.
tile_grid = displayio.TileGrid(current_mandelbrot_buffer, pixel_shader=palette)

# Position the TileGrid to show the centered portion of the buffer initially.
tile_grid.x = -current_view_pixel_x
tile_grid.y = -current_view_pixel_y

# Remove the "Calculating..." message and display the fractal.
group.remove(text_splash_group)
group.append(tile_grid)

# Add the indicator box to the display group (on top of the fractal)
group.append(indicator_box_tile_grid)


# --- Main Application Loop ---
while True:
    redraw_buffer_required = False # Flag to indicate if a full buffer recalculation is needed

    # --- Handle Button Events (Zoom In/Out) ---
    event = buttons.events.get()
    if event:
        if event.pressed:
            if event.key_number == PYGAMER_BUTTON_A:  # 'A' button for Zoom In
                # Get the complex center of the current screen view
                screen_center_complex = get_screen_center_complex(
                    current_buffer_real_min, current_buffer_real_max,
                    current_buffer_imag_min, current_buffer_imag_max,
                    current_view_pixel_x, current_view_pixel_y
                )

                # Calculate the current complex range of the displayed screen
                screen_real_range = (current_buffer_real_max - current_buffer_real_min) * (WIDTH / BUFFER_WIDTH)
                screen_imag_range = (current_buffer_imag_max - current_buffer_imag_min) * (HEIGHT / BUFFER_HEIGHT)

                # Determine the new screen view range after zooming in
                new_screen_real_range = screen_real_range / ZOOM_FACTOR
                new_screen_imag_range = screen_imag_range / ZOOM_FACTOR

                # Calculate the new buffer's complex ranges, centered around the zoom point
                new_buffer_real_range = new_screen_real_range * BUFFER_FACTOR
                new_buffer_imag_range = new_screen_imag_range * BUFFER_FACTOR

                # Update the buffer's min/max real/imaginary values
                current_buffer_real_min = screen_center_complex.real - new_buffer_real_range / 2
                current_buffer_real_max = screen_center_complex.real + new_buffer_real_range / 2
                current_buffer_imag_min = screen_center_complex.imag - new_buffer_imag_range / 2
                current_buffer_imag_max = current_buffer_imag_min + new_buffer_imag_range

                # Reset the view offset to the center of the new buffer
                current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
                current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2
                redraw_buffer_required = True # Signal that a new buffer calculation is needed

            elif event.key_number == PYGAMER_BUTTON_B:  # 'B' button for Zoom Out
                # Similar logic to Zoom In, but ranges are multiplied by ZOOM_FACTOR
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

    # --- Handle Joystick Panning ---
    joystick_x_value = joystick_x.value
    joystick_y_value = joystick_y.value

    moved_x = False
    moved_y = False

    # Adjust view based on joystick X-axis input
    if joystick_x_value < 32768 - JOYSTICK_DEADZONE: # Joystick moved left
        current_view_pixel_x = max(0, current_view_pixel_x - PAN_PIXEL_SPEED)
        moved_x = True
    elif joystick_x_value > 32768 + JOYSTICK_DEADZONE: # Joystick moved right
        current_view_pixel_x = min(BUFFER_WIDTH - WIDTH, current_view_pixel_x + PAN_PIXEL_SPEED)
        moved_x = True

    # Adjust view based on joystick Y-axis input (Y-axis is often inverted for 'up')
    if joystick_y_value < 32768 - JOYSTICK_DEADZONE: # Joystick moved up
        current_view_pixel_y = max(0, current_view_pixel_y - PAN_PIXEL_SPEED)
        moved_y = True
    elif joystick_y_value > 32768 + JOYSTICK_DEADZONE: # Joystick moved down
        current_view_pixel_y = min(BUFFER_HEIGHT - HEIGHT, current_view_pixel_y + PAN_PIXEL_SPEED)
        moved_y = True

    # If the view offset has changed due to joystick input, update the TileGrid position
    if moved_x or moved_y:
        tile_grid.x = -current_view_pixel_x
        tile_grid.y = -current_view_pixel_y

        # --- Check for Buffer Edge and Trigger Recalculation ---
        # If the current view approaches the edge of the pre-calculated buffer,
        # a new full buffer needs to be computed.
        if (current_view_pixel_x <= BUFFER_EDGE_THRESHOLD or
            current_view_pixel_x >= (BUFFER_WIDTH - WIDTH - BUFFER_EDGE_THRESHOLD) or
            current_view_pixel_y <= BUFFER_EDGE_THRESHOLD or
            current_view_pixel_y >= (BUFFER_HEIGHT - HEIGHT - BUFFER_EDGE_THRESHOLD)):

            # Get the complex center of the current screen view before recalculating
            screen_center_complex = get_screen_center_complex(
                current_buffer_real_min, current_buffer_real_max,
                current_buffer_imag_min, current_buffer_imag_max,
                current_view_pixel_x, current_view_pixel_y
            )

            # Determine the complex range of the current screen view
            screen_real_range = (current_buffer_real_max - current_buffer_real_min) * (WIDTH / BUFFER_WIDTH)
            screen_imag_range = (current_buffer_imag_max - current_buffer_imag_min) * (HEIGHT / BUFFER_HEIGHT)

            # Calculate the new, larger buffer's complex ranges centered around the current screen
            # When simply re-centering the buffer, we maintain the current screen's zoom level.
            new_buffer_real_range = screen_real_range * BUFFER_FACTOR
            new_buffer_imag_range = screen_imag_range * BUFFER_FACTOR

            # Update the buffer's min/max real/imaginary values
            current_buffer_real_min = screen_center_complex.real - new_buffer_real_range / 2
            current_buffer_real_max = screen_center_complex.real + new_buffer_real_range / 2
            current_buffer_imag_min = screen_center_complex.imag - new_buffer_imag_range / 2
            current_buffer_imag_max = current_buffer_imag_min + new_buffer_imag_range

            # Reset the pixel offset to the center of the newly calculated buffer
            current_view_pixel_x = (BUFFER_WIDTH - WIDTH) // 2
            current_view_pixel_y = (BUFFER_HEIGHT - HEIGHT) // 2
            redraw_buffer_required = True # Signal that a new buffer calculation is needed


    # --- Full Buffer Recalculation and Display Update ---
    # This block executes if a zoom action or nearing a buffer edge has occurred.
    if redraw_buffer_required:
        # Temporarily remove the fractal TileGrid and display "Calculating..." message
        group.remove(tile_grid)
        
        # IMPORTANT: Remove the indicator_box_tile_grid from the group
        # so it can be re-added on top later without error, ensuring correct layering.
        group.remove(indicator_box_tile_grid) 
        
        indicator_box_tile_grid.hidden = True # Hide it during calculation

        status_label.text = "Calculating..."
        group.append(text_splash_group)

        # Record time before calculation for performance measurement
        start_time = time.monotonic()
        # Recalculate the entire Mandelbrot buffer for the new complex range
        current_mandelbrot_buffer = calculate_mandelbrot_buffer(
            current_buffer_real_min, current_buffer_real_max,
            current_buffer_imag_min, current_buffer_imag_max
        )
        end_time = time.monotonic()
        calculation_duration = end_time - start_time
        print(f"Image recalculated in {calculation_duration:.2f} seconds.") # Output calculation time

        # Update the TileGrid's bitmap with the newly calculated fractal
        tile_grid.bitmap = current_mandelbrot_buffer

        # Reset the TileGrid position to center the view within the new buffer
        tile_grid.x = -current_view_pixel_x
        tile_grid.y = -current_view_pixel_y

        # Remove the "Calculating..." message and display the updated fractal
        group.remove(text_splash_group)
        group.append(tile_grid)
        
        # Re-append the indicator to ensure it's on top of the main fractal image.
        # This is now safe because it was explicitly removed earlier.
        group.append(indicator_box_tile_grid) 
        indicator_box_tile_grid.hidden = False

        # --- Clear the indicator bitmap and redraw the outer box ---
        # This ensures any previous inner box is removed and the outer box is clean.
        indicator_box_bitmap.fill(0) # Clear to black (palette index 0)
        # Redraw the outer box lines
        for i in range(BOX_SIZE):
            indicator_box_bitmap[i, 0] = 1              # Top border
            indicator_box_bitmap[i, BOX_SIZE - 1] = 1   # Bottom border
            indicator_box_bitmap[0, i] = 1              # Left border
            indicator_box_bitmap[BOX_SIZE - 1, i] = 1   # Right border

        # Reset the last drawn inner box coordinates. The new inner box will be drawn
        # in the next iteration of the main loop based on the fresh view.
        last_inner_box_x = -1
        last_inner_box_y = -1
        last_inner_box_width = -1
        last_inner_box_height = -1


    # --- Update Position Indicator Box Visuals Every Frame (Box within a Box) ---
    # Calculate current inner box dimensions and position relative to BOX_SIZE
    # These represent the visible screen portion within the overall buffer
    
    # Scale screen dimensions to fit within the BOX_SIZE indicator
    # Ensure a minimum size of 1 pixel
    current_inner_box_width = max(1, int(WIDTH * BOX_SIZE / BUFFER_WIDTH))
    current_inner_box_height = max(1, int(HEIGHT * BOX_SIZE / BUFFER_HEIGHT))

    # Scale current view's top-left pixel coordinates to fit within the BOX_SIZE indicator
    current_inner_box_x = int(current_view_pixel_x * BOX_SIZE / BUFFER_WIDTH)
    current_inner_box_y = int(current_view_pixel_y * BOX_SIZE / BUFFER_HEIGHT)

    # Clamp the inner box position to ensure it stays within the outer BOX_SIZE boundaries
    current_inner_box_x = max(0, min(current_inner_box_x, BOX_SIZE - current_inner_box_width))
    current_inner_box_y = max(0, min(current_inner_box_y, BOX_SIZE - current_inner_box_height))

    # Update the inner box only if its position or size has changed
    if (current_inner_box_x != last_inner_box_x or
        current_inner_box_y != last_inner_box_y or
        current_inner_box_width != last_inner_box_width or
        current_inner_box_height != last_inner_box_height):

        # If a previous inner box was drawn, clear its old position (draw with black, palette index 0)
        # This check is still necessary for normal panning movement between recalculations.
        if last_inner_box_x != -1:
            draw_rectangle_perimeter(indicator_box_bitmap, 
                                     last_inner_box_x, last_inner_box_y,
                                     last_inner_box_width, last_inner_box_height, 0) # Clear with black

        # Draw the new inner box (draw with white, palette index 1)
        draw_rectangle_perimeter(indicator_box_bitmap, 
                                 current_inner_box_x, current_inner_box_y,
                                 current_inner_box_width, current_inner_box_height, 1) # Draw with white

        # Store current inner box position and size for the next iteration
        last_inner_box_x = current_inner_box_x
        last_inner_box_y = current_inner_box_y
        last_inner_box_width = current_inner_box_width
        last_inner_box_height = current_inner_box_height

    # Small delay to prevent the loop from consuming all CPU cycles unnecessarily
    time.sleep(0.01)
import board
import displayio
import time
import digitalio
import random
import keypad # Import the keypad module

# --- Configuration ---
# Get the display width and height directly from the board's display object.
# For Adafruit PyGamer, this is typically 160x128 pixels.
DISPLAY_WIDTH = board.DISPLAY.width
DISPLAY_HEIGHT = board.DISPLAY.height

# Define the size of each Conway's Game of Life cell in pixels.
# Setting this to a value greater than 1 makes cells larger and reduces memory usage
# by decreasing the size of the logical game grid.
CELL_PIXEL_SIZE = 4 # Example: 4x4 pixels per logical cell

# Calculate the logical dimensions of the game grid based on display resolution
# and cell pixel size. This is the size of our 'grid' array.
WIDTH = DISPLAY_WIDTH // CELL_PIXEL_SIZE
HEIGHT = DISPLAY_HEIGHT // CELL_PIXEL_SIZE

# Initial percentage of live cells when the simulation starts.
# This is set to 25% to stay well within the requested maximum of 30%.
INITIAL_LIVE_PERCENTAGE = 0.25

# Minimum and maximum time (in seconds) between generations.
# These control the simulation speed.
MIN_DELAY = 0.05  # Faster updates
MAX_DELAY = 1.0   # Slower updates

# The amount by which the delay changes with each A or B button press.
DELAY_STEP = 0.05

# Time (in seconds) to wait after a button press to prevent multiple activations
# from a single, prolonged press (debouncing).
BUTTON_DEBOUNCE_TIME = 0.1

# Define the number of generations after which the grid will reinitialize.
GENERATIONS_UNTIL_REINITIALIZE = 150

# --- Helper Function for Random Color ---
def get_random_bright_color():
    """
    Generates a random 24-bit RGB color.
    Each component (Red, Green, Blue) is generated with a minimum value
    to ensure the resulting color is not too dark and is visible on the display.
    """
    # Generate random R, G, B components (0-255).
    # Starting at 50 to ensure some brightness and avoid pure black.
    r = random.randint(50, 255)
    g = random.randint(50, 255)
    b = random.randint(50, 255)
    # Combine the RGB components into a single 24-bit hexadecimal color value.
    return (r << 16) | (g << 8) | b

# --- Display Setup ---
# Get the main display object for the PyGamer.
display = board.DISPLAY

# Create a displayio.Group. This is a container for display elements.
# We will add our game grid to this group.
splash = displayio.Group()

# Show the created splash group on the display. Anything added to 'splash'
# will then become visible.
# .show(x) was removed in newer displayio, use .root_group = x instead.
display.root_group = splash

# Create a displayio.Bitmap object. This is like a canvas for drawing pixels.
# It uses the full display dimensions.
color_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 2)

# Create a displayio.Palette object. This defines the actual colors for the bitmap.
# Index 0 of the palette will be used for 'dead' cells, and index 1 for 'alive' cells.
palette = displayio.Palette(2)
palette[0] = 0x000000  # Black color (hex code) for dead cells
# palette[1] will be set with a random color during initialization

# Create a displayio.TileGrid. This is used to display the bitmap on the screen.
# It takes the bitmap and the pixel_shader (our palette) as arguments.
tile_grid = displayio.TileGrid(color_bitmap, pixel_shader=palette)

# Add the tile_grid to the 'splash' group. This makes our game grid visible on the screen.
splash.append(tile_grid)

# --- Button Setup with keypad.ShiftRegisterKeys ---
# Define the button numbers for the PyGamer's ShiftRegisterKeys.
# These correspond to the indices in the shift register's output.
PYGAMER_BUTTON_A = 0 # Typically for decreasing delay (Button A on PyGamer)
PYGAMER_BUTTON_B = 1 # Typically for increasing delay (Button B on PyGamer)

# Configure the PyGamer's ShiftRegisterKeys for button input.
# The PyGamer's built-in buttons (A and B) are internally wired to a shift register,
# and these are the correct board pins to interface with it using the keypad module.
buttons = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8, # Total number of keys on the shift register (PyGamer has more than A/B)
    value_when_pressed=False # Buttons are active low (pull to ground when pressed)
)

# --- Game State ---
# Initialize the 2D grid that holds the state of each cell in Conway's Game of Life.
# `grid[y][x]` stores the state of the cell at column `x` and row `y`.
# 0 represents a dead cell, 1 represents a live cell.
# The dimensions are now based on WIDTH and HEIGHT calculated using CELL_PIXEL_SIZE.
grid = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

# Set the initial time delay between generations. This can be adjusted by buttons.
delay_time = 0.2

# Initialize a counter for the current generation.
generation_count = 0

# --- Game Functions ---

def initialize_grid(grid_data):
    """
    Randomly initializes the `grid_data` with live cells at the beginning of the simulation.
    This version avoids creating large intermediate lists to prevent MemoryError.
    It sets each cell to live with a probability equal to INITIAL_LIVE_PERCENTAGE.
    """
    live_cells_count = 0
    total_cells = WIDTH * HEIGHT # Calculate total logical cells

    for y in range(HEIGHT): # Iterate over logical grid height
        for x in range(WIDTH): # Iterate over logical grid width
            # Set the cell to alive based on a random probability.
            # This is more memory efficient than shuffling a large list of coordinates.
            if random.random() < INITIAL_LIVE_PERCENTAGE:
                grid_data[y][x] = 1
                live_cells_count += 1
            else:
                grid_data[y][x] = 0

    # Fallback: Ensure at least one cell is alive if no cells were set initially (very rare).
    if live_cells_count == 0 and total_cells > 0:
        grid_data[random.randint(0, HEIGHT-1)][random.randint(0, WIDTH-1)] = 1


def count_live_neighbors(grid_data, x, y):
    """
    Counts the number of live neighbors for a given cell at `(x, y)` in `grid_data`.
    This function implements toroidal (wrapping) boundary conditions, meaning cells
    on the edges of the grid connect to cells on the opposite edge.
    """
    count = 0
    # Iterate through the 3x3 neighborhood around the cell (including the cell itself).
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            # Skip the cell itself; we only count its neighbors.
            if dx == 0 and dy == 0:
                continue
            
            # Calculate the neighbor's coordinates (`nx`, `ny`) with toroidal wrapping.
            # The modulo operator (%) ensures that coordinates wrap around the grid
            # (e.g., if x+dx goes beyond WIDTH, it wraps back to 0).
            nx, ny = (x + dx) % WIDTH, (y + dy) % HEIGHT
            
            # Add the neighbor's state (0 if dead, 1 if alive) to the count.
            count += grid_data[ny][nx]
    return count

def update_grid(current_grid):
    """
    Calculates the next generation of the Game of Life grid based on `current_grid`
    and Conway's four rules.
    Returns a new grid representing the state of the next generation.
    """
    # Create a new grid (`new_grid`) to store the state of the next generation.
    # It's crucial to create a new grid because all cell updates for a given
    # generation must be based on the *current* state simultaneously. If we
    # updated `current_grid` directly, changes would affect neighbor calculations
    # for cells later in the same iteration, which is incorrect.
    new_grid = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
    
    for y in range(HEIGHT):
        for x in range(WIDTH):
            cell_state = current_grid[y][x] # Get the current state of the cell (0 or 1)
            live_neighbors = count_live_neighbors(current_grid, x, y) # Count live neighbors

            if cell_state == 1: # If the current cell is alive:
                # Conway's Rule 1: Any live cell with fewer than two live neighbours dies (underpopulation).
                # Conway's Rule 3: Any live cell with more than three live neighbours dies (overpopulation).
                if live_neighbors < 2 or live_neighbors > 3:
                    new_grid[y][x] = 0 # Cell dies
                else:
                    # Conway's Rule 2: Any live cell with two or three live neighbours lives on to the next generation.
                    new_grid[y][x] = 1 # Cell lives
            else: # If the current cell is dead:
                # Conway's Rule 4: Any dead cell with exactly three live neighbours becomes a live cell (reproduction).
                if live_neighbors == 3:
                    new_grid[y][x] = 1 # Cell becomes alive
                else:
                    # If dead and not exactly 3 neighbors, it stays dead.
                    new_grid[y][x] = 0
    return new_grid

def draw_grid(grid_data):
    """
    Updates the display bitmap (`color_bitmap`) based on the current state
    of the `grid_data`, drawing each logical cell as a square of CELL_PIXEL_SIZE.
    """
    for y_logical in range(HEIGHT): # Iterate through logical rows of the game grid
        for x_logical in range(WIDTH): # Iterate through logical columns of the game grid
            cell_state = grid_data[y_logical][x_logical] # Get the state of the current logical cell
            
            # Calculate the top-left pixel coordinates for the current logical cell on the display
            start_pixel_x = x_logical * CELL_PIXEL_SIZE
            start_pixel_y = y_logical * CELL_PIXEL_SIZE

            # Draw a square of CELL_PIXEL_SIZE x CELL_PIXEL_SIZE pixels for this logical cell
            for dy_pixel in range(CELL_PIXEL_SIZE):
                for dx_pixel in range(CELL_PIXEL_SIZE):
                    # Calculate the absolute pixel coordinates on the color_bitmap
                    pixel_x = start_pixel_x + dx_pixel
                    pixel_y = start_pixel_y + dy_pixel
                    
                    # Set the pixel in the bitmap to the color corresponding to the cell's state
                    # We use cell_state (0 or 1) directly as the index for the palette.
                    color_bitmap[pixel_x, pixel_y] = cell_state

# --- Main Program Execution ---

# Set initial random color for live cells before the first grid initialization
palette[1] = get_random_bright_color()

# 1. Initialize the game grid with a random distribution of live cells.
initialize_grid(grid)

# 2. Draw the initial state of the grid on the PyGamer's display.
draw_grid(grid)

# This is the main game loop that runs continuously.
while True:
    # --- Handle Button Events ---
    # Get any pending button events from the keypad.
    event = buttons.events.get()
    
    if event: # If an event occurred (button pressed or released)
        if event.pressed: # Check if the event was a button press
            if event.key_number == PYGAMER_BUTTON_A:
                # Decrease the `delay_time`. `max()` ensures it doesn't go below `MIN_DELAY`.
                delay_time = max(MIN_DELAY, delay_time - DELAY_STEP)
                # Print the updated delay time to the serial console for feedback.
                print(f"Delay decreased to: {delay_time:.2f} seconds")
            elif event.key_number == PYGAMER_BUTTON_B:
                # Increase the `delay_time`. `min()` ensures it doesn't exceed `MAX_DELAY`.
                delay_time = min(MAX_DELAY, delay_time + DELAY_STEP)
                # Print the updated delay time to the serial console for feedback.
                print(f"Delay increased to: {delay_time:.2f} seconds")
        # No need for time.sleep(BUTTON_DEBOUNCE_TIME) here, as keypad.events handles debouncing.

    # --- Game Logic Update ---
    # Calculate the next generation of the grid based on Conway's rules.
    # The `update_grid` function returns a brand new grid, which then becomes the current `grid`.
    grid = update_grid(grid)
    
    # Increment the generation counter.
    generation_count += 1
    
    # Check if it's time to reinitialize the grid.
    if generation_count >= GENERATIONS_UNTIL_REINITIALIZE:
        print(f"Reinitializing grid after {GENERATIONS_UNTIL_REINITIALIZE} generations.")
        # Generate a new random color for the next set of generations and update the palette.
        palette[1] = get_random_bright_color()
        initialize_grid(grid) # Reinitialize the grid with a new random pattern
        generation_count = 0 # Reset the generation counter
    
    # --- Display Update ---
    # Draw the newly calculated grid state onto the PyGamer's display.
    draw_grid(grid)
    
    # --- Time Delay ---
    # Pause for the specified `delay_time` before proceeding to the next generation.
    # This controls the speed of the simulation.
    time.sleep(delay_time)

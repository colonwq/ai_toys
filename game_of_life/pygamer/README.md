# Conway's Game of Life on Adafruit PyGamer

This CircuitPython script implements Conway's Game of Life, a zero-player game, on the Adafruit PyGamer. The simulation runs autonomously, displaying cellular patterns on the PyGamer's built-in LCD. Users can interact with the simulation by adjusting its speed and observing new patterns as the grid periodically reinitializes with a fresh set of random cells and a new color.

## Functionality

The script simulates Conway's Game of Life using a grid of cells that evolve based on a set of simple rules:

1. Any live cell with fewer than two live neighbours dies, as if by underpopulation.

1. Any live cell with two or three live neighbours lives on to the next generation.

1. Any live cell with more than three live neighbours dies, as if by overpopulation.

1. Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.

The simulation runs in an infinite loop, continuously calculating and displaying new generations.

## Features

- Conway's Game of Life Simulation: A classic cellular automaton running directly on your PyGamer.

- Adjustable Cell Size: Configurable CELL_PIXEL_SIZE allows for larger, more visible cells, which also helps reduce memory usage.

- Variable Simulation Speed:

  - Pressing Button A (mapped to PYGAMER_BUTTON_A) decreases the delay between generations, speeding up the simulation.

  - Pressing Button B (mapped to PYGAMER_BUTTON_B) increases the delay between generations, slowing down the simulation.

- Status messages are printed to the serial console to indicate speed changes.

- Periodic Reinitialization: The entire grid of cells is reinitialized with a new random pattern every 150 generations, preventing the simulation from getting stuck in static or oscillating patterns indefinitely.

- Dynamic Cell Coloring: Upon each reinitialization, live cells are assigned a new, randomly generated bright color, adding visual variety to the simulation.

- Memory Optimized: The script uses techniques like larger cell pixel sizes and probabilistic grid initialization to manage memory effectively on the PyGamer's limited resources.

- Robust Button Handling: Utilizes the keypad.ShiftRegisterKeys module for reliable and debounced button input.

## How to Use

1. Hardware: Ensure you have an Adafruit PyGamer.

1. CircuitPython: Make sure your PyGamer is running CircuitPython. You can download the latest stable version from the CircuitPython Downloads page.

1. Libraries: Copy the necessary CircuitPython libraries to the lib folder on your PyGamer's CIRCUITPY drive. At minimum, you will need:

   - adafruit_busio

   - adafruit_displayio_sh1107 (or similar for your display)

   - digitalio

   - keypad

1. Upload Script: Save the provided Python code as code.py in the root directory of your PyGamer's CIRCUITPY drive.

1. Run: The PyGamer will automatically run the code.py script upon boot. Connect to the serial console (e.g., using PuTTY, CoolTerm, or the built-in serial monitor in Mu Editor) to see the delay status messages.

## Initial Prompt

This script was generated based on the following initial request:

"Create a circuitpython script for the adafruit pygammer, this script will implement conways game of life. No more than 30% of the pixels should be used for the initial cells. The A and B buttons should be used to lengthen or shorten the time between generations."

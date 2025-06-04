# CircuitPython Mandelbrot Viewer for Adafruit PyGamer

Please write a CircuitPython program for an Adafruit PyGamer that displays a Mandelbrot fractal.

The program should include the following features:

## Display & Core Functionality

- Display Setup: Initialize the PyGamer's display and set up a main displayio.Group to manage all on-screen elements.

- Mandelbrot Calculation: Implement a mandelbrot function that determines if a given complex number is within the Mandelbrot set. This function should return the number of iterations taken to diverge (or MAX_ITER if it converges).
- Color Palette: Define a displayio.Palette with MAX_ITER = 30 entries. The colors should transition gradually from reds for lower iterations, to greens, and then to blues for higher iterations. Points that remain within the set (reaching MAX_ITER) should be colored black (0x000000).
## Buffered Panning & Movement
- Buffered Image: The fractal should be calculated into a displayio.Bitmap that is 1.5 times wider and taller than the PyGamer's screen dimensions (BUFFER_FACTOR = 1.5). This larger bitmap will serve as a buffer for smooth panning.
- Initial View: The program should start with the fractal centered at (-0.5, 0.0) in the complex plane, with an initial screen real range of 3.0. The display should initially show the center portion of the buffered image.
- Joystick Panning: Implement smooth panning control using the PyGamer's analog joystick.

  Set a JOYSTICK_DEADZONE of 5000 to prevent unintended movement from slight joystick drift.S

  Define a PAN_PIXEL_SPEED of 1 pixel per joystick movement tick to control the panning responsiveness.

- Dynamic Recalculation: When the currently displayed view approaches within 10% of the buffered image's edge (BUFFER_EDGE_THRESHOLD), trigger a full recalculation of the fractal. The new buffered image should be centered around the current screen's complex coordinates, ensuring a seamless and continuous exploration experience.
- Zoom Functionality

  Zoom Controls: Allow users to zoom in and zoom out using the PyGamer's A and B buttons (accessed via keypad.ShiftRegisterKeys using PYGAMER_BUTTON_A = 0 and PYGAMER_BUTTON_B = 1).
  
  Zoom Factor: Apply a ZOOM_FACTOR of 1.1 for each zoom operation. When zooming, recalculate the fractal into a new buffer based on the new, zoomed-in or zoomed-out complex range.

# User Experience

- Calculating Status: Display a prominent "Calculating..." message using adafruit_display_text.label whenever the fractal is being calculated or recalculated, providing clear feedback to the user during processing times.

# Libraries

Ensure all necessary CircuitPython libraries, including ```board, displayio, terminalio, adafruit_display_text.label, time, analogio, and keypad```, are imported.
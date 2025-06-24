# CircuitPython Simple Simon Game for Adafruit Macropad

This repository contains a CircuitPython script that transforms your Adafruit Macropad RP2040 into a classic Simple Simon memory game. It leverages the Macropad's 12-key keypad, NeoPixel LEDs, built-in speaker, and OLED display to provide an engaging and interactive game experience.

## Features

- 12-Key Simon Game: Utilizes all 12 keys of the Macropad for game input.

- Unique LED Colors: Each key is assigned a distinct NeoPixel LED color, which illuminates when the key is part of the sequence or pressed by the player.

- Distinct Tones: Each key has a unique audio tone, played when its corresponding LED lights up.

- OLED Display for Game Stats: The built-in OLED screen provides real-time feedback:

- Current: Displays the length of the current sequence.

- Max: Shows the highest sequence length achieved in the current game session.

- Status Messages: Guides the player with messages like "Press any key to start!", "Watch the sequence!", "Your turn!", "Correct!", and "Wrong! Game Over".

- Game Logic: Implements the core Simon game mechanics:

  - Generates random sequences of increasing length.

  - Plays the sequence for the player to memorize.

  - Waits for player input and checks for correctness.

  - Provides visual and auditory feedback for correct and incorrect moves.

  - Tracks and displays the maximum level achieved.

- Responsive Feedback: Quick visual and auditory feedback on key presses.

## Hardware Requirements

- Adafruit Macropad RP2040

U- SB-C cable for connecting to your computer

## Software Requirements

- CircuitPython firmware installed on your Adafruit Macropad RP2040 (version 7.x or newer recommended).

- CircuitPython Library Bundle (latest version compatible with your CircuitPython firmware). Ensure the following libraries are copied to the lib folder on your Macropad's CIRCUITPY drive:

- adafruit_macropad.mpy (or the entire adafruit_macropad folder)

- adafruit_display_text

- terminalio (usually built-in)

- displayio (usually built-in)

## Installation

- Connect Macropad: Connect your Adafruit Macropad to your computer using a USB-C cable. It should appear as a drive named CIRCUITPY.

- Copy code.py: Copy the code.py file (the script provided previously) directly into the root directory of your CIRCUITPY drive.

- Copy Libraries: If you haven't already, ensure all required CircuitPython libraries (listed above) are copied into the lib folder on your CIRCUITPY drive.

- Restart/Save: The Macropad will automatically restart and begin running the code.py script once the file is saved.

## How to Play

Start Game: When the Macropad powers on or the script restarts, the OLED display will show "Press any key to start!". Press any of the 12 keys to begin.

Watch the Sequence: The game will display a sequence by lighting up keys and playing their corresponding tones. The OLED will show "Watch the sequence!".

Your Turn: Once the sequence has played, the OLED will change to "Your turn!". Now, you must press the keys in the exact same order as the game just demonstrated.

Advance Levels: If you correctly repeat the sequence, the OLED will briefly show "Correct!", and the current level will increase. The game will then add another step to the sequence and present a longer pattern.

Game Over: If you press an incorrect key or fail to complete the sequence within the allotted time, the LEDs will flash red, a failure tone will play, and the OLED will display "Wrong! Game Over". Your maximum achieved level will be preserved.

Restart Game: To play again after a "Game Over", simply press any key on the Macropad.

## Customization

You can easily customize aspects of the game by modifying the code.py file:

- KEY_COLORS: Change the RGB hexadecimal values in this list to alter the LED colors for each key.

- KEY_TONES: Adjust the frequency values in this list to change the pitch of each key's tone.

- TONE_DURATION_MS: Modify this value to make the tones and LED flashes longer or shorter.

- timeout (in get_player_input function): Adjust the expected_length * 5 factor to give players more or less time per key to input the sequence.

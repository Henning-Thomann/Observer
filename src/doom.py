import os
from random import choice
from time import sleep

from tinkerforge.bricklet_dual_button_v2 import BrickletDualButtonV2
from tinkerforge.bricklet_lcd_128x64 import BrickletLCD128x64
from tinkerforge.bricklet_rgb_led_button import BrickletRGBLEDButton
from tinkerforge.ip_connection import IPConnection
import vizdoom as vzd
import numpy as np
import cv2

from PIL import Image

def scale_and_dither(image_array, depth_array, new_size=(128, 64), depth_intensity=-0.5, depth_boost=1):
    """Transforms an RGB image by enhancing red/blue saturation, adjusting contrast based on depth, resizing, and dithering to black & white."""

    def adjust_depth_based_on_color(image, depth_buffer, boost_factor=10):
        """Modifies the depth buffer to make strongly red/blue objects appear closer."""

        # Convert image to HSV for better color detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Identify strong red & blue regions
        blue_mask = ((h > 110) & (h < 125)).astype(np.uint8)
        color_mask =  blue_mask

        # Reduce depth values where red/blue objects are detected (make them "closer")
        adjusted_depth = depth_buffer - (color_mask * boost_factor * depth_buffer.max())
        adjusted_depth = np.clip(adjusted_depth, depth_buffer.min(), depth_buffer.max())

        return adjusted_depth

    # 1. Enhance red and blue saturation
    def enhance_red_blue(image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Detect strong red & blue areas
        red_mask = ((h < 10) | (h > 170)).astype(np.uint8)
        blue_mask = ((h > 100) & (h < 130)).astype(np.uint8)
        color_mask = red_mask | blue_mask

        # Boost saturation **and brightness**
        s = cv2.subtract(s, (red_mask * 10).astype(np.uint8))  # Increase saturation
        v = cv2.subtract(v, (red_mask * 8).astype(np.uint8))  # Boost brightness

        boosted_hsv = cv2.merge([h, s, v])
        return cv2.cvtColor(boosted_hsv, cv2.COLOR_HSV2BGR)

    depth_array = adjust_depth_based_on_color(image_array, depth_array)

    # 2. Normalize depth values for contrast adjustments
    depth_array = depth_array.astype(np.float32)
    depth_array = (depth_array - depth_array.min()) / (depth_array.max() - depth_array.min())

    # Match depth array shape with image_array
    depth_array_3ch = np.repeat(depth_array[:, :, np.newaxis], 3, axis=2)

    # Adjust brightness: closer objects are brighter, farther objects are darker
    adjusted_img = image_array.astype(np.float32) + (255 * depth_intensity * depth_array_3ch)
    adjusted_img = np.clip(adjusted_img, 0, 255).astype(np.uint8)

    boosted = enhance_red_blue(adjusted_img)
    # 3. Convert to grayscale, emphasizing closer objects
    gray_img = cv2.cvtColor(boosted, cv2.COLOR_BGR2GRAY)

    # Enhance contrast based on depth (boosting closer objects)
    enhanced_gray = cv2.addWeighted(gray_img, 1.0 + depth_boost, (depth_array * 255).astype(np.uint8), -depth_boost, 0)

    # Resize
    resized_img = cv2.resize(enhanced_gray, new_size, interpolation=cv2.INTER_LANCZOS4)

    # 4. Apply dithering to create binary (black & white) image
    image_pil = Image.fromarray(resized_img).convert("L")
    dithered_img = image_pil.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

    return np.array(dithered_img, dtype=bool)  # Convert to boolean array


IP = "172.20.10.242"
PORT = 4223

def main(conn):
    #          FWD    LEFT   RIGHT  FIRE
    actions = [False, False, False, False]
    lcd = BrickletLCD128x64("24Rh", conn);
    fire_button = BrickletRGBLEDButton("23Qx", conn)
    dual_button = BrickletDualButtonV2("Vd8", conn)

    def motion_callback(left, right, _left_led, _right_led):
        print("aaaaaaaah")
        actions[1] = left == BrickletDualButtonV2.BUTTON_STATE_PRESSED
        actions[2] = right == BrickletDualButtonV2.BUTTON_STATE_PRESSED


    def fire_callback(state):
        print(state)
        actions[3] = state == fire_button.BUTTON_STATE_PRESSED

    conn.connect(IP, PORT)

    fire_button.register_callback(fire_button.CALLBACK_BUTTON_STATE_CHANGED, fire_callback)
    dual_button.register_callback(dual_button.CALLBACK_STATE_CHANGED, motion_callback)
    dual_button.set_state_changed_callback_configuration(True)
    print(dual_button.get_led_state())

    game = vzd.DoomGame()


    game.set_doom_scenario_path(os.path.join(vzd.scenarios_path, "basic.wad"))
    game.set_doom_map("map01")
    game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
    game.set_screen_format(vzd.ScreenFormat.RGB24)

    game.set_depth_buffer_enabled(True)
    game.set_labels_buffer_enabled(True)
    game.set_automap_buffer_enabled(True)

    game.set_objects_info_enabled(True)

    game.set_sectors_info_enabled(True)

    game.set_render_hud(False)
    game.set_render_minimal_hud(False)
    game.set_render_crosshair(False)
    game.set_render_weapon(True)
    game.set_render_decals(False)
    game.set_render_particles(False)
    game.set_render_effects_sprites(False)
    game.set_render_messages(False)
    game.set_render_corpses(False)
    game.set_render_screen_flashes(
        True
    )

    game.set_available_buttons(
        [vzd.Button.MOVE_FORWARD,
         vzd.Button.MOVE_LEFT,
         vzd.Button.MOVE_RIGHT,
         vzd.Button.ATTACK
         ]
    )
    print("Available buttons:", [b.name for b in game.get_available_buttons()])

    game.set_available_game_variables([vzd.GameVariable.AMMO2])
    print(
        "Available game variables:",
        [v.name for v in game.get_available_game_variables()],
    )

    # Causes episodes to finish after 200 tics (actions)
    game.set_episode_timeout(200)

    # Makes episodes start after 10 tics (~after raising the weapon)
    game.set_episode_start_time(10)

    # Makes the window appear (turned on by default)
    game.set_window_visible(True)

    # Turns on the sound. (turned off by default)
    # game.set_sound_enabled(True)
    # Because of some problems with OpenAL on Ubuntu 20.04, we keep this line commented,
    # the sound is only useful for humans watching the game.

    # Turns on the audio buffer. (turned off by default)
    # If this is switched on, the audio will stop playing on device, even with game.set_sound_enabled(True)
    # Setting game.set_sound_enabled(True) is not required for audio buffer to work.
    # game.set_audio_buffer_enabled(True)
    # Because of some problems with OpenAL on Ubuntu 20.04, we keep this line commented.

    # Sets the living reward (for each move) to -1
    game.set_living_reward(-1)

    # Sets ViZDoom mode (PLAYER, ASYNC_PLAYER, SPECTATOR, ASYNC_SPECTATOR, PLAYER mode is default)
    game.set_mode(vzd.Mode.PLAYER)

    # Enables engine output to console, in case of a problem this might provide additional information.
    # game.set_console_enabled(True)

    # Initialize the game. Further configuration won't take any effect from now on.
    game.init()

    # Define some actions. Each list entry corresponds to declared buttons:
    # MOVE_LEFT, MOVE_RIGHT, ATTACK
    # game.get_available_buttons_size() can be used to check the number of available buttons.
    # 5 more combinations are naturally possible but only 3 are included for transparency when watching.

    # Run this many episodes
    episodes = 10

    # Sets time that will pause the engine after each action (in seconds)
    # Without this everything would go too fast for you to keep track of what's happening.
    sleep_time = 1.0 / vzd.DEFAULT_TICRATE  # = 0.028

    for i in range(episodes):
        print(f"Episode #{i + 1}")

        # Starts a new episode. It is not needed right after init() but it doesn't cost much. At least the loop is nicer.
        game.new_episode()

        tick = 0
        while not game.is_episode_finished():

            # Gets the state
            state = game.get_state()

            # Which consists of:
            n = state.number
            vars = state.game_variables

            # Different buffers (screens, depth, labels, automap, audio)
            # Expect of screen buffer some may be None if not first enabled.
            screen_buf = state.screen_buffer
            depth_buf = state.depth_buffer
            labels_buf = state.labels_buffer
            automap_buf = state.automap_buffer
            audio_buf = state.audio_buffer

            # List of labeled objects visible in the frame, may be None if not first enabled.
            labels = state.labels

            # List of all objects (enemies, pickups, etc.) present in the current episode, may be None if not first enabled
            objects = state.objects

            # List of all sectors (map geometry), may be None if not first enabled.
            sectors = state.sectors

            black_white = scale_and_dither(state.screen_buffer, state.depth_buffer)

            black_white_flat = [bool(pixel) for lines in black_white for pixel in lines]
            # print(black_white_flat)
            # if tick % 60 == 0:
            #     lcd.clear_display()
            #     lcd.write_pixels(0, 0, 127, 63, black_white_flat)
            # tick += 1
            # Games variables can be also accessed via
            # (including the ones that were not added as available to a game state):
            # game.get_game_variable(GameVariable.AMMO2)

            # Makes an action (here random one) and returns a reward.
            r = game.make_action(actions)

            # Makes a "prolonged" action and skip frames:
            # skiprate = 4
            # r = game.make_action(choice(actions), skiprate)

            # The same could be achieved with:
            # game.set_action(choice(actions))
            # game.advance_action(skiprate)
            # r = game.get_last_reward()

            if sleep_time > 0:
                sleep(sleep_time)

        # Check how the episode went.
        print("Episode finished.")
        print("Total reward:", game.get_total_reward())
        print("************************")

    # It will be done automatically anyway but sometimes you need to do it in the middle of the program...
    game.close()

if __name__ == "__main__":
    conn = IPConnection()
    try:
        main(conn)
    finally:
        conn.disconnect()

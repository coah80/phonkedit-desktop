# Phonk Edit Desktop# PhonkEdit Desktop

# yes i did use ai for a read me!

Windows desktop click-triggered phonk edit: on any mouse click, it grabs all monitors, applies a moody grayscale, pops an on-screen overlay per monitor, and plays a random phonk track. The overlay stays up until the track finishes.A tiny Windows tool that listens for global mouse clicks and, on each click or right-click, takes a screenshot of every monitor and applies the Phonk Edit grayscale + skull overlay while playing a random phonk track.



## Features## What it does

- Global left/right click trigger (polling; no drivers required)- Adds a system tray icon using a skull

- Multi-monitor screenshots with grayscale/contrast/brightness mix- Left-click the tray icon or choose "Phonk Now" in the menu

- On-screen overlay windows per monitor (always-on-top)- Captures all monitors, applies grayscale + skulls, saves to `output/`

- Separate layers: background screenshot and skull (skull is its own overlay layer)- Plays a random built-in phonk track (`.ogg`)

- Phonk audio playback, overlay lifetime tied to audio

- Configurable timing and skull size/placement via `config.json`## One-time setup (Windows PowerShell)

```powershell

## Setuppython -m venv .venv

1. Install Python 3.11+ (tested on 3.13 on Windows).. .venv\Scripts\Activate.ps1

2. Install dependencies:pip install -r requirements.txt

   - `pip install -r requirements.txt````

3. Optional: set `PHONKEDIT_ASSETS_ROOT` to point to your mod assets root (auto-copies skulls and phonk audio on first run). If not set, put your assets here:

   - `assets/skulls/` — PNG files named like `skull*.png`## Run

   - `assets/phonk/` — OGG files named like `phonk*.ogg````powershell

. .venv\Scripts\Activate.ps1

## Runpython .\main.py

- `python main.py````

- Click anywhere (left or right) to trigger.

- The overlay closes when the music ends.- Leave the window running; every mouse click triggers the effect

- Processed images are saved under `output\` with timestamps

## Configuration (`config.json`)- Press Ctrl+C in the terminal to exit

A `config.json` is created on first run with defaults. You can tweak these values:

## Assets

- `click_delay_ms` (default 300)If `assets/skulls` and `assets/phonk` are empty, the app tries to auto-copy from the mod resources when available.

  Wait after the click before capturing, in milliseconds. Useful so the screenshot reflects the click action.

Set this environment variable to point directly at the mod assets root (folder containing `textures` and `sounds`):

- `min_cooldown_ms` (default 200)

  Minimum gap between triggers, in milliseconds.```powershell

$env:PHONKEDIT_ASSETS_ROOT = "G:\phonkedit\src\main\resources\assets\phonkedit"

- `skull_size_ratio` (default 0.18)```

  Skull width as a fraction of the monitor width. Height scales to preserve aspect ratio.

It will look for:

- `skull_offset_y_ratio` (default 0.66)- Skulls: `<PHONKEDIT_ASSETS_ROOT>\textures\gui\skull*.png`

  Vertical position of the skull as a fraction of monitor height (0 = top, 1 = bottom). 0.66 puts it around the lower third.- Audio: `<PHONKEDIT_ASSETS_ROOT>\sounds\phonk\phonk*.ogg`



Restart not required; changes are read on launch.Or manually place files into:

- `assets/skulls/`

## Notes- `assets/phonk/`

- Overlays are Tkinter top-level windows and will appear on each monitor at the captured resolution and position.

- Skull is drawn as a separate canvas layer so it can be animated independently in the future.## Notes

- If you hear phonk but don’t see overlays, check that OGG files exist and that your Python can create Tkinter windows (some RDP setups restrict this).- This app stays in the system tray; use the menu to exit

- Audio output uses your default device
- If you have many monitors or large resolutions, image processing may take a second

### Typing trigger (less frequent)

You can also trigger the effect while typing. By default it’s much less common than clicks. Configure via these options in `config.json`:

- `typing_enabled` (default true)
  Enable/disable typing as a trigger source.

- `typing_min_cooldown_ms` (default 3000)
  Minimum time between typing-based triggers, in milliseconds.

- `typing_trigger_chance` (default 0.07)
  Probability per keypress to trigger (0.0 to 1.0). Lower values mean rarer effects while typing.

### Skull-only shake

Skulls are drawn on a separate overlay layer and can shake independently from the screenshot background. Configure via:

- `skull_shake_enabled` (default true)
  Toggle skull-only animation.

- `skull_shake_amplitude_px` (default 5)
  How many pixels the skull moves around its base position.

- `skull_shake_speed_hz` (default 9.0)
  Oscillation speed (cycles per second).

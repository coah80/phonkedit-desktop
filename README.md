phonkedit-desktop
=================

if u like this, try out the minecraft equivalent, or support me on ko-fi.com
-----------------------------------------

https://www.curseforge.com/mods/phonkedit 
https://www.modrinth.com/mod/phonk-edit 
https://ko-fi.com/coah

What this is
-------------
phonkedit-desktop is a small Python desktop utility that captures your screen(s), applies a stylized "phonk" filter, optionally overlays skull art, and plays a random phonk audio track. It is designed to run locally and save capture outputs to the `output/` directory.

Prerequisites
-------------
- Python 3.8 or newer (3.10+ recommended)
- Git (optional, for cloning)
- The Python packages listed in `requirements.txt` (Pillow, mss, pygame). Tkinter is required for overlays — it is included with standard Python installs on most platforms.

Bundled dependency versions (as provided in this repo)
---------------------------------------------------
- pillow==10.4.0
- mss==9.0.1
- pygame==2.6.1

Files and important paths
-------------------------
- `main.py` — main program entrypoint. Run with `python main.py`.
- `config.json` — created on first run when missing. Edit to change timing, skull sizing, triggers, etc.
- `assets/` — put your files here:
	- `assets/phonk/` — OGG audio tracks (the app will pick a random .ogg to play)
	- `assets/skulls/` — PNG skull images used for overlays
- `output/` — per-run session folders and images are saved here.

Running (macOS / Linux)
-----------------------
1. Create and activate a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python main.py
```

Running (Windows — PowerShell)
-----------------------------
1. Create and activate a virtual environment and install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell prevents activation because of execution policy, run (as user):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

2. Run the app:

```powershell
python main.py
```

Running (Windows — CMD)
-----------------------
```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

How it behaves
--------------
- On startup it ensures `assets/` subfolders exist and writes `config.json` if missing.
- When triggered (mouse click or occasional typing event), it captures all monitors, applies the filter, saves images to `output/session_<timestamp>_<pid>/` and briefly shows overlays.
- To stop the app while running, use the global hotkey Ctrl+Shift+P (the app listens for that combo).

Configuration
-------------
- Edit `config.json` to adjust timings, skull size/position, typing trigger chance, and other parameters. Reasonable defaults are created automatically.
- If you want to supply mod assets from an external path, you may set the environment variable `PHONKEDIT_ASSETS_ROOT` to point to that root; the app will use it when present.

Troubleshooting
---------------
- Missing/old Python: ensure `python --version` is 3.8+ and that the `python`/`python3` command used to create the venv matches the one used to run the app.
- No audio: ensure you have at least one `.ogg` file in `assets/phonk/` and your OS audio is working.
- No overlays on Windows: Tkinter is required; on some distributions you may need to install OS-level packages (macOS and Linux generally ship Tk; for many Linux distros install `python3-tk`).
- PowerShell activation blocked: see the `Set-ExecutionPolicy` line above.

If anything else fails, check the console output for errors; saved images include printed paths like `Saved output/...` when captures succeed.

License / Contact
-----------------
See the project repository for license and author contact information.

That's it — keep `assets/` populated and run `python main.py` to start capturing.


import os
import json
import random
import threading
import time
import ctypes
import math
import tempfile
import shutil
import atexit
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageOps, ImageEnhance, ImageChops
import mss
import tkinter as tk
from PIL import ImageTk
from queue import Queue, Empty
import pygame

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SKULLS_DIR = ASSETS_DIR / "skulls"
PHONK_DIR = ASSETS_DIR / "phonk"
OUTPUT_DIR = BASE_DIR / "output"  # Will be reassigned to a temp folder per run in main()
SESSION_OUTPUT_DIR = None

def find_mod_assets_root():
    env = os.environ.get("PHONKEDIT_ASSETS_ROOT")
    if env:
        p = Path(env)
        if p.exists():
            return p
    candidate = BASE_DIR.parent / "src" / "main" / "resources" / "assets" / "phonkedit"
    if candidate.exists():
        return candidate
    return None

MOD_ASSETS_ROOT = find_mod_assets_root()
SRC_SKULLS = (MOD_ASSETS_ROOT / "textures" / "gui") if MOD_ASSETS_ROOT else None
SRC_PHONK = (MOD_ASSETS_ROOT / "sounds" / "phonk") if MOD_ASSETS_ROOT else None

def ensure_assets():
    """Ensure asset directories exist. Use assets/skulls and assets/phonk directly."""
    SKULLS_DIR.mkdir(parents=True, exist_ok=True)
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    global SKULL_CACHE
    SKULL_CACHE = None

def get_skulls():
    global SKULL_CACHE
    if SKULL_CACHE is None:
        paths = list(SKULLS_DIR.glob("*.png"))
        SKULL_CACHE = [Image.open(p).convert("RGBA") for p in paths]
    return SKULL_CACHE

_busy = False
_last = 0.0
_lock = threading.Lock()
_hook_id = None
_proc_ptr = None
overlay_requests = Queue()
overlay_windows = {}
overlay_canvases = {}
overlay_bg_pids = {}
overlay_skull_pids = {}
overlay_bg_photos = {}
overlay_skull_photos = {}
overlay_skull_base_pos = {}
overlay_skull_phase = {}
overlay_ready_event = threading.Event()
SKULL_CACHE = None
STOP_EVENT = threading.Event()

# Config
DEFAULT_CONFIG = {
    "click_delay_ms": 300,            # Wait after click before capture (align with your action)
    "min_cooldown_ms": 200,           # Minimum gap between effects
    "skull_size_ratio": 0.18,         # Fraction of screen width
    "skull_offset_y_ratio": 0.66,     # Vertical position for skull (lower third)
    # Typing trigger controls
    "typing_enabled": True,
    "typing_min_cooldown_ms": 3000,   # Separate cooldown for typing triggers
    "typing_trigger_chance": 0.07     # Chance per keypress to trigger (0..1)
    ,
    # Skull-only shake controls
    "skull_shake_enabled": True,
    "skull_shake_amplitude_px": 5,
    "skull_shake_speed_hz": 9.0
}

def load_config():
    cfg_path = BASE_DIR / "config.json"
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(cfg_path.read_text())
        # Merge defaults
        merged = DEFAULT_CONFIG.copy()
        merged.update({k:v for k,v in data.items() if k in DEFAULT_CONFIG})
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

CONFIG = None
COOLDOWN_S = 0.2
CLICK_DELAY_S = 0.3
TYPING_COOLDOWN_S = 3.0
TYPING_TRIGGER_CHANCE = 0.07
TYPING_ENABLED = True
_last_typing = 0.0
SKULL_SHAKE_ENABLED = True
SKULL_SHAKE_AMPL_PX = 5
SKULL_SHAKE_SPEED_HZ = 9.0

def play_random_phonk():
    ensure_assets()
    tracks = list(PHONK_DIR.glob("*.ogg"))
    if not tracks:
        return
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    track = random.choice(tracks)
    pygame.mixer.music.load(str(track))
    pygame.mixer.music.set_volume(0.9)
    pygame.mixer.music.play()

def stop_audio():
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except Exception:
        pass

def overlay_skulls(img, skulls):
    # Deprecated: no longer compositing skull into background. Kept for compatibility if needed.
    return img

def process_image(img):
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = ImageEnhance.Brightness(g).enhance(0.6)
    sh1 = ImageChops.offset(g, -3, 0)
    sh2 = ImageChops.offset(g, 3, 0)
    g2 = Image.blend(sh1, sh2, 0.5)
    g_mix = Image.blend(g2, g, 0.5)
    base = g_mix.convert("RGBA")
    return base

def capture_all_monitors():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []
    images = []
    rects = []
    with mss.mss() as sct:
        for i, mon in enumerate(sct.monitors[1:], start=1):
            try:
                shot = sct.grab(mon)
                try:
                    img = Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)
                except Exception:
                    img = Image.frombytes("RGBA", (shot.width, shot.height), shot.bgra, "raw", "BGRA").convert("RGB")
                out = process_image(img)
                path = OUTPUT_DIR / f"phonk_{ts}_monitor{i}.png"
                out.save(path)
                print(f"Saved {path}", flush=True)
                saved.append(path)
                images.append(out)
                rects.append((mon["left"], mon["top"], mon["width"], mon["height"]))
            except Exception as e:
                print(f"Capture failed for monitor {i}: {e}", flush=True)
    return saved, images, rects

def stream_captures():
    with mss.mss() as sct:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch = []
        for i, mon in enumerate(sct.monitors[1:], start=1):
            if STOP_EVENT.is_set():
                break
            try:
                shot = sct.grab(mon)
                try:
                    img = Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)
                except Exception:
                    img = Image.frombytes("RGBA", (shot.width, shot.height), shot.bgra, "raw", "BGRA").convert("RGB")
                out = process_image(img)
                rect = (mon["left"], mon["top"], mon["width"], mon["height"]) 
                overlay_requests.put(("add", [(out, rect)]))
                path = OUTPUT_DIR / f"phonk_{ts}_monitor{i}.png"
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                out.save(path)
                print(f"Saved {path}", flush=True)
            except Exception as e:
                print(f"Capture failed for monitor {i}: {e}", flush=True)
        

def show_overlay_item(root, img, rect):
    x, y, w, h = rect
    key = f"{x},{y},{w},{h}"
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.geometry(f"{w}x{h}+{x}+{y}")
    cv = tk.Canvas(win, width=w, height=h, highlightthickness=0, bd=0)
    cv.pack(fill="both", expand=True)
    # Background layer
    bg_photo = ImageTk.PhotoImage(img)
    bg_pid = cv.create_image(0, 0, image=bg_photo, anchor="nw")
    # Skull layer (separate)
    skull_pid = None
    skull_photo = None
    skulls = get_skulls()
    if skulls:
        sk = random.choice(skulls)
        target_w = max(48, int(w * float(CONFIG.get("skull_size_ratio", DEFAULT_CONFIG["skull_size_ratio"]))))
        ratio = target_w / sk.width
        target_h = max(48, int(sk.height * ratio))
        sk_resized = sk.resize((target_w, target_h), Image.LANCZOS)
        skull_photo = ImageTk.PhotoImage(sk_resized)
        lx = max(0, (w - target_w) // 2)
        ly = max(0, min(h - target_h, int(h * float(CONFIG.get("skull_offset_y_ratio", DEFAULT_CONFIG["skull_offset_y_ratio"])))))
        skull_pid = cv.create_image(lx, ly, image=skull_photo, anchor="nw")
        overlay_skull_base_pos[key] = (lx, ly)
        overlay_skull_phase[key] = random.random() * math.tau
    overlay_windows[key] = win
    overlay_canvases[key] = cv
    overlay_bg_pids[key] = bg_pid
    overlay_bg_photos[key] = bg_photo
    if skull_pid is not None:
        overlay_skull_pids[key] = skull_pid
    if skull_photo is not None:
        overlay_skull_photos[key] = skull_photo
    if not overlay_ready_event.is_set():
        overlay_ready_event.set()

def close_all_overlays():
    for win in list(overlay_windows.values()):
        try:
            win.destroy()
        except Exception:
            pass
    overlay_windows.clear()
    overlay_canvases.clear()
    overlay_bg_pids.clear()
    overlay_bg_photos.clear()
    overlay_skull_pids.clear()
    overlay_skull_photos.clear()
    overlay_skull_base_pos.clear()
    overlay_skull_phase.clear()


def safe_trigger(root=None):
    global _busy, _last
    with _lock:
        now = time.monotonic()
        if _busy or (now - _last) < COOLDOWN_S or STOP_EVENT.is_set():
            return
        _busy = True
        _last = now
    def run_audio_and_stream():
        try:
            overlay_ready_event.clear()
            time.sleep(CLICK_DELAY_S)
            threading.Thread(target=stream_captures, daemon=True).start()
            start_wait = time.monotonic()
            while not overlay_ready_event.is_set() and (time.monotonic() - start_wait) < 0.3:
                time.sleep(0.002)
            if not STOP_EVENT.is_set():
                play_random_phonk()
            while not STOP_EVENT.is_set() and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                time.sleep(0.05)
        finally:
            overlay_requests.put(("close", None))
            with _lock:
                global _busy
                _busy = False
    threading.Thread(target=run_audio_and_stream, daemon=True).start()

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CAPITAL = 0x14  # CapsLock
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_P = 0x50

def poll_clicks():
    user32 = ctypes.windll.user32
    prev_left = False
    prev_right = False
    while not STOP_EVENT.is_set():
        left = (user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0
        right = (user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000) != 0
        if left and not prev_left:
            safe_trigger()
        if right and not prev_right:
            safe_trigger()
        prev_left = left
        prev_right = right
        time.sleep(0.02)

def poll_keys():
    """Poll for key press rising edges across virtual keys and trigger rarely for typing.
    Also listens for Ctrl+Shift+P to stop the app."""
    user32 = ctypes.windll.user32
    ignored = {VK_SHIFT, VK_CONTROL, VK_MENU, VK_LWIN, VK_RWIN, VK_CAPITAL, VK_TAB, VK_ESCAPE}
    prev = [False] * 256
    prev_combo = False
    while not STOP_EVENT.is_set():
        # Global stop hotkey: Ctrl+Shift+P
        ctrl_down = (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
        shift_down = (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
        p_down = (user32.GetAsyncKeyState(VK_P) & 0x8000) != 0
        combo = ctrl_down and shift_down and p_down
        if combo and not prev_combo:
            overlay_requests.put(("shutdown", None))
        prev_combo = combo
        # Scan a subset of virtual keys. 0x08..0xFE covers Backspace to OEM keys.
        triggered = False
        if not TYPING_ENABLED:
            # Skip typing trigger if disabled, but still process stop combo
            time.sleep(0.015)
            continue
        for vk in range(0x08, 0xFF):
            if vk in (VK_LBUTTON, VK_RBUTTON) or vk in ignored:
                continue
            state = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
            if state and not prev[vk]:
                triggered = True
            prev[vk] = state
        if triggered:
            now = time.monotonic()
            # Enforce separate typing cooldown
            global _last_typing
            if (now - _last_typing) >= TYPING_COOLDOWN_S and random.random() < TYPING_TRIGGER_CHANCE:
                _last_typing = now
                safe_trigger()
        time.sleep(0.015)

def process_overlay_queue(root):
    global _busy
    try:
        while True:
            msg, payload = overlay_requests.get_nowait()
            if msg == "add":
                for img, rect in payload:
                    show_overlay_item(root, img, rect)
            elif msg == "add_many":
                for img, rect in payload:
                    show_overlay_item(root, img, rect)
            elif msg == "close":
                close_all_overlays()
            elif msg == "shutdown":
                # Stop everything and exit
                STOP_EVENT.set()
                try:
                    stop_audio()
                except Exception:
                    pass
                close_all_overlays()
                # Remove session output directory if used
                try:
                    if SESSION_OUTPUT_DIR and SESSION_OUTPUT_DIR.exists():
                        shutil.rmtree(SESSION_OUTPUT_DIR, ignore_errors=True)
                except Exception:
                    pass
                try:
                    root.after(50, root.quit)
                except Exception:
                    pass
    except Empty:
        pass
    root.after(10, lambda: process_overlay_queue(root))

def main():
    ensure_assets()
    # Load config and derive timing values
    global CONFIG, COOLDOWN_S, CLICK_DELAY_S, TYPING_COOLDOWN_S, TYPING_TRIGGER_CHANCE, TYPING_ENABLED
    global SKULL_SHAKE_ENABLED, SKULL_SHAKE_AMPL_PX, SKULL_SHAKE_SPEED_HZ
    CONFIG = load_config()
    COOLDOWN_S = max(0.0, float(CONFIG.get("min_cooldown_ms", DEFAULT_CONFIG["min_cooldown_ms"])) / 1000.0)
    CLICK_DELAY_S = max(0.0, float(CONFIG.get("click_delay_ms", DEFAULT_CONFIG["click_delay_ms"])) / 1000.0)
    TYPING_COOLDOWN_S = max(0.0, float(CONFIG.get("typing_min_cooldown_ms", DEFAULT_CONFIG["typing_min_cooldown_ms"])) / 1000.0)
    TYPING_TRIGGER_CHANCE = max(0.0, min(1.0, float(CONFIG.get("typing_trigger_chance", DEFAULT_CONFIG["typing_trigger_chance"])) ))
    TYPING_ENABLED = bool(CONFIG.get("typing_enabled", DEFAULT_CONFIG["typing_enabled"]))
    SKULL_SHAKE_ENABLED = bool(CONFIG.get("skull_shake_enabled", DEFAULT_CONFIG["skull_shake_enabled"]))
    SKULL_SHAKE_AMPL_PX = max(0, int(CONFIG.get("skull_shake_amplitude_px", DEFAULT_CONFIG["skull_shake_amplitude_px"])) )
    SKULL_SHAKE_SPEED_HZ = max(0.1, float(CONFIG.get("skull_shake_speed_hz", DEFAULT_CONFIG["skull_shake_speed_hz"])) )
    # Create a per-run temporary output folder under ./output and clean it up on exit
    global SESSION_OUTPUT_DIR, OUTPUT_DIR
    try:
        (BASE_DIR / "output").mkdir(parents=True, exist_ok=True)
        SESSION_OUTPUT_DIR = (BASE_DIR / "output" / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}")
        SESSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR = SESSION_OUTPUT_DIR
    except Exception:
        # Fallback to system temp if local path fails
        SESSION_OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="phonkedit-session-"))
        OUTPUT_DIR = SESSION_OUTPUT_DIR

    def _cleanup_on_exit():
        try:
            stop_audio()
        except Exception:
            pass
        close_all_overlays()
        try:
            if SESSION_OUTPUT_DIR and SESSION_OUTPUT_DIR.exists():
                shutil.rmtree(SESSION_OUTPUT_DIR, ignore_errors=True)
        except Exception:
            pass

    atexit.register(_cleanup_on_exit)

    root = tk.Tk()
    root.withdraw()
    threading.Thread(target=poll_clicks, daemon=True).start()
    threading.Thread(target=poll_keys, daemon=True).start()
    process_overlay_queue(root)
    # Start skull-only shake animation loop if enabled
    def skull_shake_step():
        if SKULL_SHAKE_ENABLED and overlay_skull_pids:
            t = time.monotonic()
            omega = 2 * math.pi * SKULL_SHAKE_SPEED_HZ
            for k, pid in list(overlay_skull_pids.items()):
                cv = overlay_canvases.get(k)
                base = overlay_skull_base_pos.get(k)
                phase = overlay_skull_phase.get(k, 0.0)
                if not cv or not base:
                    continue
                bx, by = base
                dx = int(round(SKULL_SHAKE_AMPL_PX * math.sin(phase + t * omega)))
                dy = int(round(SKULL_SHAKE_AMPL_PX * 0.6 * math.cos(phase + t * omega * 0.9)))
                try:
                    cv.coords(pid, bx + dx, by + dy)
                except Exception:
                    pass
        root.after(16, skull_shake_step)
    skull_shake_step()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        overlay_requests.put(("shutdown", None))
        time.sleep(0.2)

if __name__ == "__main__":
    main()

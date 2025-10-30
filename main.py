import os,json,random,threading,time,ctypes,math,tempfile,shutil,atexit
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty

try:
 import mss
except Exception:
 mss=None
try:
 import pygame
except Exception:
 pygame=None
import tkinter as tk
from PIL import Image,ImageOps,ImageEnhance,ImageChops,ImageTk
try:
 from PIL import ImageGrab
except Exception:
 ImageGrab=None

home_dump=Path(__file__).resolve().parent
asset_dumpster=home_dump/"assets"
skull_horde=asset_dumpster/"skulls"
phonk_hoard=asset_dumpster/"phonk"
vomit_dir=home_dump/"output"
session_dumpster=None

def dig_mod_wad():
 vibe=os.environ.get("PHONKEDIT_ASSETS_ROOT")
 if vibe:
  sneaky=Path(vibe)
  if sneaky.exists(): return sneaky
 fallback=home_dump.parent/"src"/"main"/"resources"/"assets"/"phonkedit"
 if fallback.exists(): return fallback
 return None

mod_root=dig_mod_wad()
skull_source=(mod_root/"textures"/"gui") if mod_root else None
phonk_source=(mod_root/"sounds"/"phonk") if mod_root else None

skull_cache=None

def spawn_trash():
 skull_horde.mkdir(parents=True,exist_ok=True)
 phonk_hoard.mkdir(parents=True,exist_ok=True)
 global skull_cache
 skull_cache=None

def yank_skulls():
 global skull_cache
 if skull_cache is None:
  skull_paths=list(skull_horde.glob("*.png"))
  skull_cache=[Image.open(p).convert("RGBA") for p in skull_paths]
 return skull_cache

busy_flag=False
last_spark=0.0
gremlin_lock=threading.Lock()
hook_thing=None
proc_thing=None
overlay_vomit=Queue()
window_litter={}
canvas_litter={}
bg_gore={}
skull_gore={}
bg_pics={}
skull_pics={}
skull_parking={}
skull_phase={}
overlay_ready=threading.Event()
global_stop=threading.Event()

crust_defaults={
 "click_delay_ms":300,
 "min_cooldown_ms":200,
 "skull_size_ratio":0.18,
 "skull_offset_y_ratio":0.66,
 "typing_enabled":True,
 "typing_min_cooldown_ms":3000,
 "typing_trigger_chance":0.03,
 "click_trigger_chance":0.35,
 "skull_shake_enabled":True,
 "skull_shake_amplitude_px":5,
 "skull_shake_speed_hz":9.0
}

cfg_blob=None
cooldown_slop=0.2
click_wait=0.3
typing_timeout=3.0
typing_spin=0.03
typing_on=True
fuck_last_ping=0.0
click_spin=1.0
skull_wobble=True
skull_wobble_px=5
skull_wobble_speed=9.0

def slurp_cfg():
 cfg_path=home_dump/"config.json"
 if not cfg_path.exists():
  cfg_path.write_text(json.dumps(crust_defaults,indent=2))
  return dict(crust_defaults)
 try:
  user=json.loads(cfg_path.read_text())
  mashed=dict(crust_defaults)
  mashed.update({k:v for k,v in user.items() if k in crust_defaults})
  try:
   cfg_path.write_text(json.dumps(mashed,indent=2))
  except Exception:
   pass
  return mashed
 except Exception:
  return dict(crust_defaults)

def scream_phonk():
 if pygame is None:
  print("JUST INSTALL THE DEPENDENCIES",flush=True)
  return
 spawn_trash()
 stash=list(phonk_hoard.glob("*.ogg"))
 if not stash: return
 if not pygame.mixer.get_init():
  pygame.mixer.init()
 tune=random.choice(stash)
 pygame.mixer.music.load(str(tune))
 pygame.mixer.music.set_volume(0.9)
 pygame.mixer.music.play()

def shut_audio_pipe():
 try:
  if pygame and pygame.mixer.get_init():
   pygame.mixer.music.stop()
   pygame.mixer.quit()
 except Exception:
  pass

def smudge_pic(pic):
  gray=ImageOps.grayscale(pic)
  gray=ImageOps.autocontrast(gray)
  gray=ImageEnhance.Brightness(gray).enhance(0.6)
  sh1=ImageChops.offset(gray,-3,0)
  sh2=ImageChops.offset(gray,3,0)
  goo=Image.blend(sh1,sh2,0.5)
  gunk=Image.blend(goo,gray,0.5)
  return gunk.convert("RGBA")

def throw_captures():
 if not mss:
  if ImageGrab is None:
   print("bro just install the dependencies",flush=True)
   return
  tag=datetime.now().strftime("%Y%m%d_%H%M%S")
  try:
   shot=ImageGrab.grab(all_screens=True)
   cooked=smudge_pic(shot)
   rect=(0,0,cooked.width,cooked.height)
   overlay_vomit.put(("add",[(cooked,rect)]))
   spot=vomit_dir/f"phonk_{tag}_monitor0.png"
   vomit_dir.mkdir(parents=True,exist_ok=True)
   cooked.save(spot)
   print(f"saved {spot}",flush=True)
  except Exception as why:
   print(f"imagegrab puked: {why}",flush=True)
  finally:
   overlay_vomit.put(("mark_ready",None))
  return
 with mss.mss() as grabber:
  tag=datetime.now().strftime("%Y%m%d_%H%M%S")
  for idx,screen in enumerate(grabber.monitors[1:],start=1):
   if global_stop.is_set(): break
   try:
    shot=grabber.grab(screen)
    try:
     raw=Image.frombytes("RGB",(shot.width,shot.height),shot.rgb)
    except Exception:
     raw=Image.frombytes("RGBA",(shot.width,shot.height),shot.bgra,"raw","BGRA").convert("RGB")
    cooked=smudge_pic(raw)
    rect=(screen["left"],screen["top"],screen["width"],screen["height"])
    overlay_vomit.put(("add",[(cooked,rect)]))
    spot=vomit_dir/f"phonk_{tag}_monitor{idx}.png"
    vomit_dir.mkdir(parents=True,exist_ok=True)
    cooked.save(spot)
    print(f"saved {spot}",flush=True)
   except Exception as splat:
    print(f"capture barfed on monitor {idx}: {splat}",flush=True)
 overlay_vomit.put(("mark_ready",None))

def spew_overlay(root,pic,rect):
 x,y,w,h=rect
 key=f"{x},{y},{w},{h}"
 win=tk.Toplevel(root)
 win.overrideredirect(True)
 win.attributes("-topmost",True)
 win.geometry(f"{w}x{h}+{x}+{y}")
 pad=tk.Canvas(win,width=w,height=h,highlightthickness=0,bd=0)
 pad.pack(fill="both",expand=True)
 bg_photo=ImageTk.PhotoImage(pic)
 bg_id=pad.create_image(0,0,image=bg_photo,anchor="nw")
 skull_id=None
 skull_photo=None
 stash=yank_skulls()
 cfg=cfg_blob or crust_defaults
 if stash:
  skull=random.choice(stash)
  want=max(48,int(w*float(cfg.get("skull_size_ratio",crust_defaults["skull_size_ratio"]))))
  ratio=want/skull.width
  target_h=max(48,int(skull.height*ratio))
  skull_resized=skull.resize((want,target_h),Image.LANCZOS)
  skull_photo=ImageTk.PhotoImage(skull_resized)
  lx=max(0,(w-want)//2)
  ly=max(0,min(h-target_h,int(h*float(cfg.get("skull_offset_y_ratio",crust_defaults["skull_offset_y_ratio"])))))
  skull_id=pad.create_image(lx,ly,image=skull_photo,anchor="nw")
  skull_parking[key]=(lx,ly)
  skull_phase[key]=random.random()*math.tau
 window_litter[key]=win
 canvas_litter[key]=pad
 bg_gore[key]=bg_id
 bg_pics[key]=bg_photo
 if skull_id is not None:
  skull_gore[key]=skull_id
 if skull_photo is not None:
  skull_pics[key]=skull_photo

def melt_overlays():
 for win in list(window_litter.values()):
  try:
   win.destroy()
  except Exception:
   pass
 window_litter.clear()
 canvas_litter.clear()
 bg_gore.clear()
 bg_pics.clear()
 skull_gore.clear()
 skull_pics.clear()
 skull_parking.clear()
 skull_phase.clear()

def trigger_sauce(root=None):
 global busy_flag,last_spark
 with gremlin_lock:
  now=time.monotonic()
  if busy_flag or (now-last_spark)<cooldown_slop or global_stop.is_set():
   return
  busy_flag=True
  last_spark=now
 def audio_n_stream():
  global busy_flag
  try:
   overlay_ready.clear()
   time.sleep(click_wait)
   threading.Thread(target=throw_captures,daemon=True).start()
   start=time.monotonic()
   while not overlay_ready.is_set() and (time.monotonic()-start)<0.3:
    time.sleep(0.002)
   if not global_stop.is_set():
    scream_phonk()
   while (not global_stop.is_set() and pygame and pygame.mixer.get_init() and pygame.mixer.music.get_busy()):
    time.sleep(0.05)
  finally:
   overlay_vomit.put(("close",None))
   with gremlin_lock:
    busy_flag=False
 threading.Thread(target=audio_n_stream,daemon=True).start()

vk_lbutton=0x01
vk_rbutton=0x02
vk_shift=0x10
vk_control=0x11
vk_menu=0x12
vk_lwin=0x5B
vk_rwin=0x5C
vk_capital=0x14
vk_tab=0x09
vk_escape=0x1B
vk_p=0x50

def spy_clicks():
 if not hasattr(ctypes,"windll"):
  print("sorry, this only works on windows, you need windll :)",flush=True)
  return
 user32=ctypes.windll.user32
 prev_left=False
 prev_right=False
 while not global_stop.is_set():
  left=(user32.GetAsyncKeyState(vk_lbutton)&0x8000)!=0
  right=(user32.GetAsyncKeyState(vk_rbutton)&0x8000)!=0
  if left and not prev_left and random.random()<click_spin:
   trigger_sauce()
  if right and not prev_right and random.random()<click_spin:
   trigger_sauce()
  prev_left=left
  prev_right=right
  time.sleep(0.02)

def stalk_keys():
 if not hasattr(ctypes,"windll"):
  print("sorry, this only works on windows, you need windll :)",flush=True)
  return
 user32=ctypes.windll.user32
 ignored={vk_shift,vk_control,vk_menu,vk_lwin,vk_rwin,vk_capital,vk_tab,vk_escape}
 prev=[False]*256
 prev_combo=False
 while not global_stop.is_set():
  ctrl_down=(user32.GetAsyncKeyState(vk_control)&0x8000)!=0
  shift_down=(user32.GetAsyncKeyState(vk_shift)&0x8000)!=0
  p_down=(user32.GetAsyncKeyState(vk_p)&0x8000)!=0
  combo=ctrl_down and shift_down and p_down
  if combo and not prev_combo:
   overlay_vomit.put(("shutdown",None))
  prev_combo=combo
  if not typing_on:
   time.sleep(0.015)
   continue
  triggered=False
  for code in range(0x08,0xFF):
   if code in (vk_lbutton,vk_rbutton) or code in ignored: continue
   state=(user32.GetAsyncKeyState(code)&0x8000)!=0
   if state and not prev[code]: triggered=True
   prev[code]=state
  if triggered:
   now=time.monotonic()
   global fuck_last_ping
   if (now-fuck_last_ping)>=typing_timeout and random.random()<typing_spin:
    fuck_last_ping=now
    trigger_sauce()
  time.sleep(0.015)

def bleed_overlay_queue(root):
 def cleanup_overlays():
  try: shut_audio_pipe()
  except Exception: pass
  melt_overlays()
 try:
  while True:
   msg,payload=overlay_vomit.get_nowait()
   if msg=="add":
    for pic,rect in payload: spew_overlay(root,pic,rect)
   elif msg=="add_many":
    for pic,rect in payload: spew_overlay(root,pic,rect)
   elif msg=="close":
    cleanup_overlays()
   elif msg=="mark_ready":
    if not overlay_ready.is_set():
     overlay_ready.set()
   elif msg=="shutdown":
    global_stop.set()
    cleanup_overlays()
    try:
     if session_dumpster and session_dumpster.exists():
      shutil.rmtree(session_dumpster,ignore_errors=True)
    except Exception:
     pass
    try:
     root.after(50,root.quit)
    except Exception:
     pass
 except Empty:
  pass
 root.after(10,lambda:bleed_overlay_queue(root))

def chaos_entry():
 spawn_trash()
 global cfg_blob,cooldown_slop,click_wait,typing_timeout,typing_spin,typing_on
 global skull_wobble,skull_wobble_px,skull_wobble_speed,click_spin
 global session_dumpster,vomit_dir
 cfg_blob=slurp_cfg()
 cooldown_slop=max(0.0,float(cfg_blob.get("min_cooldown_ms",crust_defaults["min_cooldown_ms"]))/1000.0)
 click_wait=max(0.0,float(cfg_blob.get("click_delay_ms",crust_defaults["click_delay_ms"]))/1000.0)
 typing_timeout=max(0.0,float(cfg_blob.get("typing_min_cooldown_ms",crust_defaults["typing_min_cooldown_ms"]))/1000.0)
 typing_spin=max(0.0,min(1.0,float(cfg_blob.get("typing_trigger_chance",crust_defaults["typing_trigger_chance"]))))
 typing_on=bool(cfg_blob.get("typing_enabled",crust_defaults["typing_enabled"]))
 click_spin=max(0.0,min(1.0,float(cfg_blob.get("click_trigger_chance",crust_defaults["click_trigger_chance"]))))
 skull_wobble=bool(cfg_blob.get("skull_shake_enabled",crust_defaults["skull_shake_enabled"]))
 skull_wobble_px=max(0,int(cfg_blob.get("skull_shake_amplitude_px",crust_defaults["skull_shake_amplitude_px"])))
 skull_wobble_speed=max(0.1,float(cfg_blob.get("skull_shake_speed_hz",crust_defaults["skull_shake_speed_hz"])))
 try:
  (home_dump/"output").mkdir(parents=True,exist_ok=True)
  session_dumpster=(home_dump/"output"/f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}")
  session_dumpster.mkdir(parents=True,exist_ok=True)
  vomit_dir=session_dumpster
 except Exception:
  session_dumpster=Path(tempfile.mkdtemp(prefix="phonkedit-session-"))
  vomit_dir=session_dumpster
 def trash_cleanup():
  try: shut_audio_pipe()
  except Exception: pass
  melt_overlays()
  try:
   if session_dumpster and session_dumpster.exists():
    shutil.rmtree(session_dumpster,ignore_errors=True)
  except Exception:
   pass
 atexit.register(trash_cleanup)
 root=tk.Tk()
 root.withdraw()
 def show_intro():
  intro=tk.Toplevel(root)
  intro.title("Phonkedit Info")
  intro.attributes("-topmost",True)
  intro.geometry("340x150")
  msg="To stop the \"virus\" just press Ctrl + Shift + P"
  frame=tk.Frame(intro,padx=16,pady=16)
  frame.pack(fill="both",expand=True)
  label=tk.Label(frame,text=msg,wraplength=300,justify="center",font=("Segoe UI",12))
  label.pack(pady=(0,16))
  def close_intro():
   try:
    intro.grab_release()
   except Exception:
    pass
   intro.destroy()
  btn=tk.Button(frame,text="Got it",command=close_intro)
  btn.pack()
  intro.protocol("WM_DELETE_WINDOW",close_intro)
  intro.grab_set()
  intro.lift()
 show_intro()
 threading.Thread(target=spy_clicks,daemon=True).start()
 threading.Thread(target=stalk_keys,daemon=True).start()
 bleed_overlay_queue(root)
 def skull_wiggle_step():
  if skull_wobble and skull_gore:
   t=time.monotonic()
   omega=2*math.pi*skull_wobble_speed
   for key,pid in list(skull_gore.items()):
    pad=canvas_litter.get(key)
    base=skull_parking.get(key)
    phase=skull_phase.get(key,0.0)
    if not pad or not base: continue
    bx,by=base
    dx=int(round(skull_wobble_px*math.sin(phase+t*omega)))
    dy=int(round(skull_wobble_px*0.6*math.cos(phase+t*omega*0.9)))
    try:
     pad.coords(pid,bx+dx,by+dy)
    except Exception:
     pass
  root.after(16,skull_wiggle_step)
 skull_wiggle_step()
 try:
  root.mainloop()
 except KeyboardInterrupt:
  overlay_vomit.put(("shutdown",None))
  time.sleep(0.2)

def main():
 chaos_entry()

if __name__=="__main__":
 main()

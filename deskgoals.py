#!/usr/bin/env python3
"""DeskGoals v4"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import json, os, threading, time, sys, traceback, socket, shutil, uuid, queue
from http.server import BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer as ServerClass
except ImportError:
    from http.server import HTTPServer as ServerClass

# ── Error logging ─────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.expanduser("~"), "deskgoals_error.log")

def log_error(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"\n{'='*60}\n{msg}\n")
    except Exception:
        pass

sys.excepthook = lambda t, v, tb: log_error(
    "".join(traceback.format_exception(t, v, tb)))

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk, ImageGrab
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    log_error("pystray/Pillow not installed - run install.bat")

try:
    import win32gui, win32process, psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import keyboard
    HAS_HOTKEY = True
except ImportError:
    HAS_HOTKEY = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False
    log_error("tkinterdnd2 not installed - pip install tkinterdnd2")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.expanduser("~"), ".deskgoals_v3.json")
MEDIA_DIR = os.path.join(os.path.expanduser("~"), ".deskgoals_media")
os.makedirs(MEDIA_DIR, exist_ok=True)
FONT      = "Segoe UI"

# ── Size presets (W, H) ───────────────────────────────────────────────────────
SIZE_PRESETS = [(225, 420), (300, 560), (375, 700), (450, 840)]
SIZE_LABELS  = ["75%", "100%", "125%", "150%"]

# ── P2P constants ─────────────────────────────────────────────────────────────
SHARE_PORT    = 7843
DISCOVER_PORT = 7844
DEVICE_NAME   = socket.gethostname()

# ── Themes ────────────────────────────────────────────────────────────────────
THEMES = {
    "Dark": {
        "bg":        "#0d0d0d",
        "bg_header": "#141414",
        "bg_row":    "#111111",
        "bg_row2":   "#141414",
        "bg_input":  "#171717",
        "bg_comp":   "#111a11",
        "border":    "#222222",
        "text":      "#d0d0d0",
        "text_mute": "#555555",
        "text_hint": "#2e2e2e",
        "text_done": "#363636",
        "check_on":  "#5ddd5d",
        "check_off": "#333333",
        "tab_act":   "#ffffff",
        "tab_idle":  "#404040",
        "del_idle":  "#252525",
        "del_hov":   "#888888",
    },
    "Slate": {
        "bg":        "#1a1e24",
        "bg_header": "#1e2330",
        "bg_row":    "#1c2028",
        "bg_row2":   "#1e2330",
        "bg_input":  "#20252e",
        "bg_comp":   "#161d1e",
        "border":    "#2a3040",
        "text":      "#c8d0dc",
        "text_mute": "#4a5570",
        "text_hint": "#2a3040",
        "text_done": "#384050",
        "check_on":  "#4ecfcf",
        "check_off": "#2a3550",
        "tab_act":   "#8ab4ff",
        "tab_idle":  "#3a4560",
        "del_idle":  "#232d3a",
        "del_hov":   "#7090b0",
    },
    "Warm": {
        "bg":        "#141210",
        "bg_header": "#1a1714",
        "bg_row":    "#171412",
        "bg_row2":   "#1a1714",
        "bg_input":  "#1d1a17",
        "bg_comp":   "#141a12",
        "border":    "#2a2520",
        "text":      "#d4c8b8",
        "text_mute": "#554e44",
        "text_hint": "#302820",
        "text_done": "#3a3028",
        "check_on":  "#d4a84b",
        "check_off": "#3a3028",
        "tab_act":   "#e8c87a",
        "tab_idle":  "#4a4030",
        "del_idle":  "#252018",
        "del_hov":   "#a08060",
    },
    "Light": {
        "bg":        "#f4f4f4",
        "bg_header": "#ebebeb",
        "bg_row":    "#f8f8f8",
        "bg_row2":   "#f0f0f0",
        "bg_input":  "#eeeeee",
        "bg_comp":   "#e8f0e8",
        "border":    "#d8d8d8",
        "text":      "#1a1a1a",
        "text_mute": "#888888",
        "text_hint": "#bbbbbb",
        "text_done": "#aaaaaa",
        "check_on":  "#2a9a2a",
        "check_off": "#bbbbbb",
        "tab_act":   "#111111",
        "tab_idle":  "#888888",
        "del_idle":  "#d0d0d0",
        "del_hov":   "#555555",
    },
}

S = {
    "bg":       "#1c1c1c",
    "bg2":      "#242424",
    "bg3":      "#2c2c2c",
    "border":   "#333333",
    "text":     "#e0e0e0",
    "mute":     "#888888",
    "accent":   "#5b9cf0",
    "danger":   "#e05555",
    "input_bg": "#2a2a2a",
    "input_fg": "#e0e0e0",
}

HINTS = {
    "goal":      "Add a goal...",
    "header_sm": "Small header...",
    "header_lg": "BIG HEADER...",
}

# ── Data ──────────────────────────────────────────────────────────────────────
def default_data():
    return {
        "position":   None,
        "active_tab": "main",
        "workspaces": {"main": {"name": "Today", "goals": []}},
        "app_rules":  {},
        "completed":  [],
        "settings": {
            "theme":         "Dark",
            "alpha":         0.93,
            "hotkey":        "ctrl+alt+g",
            "always_on_top": True,
            "auto_show":     True,
            "sync_enabled":  False,
            "sync_port":     7842,
        },
    }

def load_data():
    try:
        with open(DATA_FILE) as f:
            d    = json.load(f)
            base = default_data()
            if "settings" in d:
                base["settings"].update(d.pop("settings"))
            base.update(d)
            if "main" not in base["workspaces"]:
                base["workspaces"]["main"] = {"name": "Today", "goals": []}
            return base
    except Exception:
        return default_data()

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_error(f"save_data failed: {e}")

_LOCAL_IP = None
def get_local_ip():
    global _LOCAL_IP
    if _LOCAL_IP is None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            _LOCAL_IP = s.getsockname()[0]
            s.close()
        except Exception:
            _LOCAL_IP = "127.0.0.1"
    return _LOCAL_IP


# ── Scrollable frame ──────────────────────────────────────────────────────────
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.vsb    = tk.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview, width=4)
        self.vsb.configure(bg=bg, troughcolor=bg)
        self.inner  = tk.Frame(self.canvas, bg=bg)
        self._win   = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_scroll)
        self.canvas.bind("<Configure>", self._update_width)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_scroll))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all(
            "<MouseWheel>"))
        self.inner.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_scroll))

    def _update_scroll(self, e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_width(self, e):
        self.canvas.itemconfig(self._win, width=e.width)

    def _on_scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")


# ── Tooltip ───────────────────────────────────────────────────────────────────
class Tooltip:
    """Light hover tooltip — attach with Tooltip(widget, text)."""
    def __init__(self, widget, text):
        self._tip = None
        widget.bind("<Enter>", lambda e: self._show(widget, text), add="+")
        widget.bind("<Leave>", lambda e: self._hide(),             add="+")

    def _show(self, widget, text):
        self._hide()
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tk.Label(tw, text=text, bg="#1e2230", fg="#c8d4e8",
                 font=(FONT, 8), padx=8, pady=4,
                 relief="flat", bd=0).pack()

    def _hide(self):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None


# ── Mobile web server ─────────────────────────────────────────────────────────
MOBILE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DeskGoals Share</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#d0d0d0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:0 auto;min-height:100vh;padding:0 10px}
header{padding:14px 16px;background:#141414;border-bottom:none;display:flex;align-items:center;gap:10px;box-shadow:0 1px 10px rgba(0,0,0,0.5)}
header h1{font-size:15px;color:#fff;letter-spacing:1px;flex:1}
#sync-dot{font-size:11px;color:#5ddd5d;transition:color .3s}
.tabs{display:flex;background:#141414;box-shadow:0 1px 5px rgba(0,0,0,0.3);overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{padding:10px 16px;font-size:12px;cursor:pointer;white-space:nowrap;color:#555;border-bottom:2px solid transparent;flex-shrink:0}
.tab.active{color:#fff;border-bottom-color:#fff}
.ws-label{padding:4px 16px;font-size:10px;color:#444;letter-spacing:2px;background:#0a0a0a}
.goals{padding:4px 0 140px}
.goal-row{display:flex;align-items:flex-start;padding:11px 16px;border-bottom:1px solid #181818;gap:12px}
.goal-row.alt{background:#141414}
.header-sm,.header-lg{background:#141414;padding:9px 16px;border-bottom:1px solid #1e1e1e}
.header-sm .htxt{font-size:12px;font-weight:700;color:#fff;letter-spacing:.5px}
.header-lg .htxt{font-size:18px;font-weight:700;color:#fff}
.circle{width:22px;height:22px;border-radius:50%;border:2px solid #333;cursor:pointer;flex-shrink:0;margin-top:2px;transition:all .15s}
.circle:active{background:#5ddd5d;border-color:#5ddd5d}
.goal-text{flex:1;font-size:14px;line-height:1.45}
.empty{text-align:center;padding:50px 20px;color:#333;font-size:16px;line-height:2}
.bottom-bar{position:fixed;bottom:0;left:0;right:0;max-width:800px;margin:0 auto;background:#111318;border-top:none;box-shadow:0 -2px 10px rgba(0,0,0,0.5)}
.add-bar{display:flex;padding:10px 12px 4px;gap:8px;align-items:center}
.add-bar input{flex:1;background:#111;border:1px solid #222;color:#d0d0d0;font-size:15px;padding:10px 14px;border-radius:10px;outline:none}
.add-bar input:focus{border-color:#444}
.add-bar button{background:#5ddd5d;color:#000;border:none;width:42px;height:42px;border-radius:10px;font-size:22px;font-weight:700;cursor:pointer;flex-shrink:0}
.send-bar{display:flex;padding:4px 12px 10px;gap:8px;align-items:center}
.send-bar label{flex:1;background:#111;border:1px solid #2a2f3a;color:#6b7280;font-size:13px;padding:9px 14px;border-radius:10px;cursor:pointer;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.send-bar label.ready{color:#d0d0d0;border-color:#4f8ef7;background:#1a1d24}
.send-bar input[type=file]{display:none}
.send-bar button{background:#4f8ef7;color:#fff;border:none;padding:0 18px;height:40px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0}
.send-bar button:disabled{background:#222;color:#555;cursor:default}
.send-section-title{font-size:9px;letter-spacing:1.5px;color:#4f8ef7;font-weight:700;padding:8px 12px 2px}
#upload-progress{height:3px;background:#1e2230;margin:0 12px 6px;border-radius:2px;overflow:hidden;display:none}
#upload-bar{height:100%;background:#4f8ef7;width:0;transition:width .2s}
#upload-status{text-align:center;font-size:12px;padding:0 12px 6px;display:none}
.files-section{padding:6px 12px 10px;border-top:1px solid #1e1e1e}
.files-section h3{font-size:9px;letter-spacing:1.5px;color:#4f8ef7;margin-bottom:6px;font-weight:700}
.file-row{display:flex;align-items:center;background:#1a1d24;border-radius:8px;padding:8px 12px;margin-bottom:4px;gap:10px}
.file-row span{flex:1;font-size:12px;color:#d0d0d0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-row a{background:#3ecf6e;color:#000;text-decoration:none;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px;white-space:nowrap;flex-shrink:0}
</style>
</head>
<body>
<header>
  <h1>&#11041; DESKGOALS</h1>
  <span id="sync-dot">&#9679;</span>
</header>
<div class="tabs" id="tabs"></div>
<div class="ws-label" id="ws-label"></div>
<div class="goals" id="goals"></div>
<div class="bottom-bar">
  <div class="add-bar">
    <input id="inp" placeholder="Add a goal..." autocomplete="off">
    <button onclick="addGoal()">+</button>
  </div>
  <div style="border-top:1px solid #1e1e1e">
    <div class="send-section-title">&#8679; SEND FILE TO HOST</div>
    <div class="send-bar">
      <label id="file-label" for="file-pick">Tap to choose a file</label>
      <input type="file" id="file-pick" onchange="fileChosen(this)">
      <button id="send-btn" disabled onclick="uploadFile()">Send</button>
    </div>
    <div id="upload-progress"><div id="upload-bar"></div></div>
    <div id="upload-status"></div>
  </div>
  <div class="files-section" id="files-section" style="display:none">
    <h3>&#8595; FILES FROM HOST</h3>
    <div id="files-list"></div>
  </div>
</div>
<script>
let state={workspaces:{},active_tab:"main"};
let activeTab="main";
let chosenFile=null;

function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}

async function load(){
  try{
    const r=await fetch("/api/state");
    if(!r.ok)throw 0;
    state=await r.json();
    if(!state.workspaces[activeTab])
      activeTab=state.active_tab||Object.keys(state.workspaces)[0];
    render();
    document.getElementById("sync-dot").style.color="#5ddd5d";
  }catch(e){
    document.getElementById("sync-dot").style.color="#555";
  }
}

function render(){
  const tabEl=document.getElementById("tabs");
  tabEl.innerHTML=Object.entries(state.workspaces).map(([k,ws])=>
    `<div class="tab${k===activeTab?" active":""}" onclick="switchTab('${k}')">${esc(ws.name)}</div>`
  ).join("");
  const ws=state.workspaces[activeTab]||{name:"",goals:[]};
  document.getElementById("ws-label").textContent=ws.name.toUpperCase();
  const goals=ws.goals||[];
  const rows=[];let alt=0;
  goals.forEach((g,ri)=>{
    if(g.done)return;
    if(g.type==="header"){
      rows.push(`<div class="header-${g.size||'sm'}"><span class="htxt">${esc(g.text)}</span></div>`);
      return;
    }
    if(g.type==="media"){
      let icon = g.media_type==="image"?"🖼️":g.media_type==="audio"?"🎵":g.media_type==="video"?"🎬":g.media_type==="pdf"?"📄":"📁";
      rows.push(`<div class="goal-row${alt++%2?" alt":""}"><div class="circle" onclick="complete(${ri})"></div><span class="goal-text" style="color:#4f8ef7;text-decoration:underline;">${icon} ${esc(g.filename)}</span></div>`);
      return;
    }
    rows.push(`<div class="goal-row${alt++%2?" alt":""}"><div class="circle" onclick="complete(${ri})"></div><span class="goal-text">${esc(g.text)}</span></div>`);
  });
  document.getElementById("goals").innerHTML=rows.length
    ?rows.join(""):`<div class="empty">Nothing here.<br>Add a goal below.</div>`;
}

function switchTab(k){activeTab=k;render();}

async function complete(ri){
  await fetch("/api/complete",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({workspace:activeTab,index:ri})});
  load();
}

async function addGoal(){
  const inp=document.getElementById("inp");
  const text=inp.value.trim();
  if(!text)return;
  await fetch("/api/add",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({workspace:activeTab,text})});
  inp.value="";load();
}

function fileChosen(input){
  chosenFile=input.files[0]||null;
  const lbl=document.getElementById("file-label");
  const btn=document.getElementById("send-btn");
  if(chosenFile){
    lbl.textContent=chosenFile.name;
    lbl.classList.add("ready");
    btn.disabled=false;
  } else {
    lbl.textContent="↑ Send a file to Host";
    lbl.classList.remove("ready");
    btn.disabled=true;
  }
}

async function uploadFile(){
  if(!chosenFile)return;
  const btn=document.getElementById("send-btn");
  const prog=document.getElementById("upload-progress");
  const bar=document.getElementById("upload-bar");
  const status=document.getElementById("upload-status");
  const fname=chosenFile.name;
  btn.disabled=true;
  prog.style.display="block";
  status.style.display="block";
  status.style.color="#4f8ef7";
  status.textContent="Waiting for Host to accept...";
  bar.style.width="0";
  bar.style.background="#4f8ef7";

  const xhr=new XMLHttpRequest();
  xhr.open("POST","/api/upload");
  xhr.setRequestHeader("X-Filename", encodeURIComponent(fname));
  xhr.upload.onprogress=e=>{
    if(e.lengthComputable)
      bar.style.width=(e.loaded/e.total*100)+"%";
  };
  xhr.onload=()=>{
    const ok=xhr.status===200;
    bar.style.width="100%";
    
    if(xhr.status===403){
      bar.style.background="#e05555";
      status.style.display="block";
      status.style.color="#e05555";
      status.textContent="✗ Host declined the file";
    } else {
      bar.style.background=ok?"#3ecf6e":"#e05555";
      status.style.display="block";
      status.style.color=ok?"#3ecf6e":"#e05555";
      status.textContent=ok?`✓ Sent: ${fname}`:"✗ Send failed — try again";
    }
    
    setTimeout(()=>{
      prog.style.display="none";
      status.style.display="none";
      bar.style.width="0";
      bar.style.background="#4f8ef7";
    },4000);
    chosenFile=null;
    document.getElementById("file-pick").value="";
    document.getElementById("file-label").textContent="Tap to choose a file";
    document.getElementById("file-label").classList.remove("ready");
    btn.disabled=true;
  };
  xhr.onerror=()=>{
    bar.style.background="#e05555";
    status.style.display="block";
    status.style.color="#e05555";
    status.textContent="✗ Connection lost";
    btn.disabled=false;
  };
  xhr.send(chosenFile);
}

document.getElementById("inp").addEventListener("keydown",e=>{if(e.key==="Enter")addGoal();});

async function pollFiles(){
  try{
    const r=await fetch("/api/files");
    if(!r.ok)return;
    const d=await r.json();
    const sec=document.getElementById("files-section");
    const lst=document.getElementById("files-list");
    if(!d.files||!d.files.length){sec.style.display="none";return;}
    sec.style.display="block";
    lst.innerHTML=d.files.map(f=>
      `<div class="file-row"><span>${esc(f)}</span><a href="/api/download/${encodeURIComponent(f)}" download="${esc(f)}">Save</a></div>`
    ).join("");
  }catch(e){}
}

load();pollFiles();
setInterval(load,4000);
setInterval(pollFiles,3000);
</script>
</body>
</html>"""


class MobileHandler(BaseHTTPRequestHandler):
    app            = None
    _pending       = {}   # key -> {"path": str, "ts": float}
    _connected_ips = {}   # ip -> {"ts": float, "name": str}

    @classmethod
    def push_file(cls, filepath):
        """Queue a file so mobile can download it. Returns the key name."""
        # Expire any pending files older than 10 minutes
        now = time.time()
        cls._pending = {k: v for k, v in cls._pending.items()
                        if now - v.get("ts", now) < 600}
        fname = os.path.basename(filepath)
        key = fname
        counter = 1
        while key in cls._pending:
            base, ext = os.path.splitext(fname)
            key = f"{base}_{counter}{ext}"
            counter += 1
        cls._pending[key] = {"path": filepath, "ts": now}
        return key

    def log_message(self, *a): pass

    def do_GET(self):
        ip = self.client_address[0]
        if ip not in MobileHandler._connected_ips:
            try:
                name = socket.gethostbyaddr(ip)[0]
                if name.endswith('.local') or name.endswith('.lan'):
                    name = name.split('.')[0]
            except Exception:
                name = f"Browser ({ip})"
            MobileHandler._connected_ips[ip] = {"ts": time.time(), "name": name}
        else:
            MobileHandler._connected_ips[ip]["ts"] = time.time()

        if self.path == "/api/state":
            self._json(200, {
                "active_tab": self.app.data.get("active_tab"),
                "workspaces": self.app.data.get("workspaces", {}),
            })
        elif self.path == "/api/files":
            # Expire stale entries before listing
            now = time.time()
            MobileHandler._pending = {k: v for k, v in MobileHandler._pending.items()
                                      if now - v.get("ts", now) < 600}
            self._json(200, {"files": list(MobileHandler._pending.keys())})

        elif self.path.startswith("/api/download/"):
            import urllib.parse as _up
            key    = _up.unquote(self.path[len("/api/download/"):])
            entry  = MobileHandler._pending.get(key)
            fp     = entry["path"] if isinstance(entry, dict) else entry
            if not fp or not os.path.isfile(fp):
                self.send_response(404); self.end_headers(); return
            size = os.path.getsize(fp)
            self.send_response(200)
            self.send_header("Content-Type",        "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{key}"')
            self.send_header("Content-Length",      size)
            self.end_headers()
            with open(fp, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            # Remove after download
            MobileHandler._pending.pop(key, None)

        elif self.path == "/":
            body = MOBILE_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/upload":
            self.do_POST_upload()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            body = {}

        if self.path == "/api/add":
            ws_key = body.get("workspace", self.app.data.get("active_tab"))
            text   = (body.get("text") or "").strip()
            if text and ws_key in self.app.data.get("workspaces", {}):
                def do():
                    self.app.data["workspaces"][ws_key]["goals"].append(
                        {"text": text, "done": False})
                    save_data(self.app.data)
                    self.app._render_all()
                self.app.root.after(0, do)
            self._json(200, {"ok": True})

        elif self.path == "/api/complete":
            ws_key = body.get("workspace")
            idx    = body.get("index")
            if ws_key is not None and idx is not None:
                def do():
                    goals = self.app.data.get("workspaces", {}).get(
                        ws_key, {}).get("goals", [])
                    if 0 <= idx < len(goals) and not goals[idx].get("done"):
                        self.app._complete_goal_in_ws(idx, ws_key)
                self.app.root.after(0, do)
            self._json(200, {"ok": True})

        else:
            self._json(404, {"error": "not found"})

    def do_POST_upload(self):
        """Handle raw file upload from mobile browser (called by do_POST routing)."""
        import urllib.parse as _up
        raw_name  = self.headers.get("X-Filename", "upload")
        try:
            filename = _up.unquote(raw_name)
        except Exception:
            filename = raw_name
        total     = int(self.headers.get("Content-Length", 0))
        safe_name = os.path.basename(filename) or "upload"
        
        sender_ip = self.client_address[0]
        sender_name = MobileHandler._connected_ips.get(sender_ip, {}).get("name", sender_ip)

        # ── ASK USER BEFORE DOWNLOADING ──
        if not self.app._ask_accept_file(safe_name, sender_name):
            self._json(403, {"error": "Declined by user"})
            return

        dest_dir  = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(dest_dir, exist_ok=True)
        dest      = os.path.join(dest_dir, safe_name)
        base, ext = os.path.splitext(safe_name)
        counter   = 1
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1

        tid    = f"m_{time.time():.3f}"
        panel  = (self.app._share_win
                  if self.app._share_win and self.app._share_win.alive else None)
        if panel:
            self.app.root.after(0, lambda: panel._add_recv_row(
                tid, safe_name, total, f"📱 {sender_name}"))
        try:
            received    = 0
            _last_ui_t  = 0.0   # Fix 5: throttle UI updates to ≤10/sec
            with open(dest, "wb") as f:
                while received < total:
                    chunk = self.rfile.read(min(65536, total - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if panel:
                        _now = time.time()
                        if _now - _last_ui_t >= 0.1:
                            _last_ui_t = _now
                            b = received
                            self.app.root.after(0,
                                lambda b=b: panel._update_recv(tid, b, total))
            if panel:
                self.app.root.after(0,
                    lambda: panel._finish_recv(tid, True, dest))
            else:
                # Panel not open — flash ⇄ button to signal file arrived
                self.app.root.after(0,
                    lambda: self.app._flash_share_btn(safe_name))
            self._json(200, {"ok": True, "saved": os.path.basename(dest)})
        except Exception as e:
            log_error(f"mobile upload failed: {e}")
            if panel:
                self.app.root.after(0, lambda: panel._finish_recv(tid, False, None))
            self._json(500, {"error": str(e)})

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


# ── Main App ──────────────────────────────────────────────────────────────────
class DeskGoals:
    def __init__(self):
        self.data              = load_data()
        self.visible           = True
        self._drag_x           = 0
        self._drag_y           = 0
        self._hotkey_id        = None
        self.settings_win      = None
        self.comp_open         = False
        self._hint_active      = True
        self._input_mode       = "goal"   # "goal" | "header_sm" | "header_lg"
        self._sync_server      = None
        self._settings_rebuild_ws    = None
        self._settings_rebuild_rules = None
        self._prev_focused_proc      = None
        self._user_hidden            = False   # True when user explicitly hid widget
        self._app_switch_queue       = queue.Queue()  # thread-safe channel for app-watch → main thread
        self._share_win              = None
        self._size_idx               = self.data["settings"].get("size_idx", 1)
        self._image_cache            = {}
        self._row_widget_map         = {}   # uid → row entry dict for targeted updates

        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
            
        self.root.title("DeskGoals")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-toolwindow", False)
        self.root.attributes("-topmost",
            self.data["settings"].get("always_on_top", True))
        self.root.attributes("-alpha",
            self.data["settings"].get("alpha", 0.93))
            
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
            
        self.root.bind('<Control-v>', self._on_paste)

        self._restore_position()
        self._build_ui()
        # Start hidden — live in tray until user shows it
        self.root.withdraw()
        self.visible = False

        try:
            self._setup_tray()
        except Exception as e:
            log_error(f"_setup_tray failed: {e}")

        self._register_hotkey()
        self._cleanup_old_completed()  # purge on startup, then hourly

        if self.data["settings"].get("sync_enabled", False):
            self._start_sync_server()

        if HAS_WIN32:
            threading.Thread(target=self._app_watch_loop, daemon=True).start()
            self.root.after(200, self._poll_app_switch_queue)

        self.root.protocol("WM_DELETE_WINDOW", self._toggle_visibility)

    @property
    def T(self):
        return THEMES.get(
            self.data["settings"].get("theme", "Dark"), THEMES["Dark"])

    # ── Respectful File Prompt ────────────────────────────────────────────────
    def _ask_accept_file(self, filename, sender):
        """Thread-safe prompt asking the user if they want to save an incoming file."""
        result = [False]
        evt = threading.Event()
        dlg_ref = []

        def _show():
            dlg = tk.Toplevel(self.root)
            dlg_ref.append(dlg)
            dlg.title("Incoming File")
            dlg.geometry("320x130")
            dlg.configure(bg=S["bg"])
            dlg.attributes("-topmost", True)
            dlg.resizable(False, False)

            # Center on screen
            dlg.update_idletasks()
            w = dlg.winfo_width()
            h = dlg.winfo_height()
            x = (dlg.winfo_screenwidth() // 2) - (w // 2)
            y = (dlg.winfo_screenheight() // 2) - (h // 2)
            dlg.geometry(f"+{x}+{y}")

            tk.Label(dlg, text=f"Accept file from {sender}?", bg=S["bg"], fg=S["mute"], font=(FONT, 9)).pack(pady=(15, 5))
            tk.Label(dlg, text=filename, bg=S["bg"], fg=S["text"], font=(FONT, 10, "bold"), wraplength=280).pack(pady=(0, 15))

            btn_frame = tk.Frame(dlg, bg=S["bg"])
            btn_frame.pack(fill="x", pady=(0, 8))

            def on_yes():
                result[0] = True
                evt.set()
                dlg.destroy()
            def on_no():
                result[0] = False
                evt.set()
                dlg.destroy()

            tk.Button(btn_frame, text="Accept", command=on_yes, bg=S["accent"], fg="white", relief="flat", font=(FONT, 9, "bold"), width=12).pack(side="left", padx=(30, 10))
            tk.Button(btn_frame, text="Decline", command=on_no, bg=S["bg3"], fg=S["text"], relief="flat", font=(FONT, 9), width=12).pack(side="right", padx=(10, 30))

            dlg.protocol("WM_DELETE_WINDOW", on_no)
            dlg.grab_set()
            dlg.focus_force()

        self.root.after(0, _show)
        evt.wait(timeout=120) # Auto-decline after 2 minutes
        
        # Cleanup if the timeout triggered
        if not evt.is_set():
            def _kill():
                if dlg_ref and dlg_ref[0].winfo_exists():
                    dlg_ref[0].destroy()
            self.root.after(0, _kill)
            return False
            
        return result[0]

    # ── Media Drag and Drop / Paste ───────────────────────────────────────────
    def _browse_and_add_file(self, event=None):
        """Open a file dialog to manually attach files."""
        from tkinter import filedialog
        filepaths = filedialog.askopenfilenames(
            parent=self.root, title="Select files to attach")
        
        if filepaths:
            for fp in filepaths:
                self._process_dropped_file(fp)
            self._render_all()
            self.root.after(50, lambda: self.scroll.canvas.yview_moveto(1.0))

    def _on_paste(self, event=None):
        """Catch Ctrl+V to paste screenshots from the clipboard."""
        if self._entry_focused():
            return # Let the text entry handle normal text pasting

        try:
            img = ImageGrab.grabclipboard()
            if img:
                filename = f"clipboard_{uuid.uuid4().hex[:8]}.png"
                filepath = os.path.join(MEDIA_DIR, filename)
                
                # Sometimes files copied from explorer come as a list of paths
                if isinstance(img, list):
                    for f in img:
                        self._process_dropped_file(f)
                else:
                    img.save(filepath, "PNG")
                    self._add_media_goal("image", filename, dest_path=filepath)
        except Exception as e:
            log_error(f"Paste error: {e}")
        return "break"

    def _on_drop(self, event):
        """Handle dragging and dropping files into the app."""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            self._process_dropped_file(file_path)
            
        self._render_all()
        self.root.after(50, lambda: self.scroll.canvas.yview_moveto(1.0))

    def _process_dropped_file(self, file_path):
        if not os.path.isfile(file_path):
            return
            
        filename = os.path.basename(file_path)
        base, ext = os.path.splitext(filename)
        dest_path = os.path.join(MEDIA_DIR, filename)
        
        # Avoid overwriting files with the same name
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(MEDIA_DIR, f"{base}_{counter}{ext}")
            filename = f"{base}_{counter}{ext}"
            counter += 1
            
        shutil.copy(file_path, dest_path)
        
        ext_lower = ext.lower()
        if ext_lower in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            m_type = "image"
        elif ext_lower in ['.mp3', '.wav', '.ogg', '.flac']:
            m_type = "audio"
        elif ext_lower in ['.mp4', '.mkv', '.avi', '.mov']:
            m_type = "video"
        elif ext_lower == '.pdf':
            m_type = "pdf"
        else:
            m_type = "file"

        self._add_media_goal(m_type, filename, dest_path=dest_path)

    def _add_media_goal(self, m_type, filename, dest_path=None):
        # Ask the user for an optional description when a file is added
        from tkinter import simpledialog
        desc = simpledialog.askstring(
            "Attachment Note", 
            "Write a description for this file (leave blank for none):",
            parent=self.root
        )
        
        # User pressed Cancel — abort and remove the already-copied file
        if desc is None:
            if dest_path and os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return
        
        item = {
            "type": "media", 
            "media_type": m_type, 
            "filename": filename, 
            "text": desc.strip() if desc else "",
            "done": False
        }
        self._current_goals().append(item)
        save_data(self.data)
        self._render_all()
        self.root.after(50, lambda: self.scroll.canvas.yview_moveto(1.0))

    def _show_image_popup(self, filepath):
        if not os.path.exists(filepath): return
        
        top = tk.Toplevel(self.root)
        top.title("Image Preview")
        top.configure(bg="#000000")
        top.attributes("-topmost", True)
        top.overrideredirect(True)
        
        try:
            img = Image.open(filepath)
            
            # Resize to fit screen reasonably
            sw = self.root.winfo_screenwidth() * 0.8
            sh = self.root.winfo_screenheight() * 0.8
            img.thumbnail((int(sw), int(sh)))
            photo = ImageTk.PhotoImage(img)
            
            lbl = tk.Label(top, image=photo, bg="#000000", cursor="hand2")
            lbl.image = photo # Keep reference
            lbl.pack(padx=2, pady=2)
            
            # Click to close
            lbl.bind("<Button-1>", lambda e: top.destroy())
            top.bind("<Escape>", lambda e: top.destroy())
            
            # Center window
            top.update_idletasks()
            w = top.winfo_width()
            h = top.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (w // 2)
            y = (self.root.winfo_screenheight() // 2) - (h // 2)
            top.geometry(f"+{x}+{y}")
            
        except Exception as e:
            log_error(f"Popup error: {e}")
            top.destroy()

    # ── Position ──────────────────────────────────────────────────────────────
    def _current_wh(self):
        idx = max(0, min(self._size_idx, len(SIZE_PRESETS) - 1))
        return SIZE_PRESETS[idx]

    def _restore_position(self):
        pos     = self.data.get("position")
        cw, ch  = self._current_wh()
        if pos:
            x, y = pos
        else:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x  = sw - cw - 28
            y  = (sh - ch) // 2
        self.root.geometry(f"{cw}x{ch}+{x}+{y}")

    def _save_position(self):
        self.data["position"] = [self.root.winfo_x(), self.root.winfo_y()]
        save_data(self.data)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        t = self.T

        # Header
        self.header = tk.Frame(self.root, bg=t["bg_header"],
                                height=42, cursor="fleur")
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        self.header.bind("<ButtonPress-1>",   self._drag_start)
        self.header.bind("<B1-Motion>",       self._drag_move)
        self.header.bind("<ButtonRelease-1>", lambda e: self._save_position())

        self.ws_label = tk.Label(self.header, text="", bg=t["bg_header"],
                                  fg=t["text_mute"], font=(FONT, 8, "bold"))
        self.ws_label.pack(side="left", padx=14)

        self.app_badge = tk.Label(self.header, text="", bg=t["bg_header"],
                                   fg=t["check_on"], font=(FONT, 7))
        self.app_badge.pack(side="left", padx=2)

        # ── Right-side header controls ─────────────────────────────────────
        # Use tab_act (always bright) so icons stay visible at low transparency

        cog = tk.Label(self.header, text="⚙", bg=t["bg_header"],
                       fg=t["tab_act"], font=(FONT, 13), cursor="hand2")
        cog.pack(side="right", padx=(4, 8))
        cog.bind("<Button-1>", lambda e: self._open_settings())
        cog.bind("<Enter>",    lambda e: cog.configure(fg=t["check_on"]))
        cog.bind("<Leave>",    lambda e: cog.configure(fg=t["tab_act"]))
        Tooltip(cog, "Settings  (Ctrl+,)")

        hide = tk.Label(self.header, text="–", bg=t["bg_header"],
                        fg=t["tab_act"], font=(FONT, 13), cursor="hand2")
        hide.pack(side="right", padx=2)
        hide.bind("<Button-1>", lambda e: self._toggle_visibility())
        hide.bind("<Enter>",    lambda e: hide.configure(fg=t["check_on"]))
        hide.bind("<Leave>",    lambda e: hide.configure(fg=t["tab_act"]))
        Tooltip(hide, "Minimise to tray  (Numpad 5)")

        # Share button  ⇄
        self._share_btn_ref = tk.Label(self.header, text="⇄", bg=t["bg_header"],
                             fg=t["tab_act"], font=(FONT, 13), cursor="hand2")
        self._share_btn_ref.pack(side="right", padx=2)
        self._share_btn_ref.bind("<Button-1>", lambda e: self._open_fileshare())
        self._share_btn_ref.bind("<Enter>",    lambda e: self._share_btn_ref.configure(fg=t["check_on"]))
        self._share_btn_ref.bind("<Leave>",    lambda e: self._share_btn_ref.configure(fg=t["tab_act"]))
        Tooltip(self._share_btn_ref, "File Share")

        # Resize button — cycles through SIZE_PRESETS
        self.size_btn = tk.Label(self.header, text=SIZE_LABELS[self._size_idx],
                                  bg=t["bg_header"], fg=t["text_mute"],
                                  font=(FONT, 7), cursor="hand2")
        self.size_btn.pack(side="right", padx=(4, 0))
        self.size_btn.bind("<Button-1>", lambda e: self._cycle_size())
        Tooltip(self.size_btn, "Resize widget")

        self.count_lbl = tk.Label(self.header, text="", bg=t["bg_header"],
                                   fg=t["text_mute"], font=(FONT, 8))
        self.count_lbl.pack(side="right", padx=4)

        tk.Frame(self.root, bg=t["border"], height=1).pack(fill="x")

        # Tab bar — scrollable canvas so many workspaces don't get clipped
        tab_canvas_frame = tk.Frame(self.root, bg=t["bg_header"], height=32)
        tab_canvas_frame.pack(fill="x")
        tab_canvas_frame.pack_propagate(False)
        self.tab_canvas = tk.Canvas(tab_canvas_frame, bg=t["bg_header"],
                                    height=32, bd=0, highlightthickness=0)
        self.tab_canvas.pack(fill="both", expand=True)
        self.tab_bar = tk.Frame(self.tab_canvas, bg=t["bg_header"])
        self._tab_win = self.tab_canvas.create_window(
            (0, 0), window=self.tab_bar, anchor="nw")
        self.tab_bar.bind("<Configure>",
            lambda e: self.tab_canvas.configure(
                scrollregion=self.tab_canvas.bbox("all")))
        self.tab_canvas.bind("<MouseWheel>",
            lambda e: self.tab_canvas.xview_scroll(
                int(-1 * (e.delta / 120)), "units"))
        # Also allow scrolling when hovering child tab labels
        self.tab_bar.bind("<MouseWheel>",
            lambda e: self.tab_canvas.xview_scroll(
                int(-1 * (e.delta / 120)), "units"))
        tk.Frame(self.root, bg=t["border"], height=1).pack(fill="x")

        # Goal list
        self.scroll = ScrollFrame(self.root, bg=t["bg"])
        self.scroll.pack(fill="both", expand=True)

        # Completed bar
        self.comp_bar = tk.Frame(self.root, bg=t["bg_header"], cursor="hand2")
        self.comp_bar.pack(fill="x")

        self.comp_arrow = tk.Label(self.comp_bar, text="▶",
                                    bg=t["bg_header"], fg=t["text_mute"],
                                    font=(FONT, 7))
        self.comp_arrow.pack(side="left", padx=(12, 4), pady=6)

        self.comp_lbl = tk.Label(self.comp_bar, text="Completed  (0)",
                                  bg=t["bg_header"], fg=t["text_mute"],
                                  font=(FONT, 8))
        self.comp_lbl.pack(side="left")

        clr = tk.Label(self.comp_bar, text="Clear", bg=t["bg_header"],
                       fg=t["del_idle"], font=(FONT, 7), cursor="hand2")
        clr.pack(side="right", padx=12)
        clr.bind("<Button-1>", lambda e: self._clear_completed())
        clr.bind("<Enter>",    lambda e: clr.configure(fg=t["del_hov"]))
        clr.bind("<Leave>",    lambda e: clr.configure(fg=t["del_idle"]))

        for w in (self.comp_bar, self.comp_arrow, self.comp_lbl):
            w.bind("<Button-1>", lambda e: self._toggle_completed())

        self.comp_frame = tk.Frame(self.root, bg=t["bg_comp"])

        tk.Frame(self.root, bg=t["border"], height=1).pack(fill="x")

        # Input bar
        inp = tk.Frame(self.root, bg=t["bg_input"], height=46)
        inp.pack(fill="x", side="bottom")
        inp.pack_propagate(False)

        # Mode toggle: ¶ = goal, H = header
        self.mode_btn = tk.Label(inp, text="¶", bg=t["bg_input"],
                                  fg=t["text_mute"], font=(FONT, 11, "bold"),
                                  cursor="hand2", padx=6)
        self.mode_btn.pack(side="left", padx=(8, 0))
        self.mode_btn.bind("<Button-1>", lambda e: self._cycle_input_mode())
        Tooltip(self.mode_btn, "Toggle mode: goal / small header / big header")

        # File Attachment Button
        attach_btn = tk.Label(inp, text="+", bg=t["bg_input"], fg=t["text_mute"],
                              font=(FONT, 16), cursor="hand2")
        attach_btn.pack(side="left", padx=(6, 4))
        attach_btn.bind("<Button-1>", self._browse_and_add_file)
        attach_btn.bind("<Enter>", lambda e, b=attach_btn: b.configure(fg=t["accent"]))
        attach_btn.bind("<Leave>", lambda e, b=attach_btn: b.configure(fg=t["text_mute"]))
        Tooltip(attach_btn, "Attach files")

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(inp, textvariable=self.entry_var,
                              bg=t["bg_input"], fg=t["text_hint"],
                              insertbackground=t["text"],
                              relief="flat", font=(FONT, 11), bd=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.entry.bind("<Return>",   self._add_goal)
        self.entry.bind("<FocusIn>",  self._hint_clear)
        self.entry.bind("<FocusOut>", self._hint_show)

        self.entry_var.trace_add("write", self._on_entry_changed)

        self._hint_active = True
        self._input_mode  = "goal"
        self.entry_var.set(HINTS["goal"])

        # ── Click empty list area → focus entry ───────────────────────────────
        self.scroll.canvas.bind("<Button-1>", self._focus_entry)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        self.root.bind("<Control-comma>", lambda e: self._open_settings())
        self.root.bind("<Control-t>",     lambda e: self._new_workspace())
        self.root.bind("<Control-slash>", lambda e: self._focus_entry())
        self.root.bind("<Tab>",
            lambda e: self._tab_next() if not self._entry_focused() else None)
        # Return works anywhere — focuses entry if needed, otherwise submits
        self.root.bind("<Return>", self._add_goal)
        self.root.bind("<KP_Enter>", self._add_goal)

        self._refresh_tabs()
        self._render_all()

    def _full_redraw(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.comp_open   = False
        self._input_mode = "goal"
        self.root.configure(bg=self.T["bg"])
        self._build_ui()

    # ── Input mode & hints ────────────────────────────────────────────────────
    def _cycle_input_mode(self):
        modes = ["goal", "header_sm", "header_lg"]
        self._input_mode = modes[(modes.index(self._input_mode) + 1) % 3]
        t = self.T
        if self._input_mode == "goal":
            self.mode_btn.configure(text="¶", fg=t["text_mute"],
                                     font=(FONT, 11, "bold"))
        elif self._input_mode == "header_sm":
            self.mode_btn.configure(text="H", fg=t["check_on"],
                                     font=(FONT, 11, "bold"))
        else:
            self.mode_btn.configure(text="H", fg=t["tab_act"],
                                     font=(FONT, 14, "bold"))
        if self._hint_active:
            self.entry_var.set(HINTS[self._input_mode])

    def _current_hint(self):
        return HINTS.get(self._input_mode, HINTS["goal"])

    def _hint_show(self, _=None):
        if not self.entry_var.get().strip():
            self._hint_active = True
            self.entry.configure(fg=self.T["text_hint"])
            self.entry_var.set(self._current_hint())

    def _hint_clear(self, _=None):
        if self._hint_active:
            self._hint_active = False
            self.entry_var.set("")
            self.entry.configure(fg=self.T["text"])

    def _on_entry_changed(self, *_):
        if self._hint_active or getattr(self, '_clearing_hint', False):
            return
        val  = self.entry_var.get()
        hint = self._current_hint()
        if hint in val:
            clean = val.replace(hint, "")
            self._clearing_hint = True
            self.entry_var.set(clean)
            self.entry.icursor(len(clean))
            self.entry.configure(fg=self.T["text"])
            self._clearing_hint = False

    # ── Tabs ──────────────────────────────────────────────────────────────────
    def _refresh_tabs(self):
        t = self.T
        for w in self.tab_bar.winfo_children():
            w.destroy()

        for key, ws in self.data["workspaces"].items():
            active = (key == self.data["active_tab"])
            lbl = tk.Label(self.tab_bar, text=ws["name"],
                           bg=t["bg_header"],
                           fg=t["tab_act"] if active else t["tab_idle"],
                           font=(FONT, 8, "bold" if active else "normal"),
                           cursor="hand2", padx=10, pady=8)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, k=key: self._switch_tab(k))
            lbl.bind("<Button-3>", lambda e, k=key: self._tab_context_menu(e, k))
            lbl.bind("<MouseWheel>",
                lambda e: self.tab_canvas.xview_scroll(
                    int(-1 * (e.delta / 120)), "units"))
            ct = len([g for g in ws.get("goals", [])
                      if not g.get("done") and g.get("type") != "header"])
            Tooltip(lbl, f"{ws['name']}  —  {ct} active  (Tab / Numpad 2 to cycle)")
            if active:
                tk.Frame(self.tab_bar, bg=t["tab_act"],
                         height=2, width=max(len(ws["name"]) * 7, 20)
                         ).place(in_=lbl, relx=0, rely=1.0, anchor="sw")

        add_tab = tk.Label(self.tab_bar, text="＋", bg=t["bg_header"],
                           fg=t["del_idle"], font=(FONT, 10),
                           cursor="hand2", padx=8)
        add_tab.pack(side="left")
        add_tab.bind("<Button-1>", lambda e: self._new_workspace())
        add_tab.bind("<Enter>",    lambda e: add_tab.configure(fg=t["text_mute"]))
        add_tab.bind("<Leave>",    lambda e: add_tab.configure(fg=t["del_idle"]))
        Tooltip(add_tab, "New workspace  (Ctrl+T / Numpad 3)")

    def _switch_tab(self, key):
        self.data["active_tab"] = key
        save_data(self.data)
        self._refresh_tabs()
        self._render_all()

    def _new_workspace(self):
        """Show an inline popup over the tab bar to name the new workspace."""
        t = self.T
        # Overlay frame positioned over the tab area
        overlay = tk.Frame(self.root, bg=t["bg_header"],
                           relief="flat", bd=0)
        overlay.place(relx=0, rely=0, relwidth=1.0, height=34,
                      y=self.header.winfo_height() + 1)
        overlay.lift()

        var = tk.StringVar()
        entry = tk.Entry(overlay, textvariable=var,
                         bg=t["bg_input"], fg=t["text"],
                         insertbackground=t["text"],
                         relief="flat", font=(FONT, 9), bd=0)
        entry.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=6)
        entry.insert(0, "Workspace name…")
        entry.select_range(0, "end")
        entry.focus_set()

        def confirm(e=None):
            name = var.get().strip()
            overlay.destroy()
            if not name or name == "Workspace name…":
                return
            key = f"ws_{len(self.data['workspaces'])}_{name.lower().replace(' ', '_')}"
            self.data["workspaces"][key] = {"name": name, "goals": []}
            self.data["active_tab"] = key
            save_data(self.data)
            self._refresh_tabs()
            self._render_all()
            self._sync_settings()

        def cancel(e=None):
            overlay.destroy()

        entry.bind("<Return>",  confirm)
        entry.bind("<Escape>",  cancel)
        entry.bind("<FocusOut>", cancel)

        ok_btn = tk.Label(overlay, text="OK", bg=t["check_on"], fg="#000",
                          font=(FONT, 8, "bold"), padx=8, cursor="hand2")
        ok_btn.pack(side="right", padx=(0, 6), pady=6)
        ok_btn.bind("<Button-1>", confirm)

    def _entry_focused(self):
        """True when the text entry currently has keyboard focus."""
        try:
            return self.root.focus_get() is self.entry
        except Exception:
            return False

    def _focus_entry(self, event=None):
        """Focus the input — called by canvas click or Ctrl+/ or numpad 1."""
        self._hint_clear()
        self.entry.focus_set()
        return "break"
        
    def _tab_next(self):
        """Cycle to the next workspace."""
        keys = list(self.data["workspaces"].keys())
        if len(keys) < 2:
            return "break"
        idx = keys.index(self.data["active_tab"]) if self.data["active_tab"] in keys else 0
        self._switch_tab(keys[(idx + 1) % len(keys)])
        return "break"

    def _current_goals(self):
        return self.data["workspaces"].get(
            self.data["active_tab"], {}).get("goals", [])

    # ── Render ────────────────────────────────────────────────────────────────
    def _ensure_uid(self, goal):
        """Stamp a stable short UUID onto a goal dict so we can track its widget."""
        if '_uid' not in goal:
            goal['_uid'] = uuid.uuid4().hex[:12]
        return goal['_uid']

    def _remove_row_widget(self, uid):
        """Destroy the widgets for a single row and recolor remaining goal rows."""
        entry = self._row_widget_map.pop(uid, None)
        if entry is None:
            return False
        try:
            entry["frame"].destroy()
        except Exception:
            pass
        if entry.get("sep"):
            try:
                entry["sep"].destroy()
            except Exception:
                pass
        # Only goal-type and media-type rows affect alternating colours
        if entry.get("row_type") in ("goal", "media"):
            self._recolor_goals()
        return True

    def _recolor_goals(self):
        """Fast pass to fix alternating row colours after a targeted remove."""
        t = self.T
        vis_idx = 0
        for entry in self._row_widget_map.values():
            row_type = entry.get("row_type")
            if row_type == "goal":
                bg = t["bg_row2"] if vis_idx % 2 == 1 else t["bg_row"]
                for w in entry.get("recolor", []):
                    try:
                        w.configure(bg=bg)
                    except Exception:
                        pass
                vis_idx += 1
            elif row_type == "media":
                vis_idx += 1

    def _render_all(self):
        t = self.T
        self._image_cache = {} # Clear old images from memory cache
        self._row_widget_map = {}  # Reset targeted-update tracking
        
        for w in self.scroll.inner.winfo_children():
            w.destroy()

        tab   = self.data["active_tab"]
        ws    = self.data["workspaces"].get(tab, {})
        goals = ws.get("goals", [])
        self.ws_label.configure(text=ws.get("name", "").upper(), fg=t["text_mute"])

        has_visible = any(not g.get("done") for g in goals)
        active_ct   = sum(1 for g in goals
                          if not g.get("done") and g.get("type") != "header")

        if not has_visible:
            tk.Label(self.scroll.inner,
                     text="Nothing here.\nAdd a goal below.",
                     bg=t["bg"], fg=t["text_hint"],
                     font=(FONT, 10), justify="center"
                     ).pack(expand=True, pady=36)
        else:
            # Display: lg headers first, sm headers second, goals last
            # Original index preserved so delete still works correctly
            def _hdisplay_order(pair):
                _, g = pair
                if g.get("type") == "header":
                    return 0 if g.get("size") == "lg" else 1
                return 2
            for i, g in sorted(enumerate(goals), key=_hdisplay_order):
                if not g.get("done"):
                    self._render_row(i, g)

        done_ct = sum(1 for g in goals if g.get("done"))
        self._update_count(active_ct, active_ct + done_ct)
        self._render_completed_section()

    def _render_row(self, index, goal):
        t = self.T
        uid = self._ensure_uid(goal)

        # ── Header ────────────────────────────────────────────────────────────
        if goal.get("type") == "header":
            size  = goal.get("size", "sm")
            fsize = 15 if size == "lg" else 10
            pady  = (10, 10) if size == "lg" else (7, 7)
            # Slightly different bg than both tasks and the tab bar
            bg    = t["bg_comp"] if size == "sm" else t["bg_header"]

            row   = tk.Frame(self.scroll.inner, bg=bg)
            row.pack(fill="x")
            # Left accent stripe in the check_on colour
            tk.Frame(row, bg=t["check_on"],
                     width=3).pack(side="left", fill="y")
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill="x", padx=(8, 10), pady=pady)

            tk.Label(inner, text=goal["text"], bg=bg, fg=t["tab_act"],
                     font=(FONT, fsize, "bold"), anchor="w",
                     wraplength=230, justify="left"
                     ).pack(side="left", fill="x", expand=True)

            d = tk.Label(inner, text="×", bg=bg, fg=t["del_idle"],
                         font=(FONT, 13), cursor="hand2")
            d.pack(side="right")
            d.bind("<Button-1>", lambda e, i=index: self._delete_goal(i))
            d.bind("<Enter>",    lambda e, b=d: b.configure(fg=t["del_hov"]))
            d.bind("<Leave>",    lambda e, b=d: b.configure(fg=t["del_idle"]))
            sep_w = tk.Frame(self.scroll.inner, bg=t["border"], height=1)
            sep_w.pack(fill="x")
            self._row_widget_map[uid] = {
                "row_type": "header", "frame": row, "sep": sep_w, "recolor": []}
            return
            
        # ── Media Files ───────────────────────────────────────────────────────
        if goal.get("type") == "media":
            m_type = goal.get("media_type", "file")
            filename = goal.get("filename", "")
            filepath = os.path.join(MEDIA_DIR, filename)

            # Create a distinct "Card" look with a border
            card_border = tk.Frame(self.scroll.inner, bg=t["border"])
            card_border.pack(fill="x", padx=12, pady=6) 
            
            card_bg = t["bg_header"] 
            inner = tk.Frame(card_border, bg=card_bg)
            inner.pack(fill="x", padx=1, pady=1) # 1px border effect

            # Top bar of the card
            top_bar = tk.Frame(inner, bg=card_bg)
            top_bar.pack(fill="x", padx=6, pady=6)

            # File Icon and Name
            icons = {"image": "🖼️", "audio": "🎵", "video": "🎬", "pdf": "📄", "file": "📁"}
            icon_char = icons.get(m_type, "📁")
            name_lbl = tk.Label(top_bar, text=f"{icon_char}  {filename}", bg=card_bg, fg=t["text"], font=(FONT, 9, "bold"), cursor="hand2", anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
            name_lbl.bind("<Button-1>", lambda e, fp=filepath: os.startfile(fp) if hasattr(os, 'startfile') and os.path.exists(fp) else None)
            name_lbl.bind("<Enter>", lambda e, l=name_lbl: l.configure(fg=t["accent"]))
            name_lbl.bind("<Leave>", lambda e, l=name_lbl: l.configure(fg=t["text"]))

            # Delete button
            d = tk.Label(top_bar, text="×", bg=card_bg, fg=t["del_idle"], font=(FONT, 13), cursor="hand2")
            d.pack(side="right", padx=(4, 0))
            d.bind("<Button-1>", lambda e, i=index: self._delete_goal(i))
            d.bind("<Enter>",    lambda e, b=d: b.configure(fg=t["del_hov"]))
            d.bind("<Leave>",    lambda e, b=d: b.configure(fg=t["del_idle"]))
            Tooltip(d, "Delete")

            # Main content area of the card (Larger Image Thumbnail)
            if m_type == "image" and os.path.exists(filepath):
                img_frame = tk.Frame(inner, bg=card_bg)
                img_frame.pack(fill="x", padx=10, pady=(0, 10))
                try:
                    img = Image.open(filepath)
                    # Create a much larger, higher quality thumbnail for the card
                    if hasattr(Image, 'Resampling'):
                        img.thumbnail((280, 200), Image.Resampling.LANCZOS)
                    else:
                        img.thumbnail((280, 200), Image.ANTIALIAS)
                    photo = ImageTk.PhotoImage(img)
                    self._image_cache[filename] = photo # Keep in memory
                    
                    # Wrap image in a dark background box
                    lbl = tk.Label(img_frame, image=photo, bg="#000000", cursor="hand2")
                    lbl.pack(pady=2)
                    lbl.bind("<Button-1>", lambda e, fp=filepath: self._show_image_popup(fp))
                except Exception:
                    tk.Label(img_frame, text="(Image format not supported)", bg=card_bg, fg=t["text_mute"], font=(FONT, 8)).pack()

            elif m_type == "pdf" and os.path.exists(filepath):
                pdf_frame = tk.Frame(inner, bg=card_bg)
                pdf_frame.pack(fill="x", padx=10, pady=(0, 10))
                try:
                    import fitz  # PyMuPDF
                    doc  = fitz.open(filepath)
                    page = doc[0]
                    mat  = fitz.Matrix(0.6, 0.6)
                    pix  = page.get_pixmap(matrix=mat)
                    from io import BytesIO
                    img  = Image.open(BytesIO(pix.tobytes("png")))
                    if hasattr(Image, 'Resampling'):
                        img.thumbnail((280, 360), Image.Resampling.LANCZOS)
                    else:
                        img.thumbnail((280, 360), Image.ANTIALIAS)
                    photo = ImageTk.PhotoImage(img)
                    self._image_cache[filename + "_pdf"] = photo
                    doc.close()
                    lbl = tk.Label(pdf_frame, image=photo, bg="#1a1a1a", cursor="hand2",
                                   relief="flat", bd=1)
                    lbl.pack(pady=2)
                    lbl.bind("<Button-1>",
                             lambda e, fp=filepath: os.startfile(fp)
                             if hasattr(os, 'startfile') and os.path.exists(fp) else None)
                except ImportError:
                    tk.Label(pdf_frame,
                             text="📄  Install PyMuPDF for PDF preview\n(pip install pymupdf)",
                             bg=card_bg, fg=t["text_mute"],
                             font=(FONT, 8), justify="center").pack(pady=4)
                except Exception as ex:
                    log_error(f"PDF preview error: {ex}")
                    tk.Label(pdf_frame, text="(PDF preview unavailable)",
                             bg=card_bg, fg=t["text_mute"], font=(FONT, 8)).pack()

            # ── NEW: Render the Description Text ──
            desc_text = goal.get("text", "")
            if desc_text:
                desc_lbl = tk.Label(inner, text=desc_text, bg=card_bg, fg=t["text"], 
                                    font=(FONT, 10), justify="left", wraplength=220)
                desc_lbl.pack(anchor="w", padx=10, pady=(0, 10))

            self._row_widget_map[uid] = {
                "row_type": "media", "frame": card_border, "sep": None, "recolor": []}
            return

        # ── Goal ──────────────────────────────────────────────────────────────
        all_g   = self.data["workspaces"].get(
            self.data["active_tab"], {}).get("goals", [])
        vis_idx = sum(1 for g in all_g[:index]
                      if not g.get("done") and g.get("type") != "header")
        bg = t["bg_row2"] if vis_idx % 2 == 1 else t["bg_row"]

        row   = tk.Frame(self.scroll.inner, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=10, pady=7)

        # Complete zone — a subtle box wrapping the circle; clicking anywhere inside completes
        complete_zone = tk.Frame(inner, bg=bg, cursor="hand2",
                                 highlightbackground=t["check_off"],
                                 highlightthickness=1)
        complete_zone.pack(side="left", padx=(0, 6), pady=1)
        chk = tk.Label(complete_zone, text="○", bg=bg, fg=t["check_off"],
                       font=(FONT, 12), cursor="hand2", padx=3, pady=1)
        chk.pack()
        for w in (complete_zone, chk):
            w.bind("<Button-1>", lambda e, i=index: self._complete_goal(i))
            w.bind("<Enter>",    lambda e: (complete_zone.configure(highlightbackground=t["check_on"]),
                                            chk.configure(fg=t["check_on"])))
            w.bind("<Leave>",    lambda e: (complete_zone.configure(highlightbackground=t["check_off"]),
                                            chk.configure(fg=t["check_off"])))
        Tooltip(chk, "Mark complete")

        lbl = tk.Label(inner, text=goal["text"], bg=bg, fg=t["text"],
                       font=(FONT, 10), anchor="w",
                       wraplength=210, justify="left")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 0))

        d = tk.Label(inner, text="×", bg=bg, fg=t["del_idle"],
                     font=(FONT, 13), cursor="hand2")
        d.pack(side="right")
        d.bind("<Button-1>", lambda e, i=index: self._delete_goal(i))
        d.bind("<Enter>",    lambda e, b=d: b.configure(fg=t["del_hov"]))
        d.bind("<Leave>",    lambda e, b=d: b.configure(fg=t["del_idle"]))
        Tooltip(d, "Delete")

        def _goal_context_menu(e, i=index, g=goal):
            menu = tk.Menu(self.root, tearoff=0,
                           bg=t["bg_row2"], fg=t["text"],
                           activebackground=t["check_off"],
                           activeforeground=t["text"],
                           relief="flat", bd=0, font=(FONT, 9))
            menu.add_command(label="Copy text",
                             command=lambda: self._copy_goal_text(g["text"]))
            menu.add_command(label="Edit goal",
                             command=lambda: self._edit_goal(i))
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()

        for w in (row, inner, lbl):
            w.bind("<Button-3>", _goal_context_menu)

        sep_w = tk.Frame(self.scroll.inner, bg=t["border"], height=1)
        sep_w.pack(fill="x")
        self._row_widget_map[uid] = {
            "row_type": "goal", "frame": row, "sep": sep_w,
            "recolor": [row, inner, chk, complete_zone, lbl, d],
            "complete_zone": complete_zone, "chk": chk,
        }

    def _render_completed_section(self):
        t   = self.T
        tab = self.data["active_tab"]
        for w in self.comp_frame.winfo_children():
            w.destroy()

        ws_done = [c for c in self.data.get("completed", [])
                   if c.get("workspace") == tab]
        self.comp_lbl.configure(text=f"Completed  ({len(ws_done)})")

        if not self.comp_open or not ws_done:
            return

        for g in ws_done:
            bg    = t["bg_comp"]
            row   = tk.Frame(self.comp_frame, bg=bg)
            row.pack(fill="x")
            inner = tk.Frame(row, bg=bg)
            inner.pack(fill="x", padx=10, pady=5)

            tk.Label(inner, text="✓", bg=bg, fg=t["check_on"],
                     font=(FONT, 10), width=2).pack(side="left")
                     
            if g.get("type") == "media":
                m_type = g.get("media_type", "file")
                icons = {"image": "🖼️", "audio": "🎵", "video": "🎬", "pdf": "📄", "file": "📁"}
                display_text = f"{icons.get(m_type, '📁')} {g.get('filename', '')}"
            else:
                display_text = g.get("text", "")
                     
            tk.Label(inner, text=display_text, bg=bg, fg=t["text_done"],
                     font=(FONT, 9, "overstrike"), anchor="w",
                     wraplength=175, justify="left"
                     ).pack(side="left", fill="x", expand=True, padx=(4, 0))

            # Restore ↩
            rb = tk.Label(inner, text="↩", bg=bg, fg=t["text_mute"],
                          font=(FONT, 11), cursor="hand2")
            rb.pack(side="right", padx=(0, 4))
            rb.bind("<Button-1>", lambda e, gi=g: self._restore_goal(gi))
            rb.bind("<Enter>",    lambda e, b=rb: b.configure(fg=t["check_on"]))
            rb.bind("<Leave>",    lambda e, b=rb: b.configure(fg=t["text_mute"]))

            d = tk.Label(inner, text="×", bg=bg, fg=t["del_idle"],
                         font=(FONT, 11), cursor="hand2")
            d.pack(side="right")
            d.bind("<Button-1>", lambda e, gi=g: self._remove_completed(gi))
            d.bind("<Enter>",    lambda e, b=d: b.configure(fg=t["del_hov"]))
            d.bind("<Leave>",    lambda e, b=d: b.configure(fg=t["del_idle"]))
            tk.Frame(self.comp_frame, bg=t["border"], height=1).pack(fill="x")

    def _toggle_completed(self):
        self.comp_open = not self.comp_open
        self.comp_arrow.configure(text="▼" if self.comp_open else "▶")
        if self.comp_open:
            self.comp_frame.pack(fill="x", before=self.comp_bar)
            self._render_completed_section()
        else:
            self.comp_frame.pack_forget()

    def _update_count(self, active, total):
        self.count_lbl.configure(
            fg=self.T["text_hint"],
            text=f"{total - active}/{total}" if total else "")

    # ── Goal actions ──────────────────────────────────────────────────────────
    def _complete_goal(self, index):
        self._complete_goal_in_ws(index, self.data["active_tab"])

    def _complete_goal_in_ws(self, index, ws_key):
        goals = self.data["workspaces"].get(ws_key, {}).get("goals", [])
        if index >= len(goals):
            return
        g   = goals[index]
        uid = g.get('_uid')

        goals.pop(index)
        g["done"]         = True
        g["workspace"]    = ws_key
        g["completed_at"] = time.time()
        self.data.setdefault("completed", []).insert(0, g)
        self.data["completed"] = self.data["completed"][:200]
        save_data(self.data)

        # Targeted removal: only when the active tab is showing this workspace
        if uid and uid in self._row_widget_map and ws_key == self.data["active_tab"]:
            self._remove_row_widget(uid)
            # If list is now empty show the placeholder
            if not any(not g2.get("done") for g2 in goals):
                for w in self.scroll.inner.winfo_children():
                    w.destroy()
                self._row_widget_map = {}
                tk.Label(self.scroll.inner,
                         text="Nothing here.\nAdd a goal below.",
                         bg=self.T["bg"], fg=self.T["text_hint"],
                         font=(FONT, 10), justify="center"
                         ).pack(expand=True, pady=36)
            active_ct = sum(1 for g2 in goals
                            if not g2.get("done") and g2.get("type") != "header")
            done_ct   = sum(1 for g2 in goals if g2.get("done"))
            self._update_count(active_ct, active_ct + done_ct)
        else:
            self._render_all()

        if self.comp_open:
            self._render_completed_section()

    def _restore_goal(self, goal_obj):
        """Move a completed goal back to active in its original workspace."""
        self.data["completed"] = [
            c for c in self.data["completed"] if c is not goal_obj]
        ws_key = goal_obj.pop("workspace", self.data["active_tab"])
        goal_obj.pop("done", None)
        goal_obj.pop("completed_at", None)
        ws = self.data["workspaces"].get(ws_key)
        if ws is None:
            ws_key = self.data["active_tab"]
            ws     = self.data["workspaces"].setdefault(
                ws_key, {"name": "Today", "goals": []})
        ws.setdefault("goals", []).append(goal_obj)
        save_data(self.data)
        self._render_all()
        self._render_completed_section()

    def _delete_goal(self, index):
        goals = self._current_goals()
        if index >= len(goals):
            return
        g   = goals[index]
        uid = g.get('_uid')
        goals.pop(index)
        save_data(self.data)

        if uid and uid in self._row_widget_map:
            self._remove_row_widget(uid)
            if not any(not g2.get("done") for g2 in goals):
                for w in self.scroll.inner.winfo_children():
                    w.destroy()
                self._row_widget_map = {}
                tk.Label(self.scroll.inner,
                         text="Nothing here.\nAdd a goal below.",
                         bg=self.T["bg"], fg=self.T["text_hint"],
                         font=(FONT, 10), justify="center"
                         ).pack(expand=True, pady=36)
            active_ct = sum(1 for g2 in goals
                            if not g2.get("done") and g2.get("type") != "header")
            done_ct   = sum(1 for g2 in goals if g2.get("done"))
            self._update_count(active_ct, active_ct + done_ct)
        else:
            self._render_all()

    def _copy_goal_text(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _edit_goal(self, index):
        goals = self._current_goals()
        if index >= len(goals):
            return
        goal = goals[index]
        current_text = goal.get("text", "")
        new_text = simpledialog.askstring(
            "Edit Goal", "Edit goal text:",
            initialvalue=current_text, parent=self.root)
        if new_text is not None and new_text.strip():
            goal["text"] = new_text.strip()
            save_data(self.data)
            self._render_all()

    def _add_goal(self, event=None):
        # If hint is showing, Enter just focuses the entry so user can start typing
        if self._hint_active:
            self._focus_entry()
            return
        text = self.entry_var.get().strip()
        if not text:
            self._focus_entry()
            return

        if self._input_mode == "header_sm":
            item = {"type": "header", "size": "sm", "text": text}
        elif self._input_mode == "header_lg":
            item = {"type": "header", "size": "lg", "text": text}
        else:
            item = {"text": text, "done": False}

        goals = self._current_goals()
        goals.append(item)
        save_data(self.data)

        self._hint_active = False
        self.entry_var.set("")
        self.entry.configure(fg=self.T["text"])
        self.entry.focus_set()

        # Headers sort to the top of the display, so they require a full rebuild.
        # Regular goals and media always append to the visible bottom — targeted add.
        if self._input_mode in ("header_sm", "header_lg"):
            self._render_all()
        else:
            # Clear "nothing here" placeholder if it was showing
            if not self._row_widget_map:
                for w in self.scroll.inner.winfo_children():
                    w.destroy()
            new_index = len(goals) - 1
            self._render_row(new_index, item)
            active_ct = sum(1 for g in goals
                            if not g.get("done") and g.get("type") != "header")
            done_ct   = sum(1 for g in goals if g.get("done"))
            self._update_count(active_ct, active_ct + done_ct)

        self.root.after(50, lambda: self.scroll.canvas.yview_moveto(1.0))

    def _remove_completed(self, goal_obj):
        self.data["completed"] = [c for c in self.data["completed"]
                                   if c is not goal_obj]
        save_data(self.data)
        self._render_completed_section()
        self._render_all()

    def _clear_completed(self):
        tab = self.data["active_tab"]
        self.data["completed"] = [c for c in self.data.get("completed", [])
                                   if c.get("workspace") != tab]
        save_data(self.data)
        if self.comp_open:
            self._render_completed_section()
        self._render_all()

    def _cleanup_old_completed(self):
        """Purge completed items older than 24 h. Runs once on startup, then hourly."""
        cutoff = time.time() - 86400
        before = len(self.data.get("completed", []))
        self.data["completed"] = [
            c for c in self.data.get("completed", [])
            if c.get("completed_at", time.time()) > cutoff
        ]
        if len(self.data["completed"]) != before:
            save_data(self.data)
            try:
                if self.comp_open:
                    self._render_completed_section()
                self._render_all()
            except Exception:
                pass
        self.root.after(3_600_000, self._cleanup_old_completed)

    # ── Drag ──────────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(
            f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── Visibility ────────────────────────────────────────────────────────────
    def _toggle_visibility(self):
        if self.visible:
            self.root.withdraw()
            self.visible      = False
            self._user_hidden = True   # user chose to hide — suppress auto-show
        else:
            self.root.deiconify()
            self.root.lift()
            self.visible      = True
            self._user_hidden = False

    def _show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.visible      = True
        self._user_hidden = False

    # ── Resize ────────────────────────────────────────────────────────────────
    def _cycle_size(self):
        self._size_idx = (self._size_idx + 1) % len(SIZE_PRESETS)
        self.data["settings"]["size_idx"] = self._size_idx
        save_data(self.data)
        cw, ch = self._current_wh()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{cw}x{ch}+{x}+{y}")
        self.size_btn.configure(text=SIZE_LABELS[self._size_idx])

    # ── File Share ────────────────────────────────────────────────────────────
    def _open_fileshare(self):
        if self._share_win and self._share_win.alive:
            self._share_win.win.lift()
            return
        self._share_win = FileSharePanel(self)

    def _flash_share_btn(self, filename=""):
        """Briefly highlight ⇄ to signal an incoming file when panel is closed."""
        try:
            btn = self._share_btn_ref
            t   = self.T
            btn.configure(fg=self.T["check_on"])
            # Tooltip-style label under the button
            tip = tk.Label(self.root, text=f"📱 {filename} saved to Downloads",
                           bg=t["check_on"], fg="#000",
                           font=(FONT, 8), padx=8, pady=4)
            tip.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=46)
            def restore():
                try:
                    btn.configure(fg=t["tab_act"])
                    tip.destroy()
                except Exception:
                    pass
            self.root.after(3500, restore)
        except Exception:
            pass

    # ── Settings ──────────────────────────────────────────────────────────────
    def _open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            return

        win = tk.Toplevel(self.root)
        self.settings_win = win
        win.title("DeskGoals — Settings")
        win.configure(bg=S["bg"])
        win.geometry("400x640")
        win.resizable(False, False)
        win.attributes("-topmost", True)

        hdr = tk.Frame(win, bg=S["bg"])
        hdr.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(hdr, text="Settings", bg=S["bg"], fg=S["text"],
                 font=(FONT, 14, "bold")).pack(side="left")
        tk.Label(hdr, text="Changes apply instantly", bg=S["bg"],
                 fg=S["mute"], font=(FONT, 8)).pack(side="left", padx=10)
        tk.Frame(win, bg=S["border"], height=1).pack(fill="x")

        body = ScrollFrame(win, bg=S["bg"])
        body.pack(fill="both", expand=True)
        f = body.inner

        def slbl(parent, text, size=9, bold=False, mute=False, **kw):
            return tk.Label(parent, text=text, bg=S["bg"],
                            fg=S["mute"] if mute else S["text"],
                            font=(FONT, size, "bold" if bold else "normal"), **kw)

        def sep():
            tk.Frame(f, bg=S["border"], height=1).pack(fill="x", padx=16, pady=10)

        def section(title):
            row = tk.Frame(f, bg=S["bg"])
            row.pack(fill="x", padx=16, pady=(12, 4))
            tk.Label(row, text=title.upper(), bg=S["bg"], fg=S["accent"],
                     font=(FONT, 7, "bold")).pack(side="left")
            tk.Frame(row, bg=S["border"], height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0))

        # ── APPEARANCE ────────────────────────────────────────────────────────
        section("Appearance")

        theme_row = tk.Frame(f, bg=S["bg"])
        theme_row.pack(fill="x", padx=16, pady=4)
        slbl(theme_row, "Theme").pack(side="left")
        for name, swatch in THEMES.items():
            active = (name == self.data["settings"].get("theme", "Dark"))
            btn = tk.Label(theme_row, text=name,
                           bg=swatch["bg_header"],
                           fg=swatch["tab_act"] if active else swatch["tab_idle"],
                           font=(FONT, 8, "bold" if active else "normal"),
                           relief="solid" if active else "flat",
                           bd=1 if active else 0,
                           padx=8, pady=4, cursor="hand2")
            btn.pack(side="right", padx=3)
            btn.bind("<Button-1>", lambda e, n=name: self._set_theme(n))

        a_row = tk.Frame(f, bg=S["bg"])
        a_row.pack(fill="x", padx=16, pady=(10, 2))
        slbl(a_row, "Transparency").pack(side="left")
        a_val = tk.Label(a_row, bg=S["bg"], fg=S["mute"], font=(FONT, 8), width=16)
        a_val.pack(side="right")
        cur_a = self.data["settings"].get("alpha", 0.93)
        a_val.configure(text=f"{int((1 - cur_a) * 100)}% transparent")

        _alpha_save_id = [None]
        def on_alpha(val):
            a = round(float(val), 2)
            self.data["settings"]["alpha"] = a
            self.root.attributes("-alpha", a)
            a_val.configure(text=f"{int((1 - a) * 100)}% transparent")
            # Debounce — only write to disk 400 ms after dragging stops
            if _alpha_save_id[0]:
                win.after_cancel(_alpha_save_id[0])
            _alpha_save_id[0] = win.after(400, lambda: save_data(self.data))

        alpha_scale = tk.Scale(f, from_=0.3, to=1.0, resolution=0.01,
                               orient="horizontal", command=on_alpha,
                               bg=S["bg"], fg=S["text"], troughcolor=S["bg3"],
                               highlightthickness=0, bd=0, showvalue=False,
                               sliderlength=14, width=6)
        alpha_scale.set(cur_a)
        alpha_scale.pack(fill="x", padx=16, pady=(0, 6))

        aot_row = tk.Frame(f, bg=S["bg"])
        aot_row.pack(fill="x", padx=16, pady=4)
        slbl(aot_row, "Always on top").pack(side="left")
        aot_var = tk.BooleanVar(
            value=self.data["settings"].get("always_on_top", True))
        aot_lbl = tk.Label(aot_row, bg=S["bg"], font=(FONT, 9, "bold"),
                           cursor="hand2", width=4)
        aot_lbl.pack(side="right")

        def refresh_aot():
            on = aot_var.get()
            aot_lbl.configure(text="ON" if on else "OFF",
                              fg=S["accent"] if on else S["mute"])

        def toggle_aot(e=None):
            aot_var.set(not aot_var.get())
            v = aot_var.get()
            self.data["settings"]["always_on_top"] = v
            self.root.attributes("-topmost", v)
            save_data(self.data)
            refresh_aot()

        aot_lbl.bind("<Button-1>", toggle_aot)
        refresh_aot()
        sep()

        # ── HOTKEY ────────────────────────────────────────────────────────────
        section("Global Hotkey")
        slbl(f, "Click Record, then press your combo.",
             mute=True).pack(anchor="w", padx=16, pady=(0, 6))

        hk_row = tk.Frame(f, bg=S["bg"])
        hk_row.pack(fill="x", padx=16)
        current_hk = self.data["settings"].get("hotkey", "ctrl+alt+g")
        hk_disp = tk.Label(hk_row, text=current_hk, bg=S["bg3"],
                            fg=S["text"], font=(FONT, 10),
                            padx=10, pady=6, width=20, anchor="w")
        hk_disp.pack(side="left")
        rec_btn = tk.Label(hk_row, text="  Record  ", bg=S["accent"],
                           fg="#fff", font=(FONT, 9, "bold"),
                           padx=6, pady=6, cursor="hand2")
        rec_btn.pack(side="left", padx=(8, 0))
        hk_status = slbl(f, "", mute=True)
        hk_status.pack(anchor="w", padx=16, pady=(4, 0))

        self._recording = False
        self._hk_parts  = []

        def on_kp(e):
            if not self._recording:
                return
            sym = e.keysym.lower()
            sym = {"control_l": "ctrl", "control_r": "ctrl",
                   "alt_l": "alt",     "alt_r": "alt",
                   "shift_l": "shift", "shift_r": "shift",
                   "super_l": "win",   "super_r": "win"}.get(sym, sym)
            if sym not in self._hk_parts:
                self._hk_parts.append(sym)
            hk_disp.configure(text="+".join(self._hk_parts))

        def on_kr(e):
            if not self._recording:
                return
            sym = e.keysym.lower()
            if sym in ("control_l", "control_r", "alt_l", "alt_r",
                       "shift_l", "shift_r", "super_l", "super_r"):
                return
            self._recording = False
            win.unbind("<KeyPress>")
            win.unbind("<KeyRelease>")
            combo = "+".join(self._hk_parts)
            self.data["settings"]["hotkey"] = combo
            save_data(self.data)
            hk_disp.configure(text=combo)
            rec_btn.configure(bg=S["accent"], text="  Record  ")
            hk_status.configure(text=f"✓  Saved: {combo}")
            self._register_hotkey()

        def start_rec(e=None):
            self._recording = True
            self._hk_parts  = []
            rec_btn.configure(bg="#c44444", text="● Recording")
            hk_disp.configure(text="Press keys...")
            hk_status.configure(text="Hold combo then release to confirm.")
            win.bind("<KeyPress>",   on_kp)
            win.bind("<KeyRelease>", on_kr)

        rec_btn.bind("<Button-1>", start_rec)
        sep()

        # ── WORKSPACES ────────────────────────────────────────────────────────
        section("Workspaces")

        ws_container = tk.Frame(f, bg=S["bg"])
        ws_container.pack(fill="x", padx=16)

        def build_ws():
            for w in ws_container.winfo_children():
                w.destroy()
            for key, ws in self.data["workspaces"].items():
                r  = tk.Frame(ws_container, bg=S["bg2"])
                r.pack(fill="x", pady=2)
                ct = len([g for g in ws.get("goals", []) if not g.get("done")])
                tk.Label(r, text=ws["name"], bg=S["bg2"], fg=S["text"],
                         font=(FONT, 9), anchor="w"
                         ).pack(side="left", padx=10, pady=6, fill="x", expand=True)
                tk.Label(r, text=f"{ct} active", bg=S["bg2"],
                         fg=S["mute"], font=(FONT, 7)).pack(side="left", padx=6)
                if key != "main":
                    dl = tk.Label(r, text="Delete", bg=S["bg2"],
                                  fg=S["danger"], font=(FONT, 8), cursor="hand2")
                    dl.pack(side="right", padx=10)
                    dl.bind("<Button-1>",
                            lambda e, k=key: self._delete_workspace(k, build_ws))

        build_ws()
        self._settings_rebuild_ws = build_ws

        # Inline create form
        new_ws_row = tk.Frame(f, bg=S["bg"])
        new_ws_row.pack(fill="x", padx=16, pady=(6, 0))
        new_ws_var = tk.StringVar()
        new_ws_entry = tk.Entry(new_ws_row, textvariable=new_ws_var,
                                bg=S["input_bg"], fg=S["input_fg"],
                                insertbackground=S["input_fg"],
                                relief="flat", font=(FONT, 9), width=18)
        new_ws_entry.pack(side="left", padx=(0, 6), ipady=4)
        new_ws_entry.insert(0, "New workspace name")
        new_ws_entry.configure(fg=S["mute"])

        def on_ws_focus_in(e):
            if new_ws_entry.get() == "New workspace name":
                new_ws_entry.delete(0, "end")
                new_ws_entry.configure(fg=S["input_fg"])

        def on_ws_focus_out(e):
            if not new_ws_entry.get().strip():
                new_ws_entry.delete(0, "end")
                new_ws_entry.insert(0, "New workspace name")
                new_ws_entry.configure(fg=S["mute"])

        new_ws_entry.bind("<FocusIn>",  on_ws_focus_in)
        new_ws_entry.bind("<FocusOut>", on_ws_focus_out)

        def create_ws_from_settings():
            name = new_ws_var.get().strip()
            if not name or name == "New workspace name":
                return
            key = f"ws_{len(self.data['workspaces'])}_{name.lower().replace(' ', '_')}"
            self.data["workspaces"][key] = {"name": name, "goals": []}
            self.data["active_tab"] = key
            save_data(self.data)
            new_ws_var.set("")
            new_ws_entry.delete(0, "end")
            new_ws_entry.insert(0, "New workspace name")
            new_ws_entry.configure(fg=S["mute"])
            build_ws()
            self._refresh_tabs()
            self._render_all()
            self._sync_settings()

        new_ws_entry.bind("<Return>", lambda e: create_ws_from_settings())
        create_btn = tk.Label(new_ws_row, text=" Create ", bg=S["accent"],
                              fg="#fff", font=(FONT, 8, "bold"),
                              padx=6, pady=4, cursor="hand2")
        create_btn.pack(side="left")
        create_btn.bind("<Button-1>", lambda e: create_ws_from_settings())
        sep()

        # ── APP-SENSITIVE WORKSPACES ──────────────────────────────────────────
        section("App-Sensitive Workspaces")
        slbl(f, "Auto-switch workspace when an app gains focus.",
             mute=True).pack(anchor="w", padx=16, pady=(0, 2))

        as_row = tk.Frame(f, bg=S["bg"])
        as_row.pack(fill="x", padx=16, pady=(0, 8))
        slbl(as_row, "Auto-show widget on app focus").pack(side="left")
        as_var = tk.BooleanVar(
            value=self.data["settings"].get("auto_show", True))
        as_lbl = tk.Label(as_row, bg=S["bg"], font=(FONT, 9, "bold"),
                          cursor="hand2", width=4)
        as_lbl.pack(side="right")

        def refresh_as():
            on = as_var.get()
            as_lbl.configure(text="ON" if on else "OFF",
                             fg=S["accent"] if on else S["mute"])

        def toggle_as(e=None):
            as_var.set(not as_var.get())
            self.data["settings"]["auto_show"] = as_var.get()
            save_data(self.data)
            refresh_as()

        as_lbl.bind("<Button-1>", toggle_as)
        refresh_as()

        rules_cont    = tk.Frame(f, bg=S["bg"])
        rules_cont.pack(fill="x", padx=16)
        add_rule_cont = tk.Frame(f, bg=S["bg"])
        add_rule_cont.pack(fill="x", padx=16)

        def build_rules():
            for w in rules_cont.winfo_children():
                w.destroy()
            rules = self.data.get("app_rules", {})
            if not rules:
                tk.Label(rules_cont, text="No rules yet.",
                         bg=S["bg"], fg=S["mute"], font=(FONT, 8)
                         ).pack(anchor="w", pady=2)
            else:
                for proc, ws_key in list(rules.items()):
                    ws_name = self.data["workspaces"].get(
                        ws_key, {}).get("name", ws_key)
                    r = tk.Frame(rules_cont, bg=S["bg2"])
                    r.pack(fill="x", pady=2)
                    tk.Label(r, text=proc, bg=S["bg2"], fg=S["text"],
                             font=(FONT, 9, "bold"), width=16, anchor="w"
                             ).pack(side="left", padx=8, pady=5)
                    tk.Label(r, text=f"→  {ws_name}", bg=S["bg2"],
                             fg=S["mute"], font=(FONT, 8)).pack(side="left")
                    xb = tk.Label(r, text="×", bg=S["bg2"], fg=S["mute"],
                                  font=(FONT, 11), cursor="hand2")
                    xb.pack(side="right", padx=8)
                    xb.bind("<Button-1>", lambda e, p=proc: [
                        self.data["app_rules"].pop(p, None),
                        save_data(self.data),
                        build_rules()])

            # Rebuild the add-rule form with up-to-date workspace list
            for w in add_rule_cont.winfo_children():
                w.destroy()

            proc_var = tk.StringVar()
            ws_names = {v["name"]: k for k, v in self.data["workspaces"].items()}
            ws_var   = tk.StringVar()
            if ws_names:
                ws_var.set(list(ws_names)[0])

            r1 = tk.Frame(add_rule_cont, bg=S["bg"])
            r1.pack(fill="x", pady=2)
            tk.Label(r1, text="Process (.exe):", bg=S["bg"], fg=S["mute"],
                     font=(FONT, 8), width=14, anchor="w").pack(side="left")
            tk.Entry(r1, textvariable=proc_var, bg=S["input_bg"],
                     fg=S["input_fg"], insertbackground=S["input_fg"],
                     relief="flat", font=(FONT, 9), width=18
                     ).pack(side="left", padx=(4, 0))

            r2 = tk.Frame(add_rule_cont, bg=S["bg"])
            r2.pack(fill="x", pady=2)
            tk.Label(r2, text="Workspace:", bg=S["bg"], fg=S["mute"],
                     font=(FONT, 8), width=14, anchor="w").pack(side="left")
            ws_opts = list(ws_names.keys()) if ws_names else ["Today"]
            om = tk.OptionMenu(r2, ws_var, *ws_opts)
            om.configure(bg=S["input_bg"], fg=S["input_fg"],
                         activebackground=S["bg3"], relief="flat",
                         font=(FONT, 9), bd=0)
            om.pack(side="left", padx=(4, 0))

            def add_rule():
                proc = proc_var.get().strip()
                ws_k = ws_names.get(ws_var.get())
                if proc and ws_k:
                    self.data.setdefault("app_rules", {})[proc] = ws_k
                    save_data(self.data)
                    proc_var.set("")
                    build_rules()

            arb = tk.Label(add_rule_cont, text="  Add Rule  ", bg=S["accent"],
                           fg="#ffffff", font=(FONT, 8, "bold"),
                           padx=10, pady=4, cursor="hand2")
            arb.pack(anchor="e", pady=6)
            arb.bind("<Button-1>", lambda e: add_rule())

        build_rules()
        self._settings_rebuild_rules = build_rules
        sep()

        # ── PHONE SYNC ────────────────────────────────────────────────────────
        section("Phone Sync  (Local Wi-Fi)")
        slbl(f, "Access goals from any device on the same network.",
             mute=True).pack(anchor="w", padx=16, pady=(0, 6))

        sync_var = tk.BooleanVar(
            value=self.data["settings"].get("sync_enabled", False))
        sync_row = tk.Frame(f, bg=S["bg"])
        sync_row.pack(fill="x", padx=16, pady=4)
        slbl(sync_row, "Enable sync server").pack(side="left")
        sync_lbl = tk.Label(sync_row, bg=S["bg"], font=(FONT, 9, "bold"),
                            cursor="hand2", width=4)
        sync_lbl.pack(side="right")

        port_val = tk.IntVar(
            value=self.data["settings"].get("sync_port", 7842))
        ip_str   = get_local_ip()

        url_lbl = tk.Label(f, bg=S["bg2"], fg=S["accent"],
                           font=(FONT, 10), padx=12, pady=8)
        url_lbl.pack(fill="x", padx=16, pady=(4, 2))

        def refresh_sync_ui():
            on = sync_var.get()
            sync_lbl.configure(text="ON" if on else "OFF",
                               fg=S["accent"] if on else S["mute"])
            url_lbl.configure(
                text=f"http://{ip_str}:{port_val.get()}" if on
                else "Server is off — toggle ON to start")

        def toggle_sync(e=None):
            sync_var.set(not sync_var.get())
            v = sync_var.get()
            self.data["settings"]["sync_enabled"] = v
            save_data(self.data)
            if v:
                self._start_sync_server()
            else:
                self._stop_sync_server()
            refresh_sync_ui()

        sync_lbl.bind("<Button-1>", toggle_sync)
        refresh_sync_ui()

        port_row = tk.Frame(f, bg=S["bg"])
        port_row.pack(fill="x", padx=16, pady=(2, 0))
        slbl(port_row, "Port", mute=True).pack(side="left")
        port_entry = tk.Entry(port_row, textvariable=port_val,
                              bg=S["input_bg"], fg=S["input_fg"],
                              insertbackground=S["input_fg"],
                              relief="flat", font=(FONT, 9), width=8)
        port_entry.pack(side="left", padx=(8, 0))

        def apply_port(e=None):
            try:
                p = int(port_val.get())
                assert 1024 <= p <= 65535
                self.data["settings"]["sync_port"] = p
                save_data(self.data)
                if sync_var.get():
                    self._stop_sync_server()
                    self._start_sync_server()
                refresh_sync_ui()
            except Exception:
                port_val.set(self.data["settings"].get("sync_port", 7842))

        port_entry.bind("<Return>",   apply_port)
        port_entry.bind("<FocusOut>", apply_port)

        tk.Frame(f, bg=S["bg"], height=30).pack()

    # ── Settings sync ─────────────────────────────────────────────────────────
    def _sync_settings(self):
        if not (self.settings_win and self.settings_win.winfo_exists()):
            return
        for fn in (self._settings_rebuild_ws, self._settings_rebuild_rules):
            if fn:
                try:
                    fn()
                except Exception:
                    pass

    def _set_theme(self, name):
        self.data["settings"]["theme"] = name
        save_data(self.data)
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.destroy()
            self.settings_win = None
        self._full_redraw()
        self.root.after(80, self._open_settings)

    # ── Hotkey ────────────────────────────────────────────────────────────────
    def _register_hotkey(self):
        if not HAS_HOTKEY:
            return
        try:
            if self._hotkey_id is not None:
                keyboard.remove_hotkey(self._hotkey_id)
                self._hotkey_id = None
        except Exception:
            pass
        combo = self.data["settings"].get("hotkey", "ctrl+alt+g")
        try:
            self._hotkey_id = keyboard.add_hotkey(
                combo, lambda: self.root.after(0, self._toggle_visibility))
        except Exception as e:
            log_error(f"hotkey register failed ({combo}): {e}")

    # ── App detection + auto-show ─────────────────────────────────────────────
    def _app_watch_loop(self):
        # Determine our own process name so we can skip it and avoid
        # _prev_focused_proc getting stuck when DeskGoals steals focus.
        try:
            _own_proc = psutil.Process(os.getpid()).name().lower()
        except Exception:
            _own_proc = "python.exe"

        while True:
            # If no rules, nothing to watch — check again in 5s
            if not self.data.get("app_rules"):
                time.sleep(5)
                continue
            try:
                hwnd   = win32gui.GetForegroundWindow()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc   = psutil.Process(pid).name().lower()

                # Ignore our own window stealing focus — don't update
                # _prev_focused_proc so we remember the real last app.
                if proc == _own_proc:
                    time.sleep(1.5)
                    continue

                if proc != self._prev_focused_proc:
                    self._prev_focused_proc = proc
                    for pattern, ws_key in list(self.data.get("app_rules", {}).items()):
                        if pattern.lower() in proc:
                            same_ws  = (ws_key == self.data["active_tab"])
                            valid_ws = (ws_key in self.data["workspaces"])
                            if not same_ws and valid_ws:
                                # Enqueue workspace switch — processed on main thread
                                self._user_hidden = False
                                self.data["active_tab"] = ws_key
                                self._app_switch_queue.put(("switch", ws_key))
                            elif (not self.visible
                                  and not self._user_hidden
                                  and self.data["settings"].get("auto_show", True)):
                                self._app_switch_queue.put(("show", None))
                            break
            except Exception:
                pass
            time.sleep(1.5)

    def _poll_app_switch_queue(self):
        """Drain the thread-safe queue on the main thread and act on events."""
        try:
            while True:
                event, ws_key = self._app_switch_queue.get_nowait()
                if event == "switch":
                    self._on_app_switch(ws_key)
                elif event == "show":
                    self.root.deiconify()
                    self.visible = True
        except queue.Empty:
            pass
        # Re-schedule — poll every 200 ms (well within the 1.5 s watch interval)
        self.root.after(200, self._poll_app_switch_queue)

    def _on_app_switch(self, ws_key):
        ws_name = self.data["workspaces"].get(ws_key, {}).get("name", "")
        self.app_badge.configure(text=f"● {ws_name}")
        self._refresh_tabs()
        self._render_all()
        save_data(self.data)
        # Only auto-show if user hasn't explicitly hidden the widget
        if (self.data["settings"].get("auto_show", True)
                and not self.visible
                and not self._user_hidden):
            self.root.deiconify()
            self.visible = True

    # ── Workspace delete ──────────────────────────────────────────────────────
    def _delete_workspace(self, key, rebuild_fn=None):
        if key == "main":
            return
        name = self.data["workspaces"][key]["name"]
        if messagebox.askyesno(
                "Delete Workspace",
                f"Delete '{name}'?\nGoals will be lost.",
                parent=self.settings_win or self.root):
            del self.data["workspaces"][key]
            if self.data["active_tab"] == key:
                self.data["active_tab"] = "main"
            save_data(self.data)
            if rebuild_fn:
                rebuild_fn()
            self._refresh_tabs()
            self._render_all()

    def _rename_workspace(self, key):
        ws = self.data["workspaces"].get(key)
        if not ws:
            return
        new_name = simpledialog.askstring(
            "Rename Space", "New name:",
            initialvalue=ws["name"], parent=self.root)
        if new_name and new_name.strip():
            ws["name"] = new_name.strip()
            save_data(self.data)
            self._refresh_tabs()
            self._render_all()
            self._sync_settings()

    def _tab_context_menu(self, event, key):
        t = self.T
        menu = tk.Menu(self.root, tearoff=0,
                       bg=t["bg_header"], fg=t["text"],
                       activebackground=t["check_off"],
                       activeforeground=t["text"],
                       relief="flat", bd=0, font=(FONT, 9))
        menu.add_command(label="Rename",
                         command=lambda: self._rename_workspace(key))
        if key != "main":
            menu.add_separator()
            menu.add_command(label="Delete",
                             command=lambda: self._delete_workspace(key))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ── Phone sync server ─────────────────────────────────────────────────────
    def _start_sync_server(self):
        if self._sync_server:
            return
        try:
            port = self.data["settings"].get("sync_port", 7842)
            MobileHandler.app = self
            self._sync_server  = ServerClass(("0.0.0.0", port), MobileHandler)
            threading.Thread(target=self._sync_server.serve_forever,
                             daemon=True).start()
        except Exception as e:
            log_error(f"sync server failed to start: {e}")
            self._sync_server = None

    def _stop_sync_server(self):
        if self._sync_server:
            try:
                self._sync_server.shutdown()
            except Exception:
                pass
            self._sync_server = None

    # ── System tray ───────────────────────────────────────────────────────────
    def _setup_tray(self):
        if not HAS_TRAY:
            return
        sz  = 64
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)
        try:
            d.rounded_rectangle([4, 4, 60, 60], radius=12,
                                 fill=(18, 18, 18, 240),
                                 outline=(70, 70, 70), width=2)
        except AttributeError:
            d.rectangle([4, 4, 60, 60], fill=(18, 18, 18, 240),
                        outline=(70, 70, 70), width=2)
        for y_, w_ in [(20, 36), (30, 28), (40, 20)]:
            d.line([13, y_, 13 + w_, y_], fill=(180, 180, 180), width=2)
        d.ellipse([10, 16, 17, 23], fill=(90, 220, 90))

        hk   = self.data["settings"].get("hotkey", "ctrl+alt+g")
        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide",
                lambda *_: self.root.after(0, self._toggle_visibility),
                default=True),
            pystray.MenuItem("Settings",
                lambda *_: self.root.after(0, self._open_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",
                lambda *_: self.root.after(0, self._quit)),
        )
        self.tray = pystray.Icon(
            "DeskGoals", img, f"DeskGoals  ({hk})", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    # ── Quit ──────────────────────────────────────────────────────────────────
    def _quit(self):
        self._save_position()
        self._stop_sync_server()
        if self._share_win and self._share_win.alive:
            try:
                self._share_win._cleanup()
            except Exception:
                pass
        if HAS_TRAY:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()




# ── P2P File Share Panel ──────────────────────────────────────────────────────
import http.client as _http_client
from tkinter import filedialog as _filedialog

P = {   # panel palette — always dark regardless of theme
    "bg":      "#111318",
    "bg2":     "#1a1d24",
    "bg3":     "#22262f",
    "border":  "#2a2f3a",
    "text":    "#dde2ec",
    "mute":    "#6b7280",
    "accent":  "#4f8ef7",
    "green":   "#3ecf6e",
    "red":     "#e05555",
    "bar_bg":  "#1e2230",
    "bar_fg":  "#4f8ef7",
    "send_fg": "#3ecf6e",
    "recv_fg": "#c97bf7",
}

def _fmt_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class _TransferRow:
    """One row in the transfers list — owns its own canvas progress bar."""
    H = 62

    def __init__(self, parent, tid, filename, total, peer, incoming):
        self.tid      = tid
        self.total    = total
        self.received = 0
        self.done     = False
        self.error    = False
        self._t_start = time.time()
        self._last_b  = 0
        self._last_t  = time.time()
        self._speed   = 0.0

        direction_col = P["recv_fg"] if incoming else P["send_fg"]
        arrow         = "↓" if incoming else "↑"

        self.frame = tk.Frame(parent, bg=P["bg2"])
        self.frame.pack(fill="x", pady=(0, 2))

        top = tk.Frame(self.frame, bg=P["bg2"])
        top.pack(fill="x", padx=12, pady=(8, 2))

        tk.Label(top, text=arrow, bg=P["bg2"], fg=direction_col,
                 font=("Segoe UI", 11, "bold"), width=2).pack(side="left")

        name_lbl = tk.Label(top, text=filename, bg=P["bg2"], fg=P["text"],
                            font=("Segoe UI", 9, "bold"), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True)

        self.pct_lbl = tk.Label(top, text="0%", bg=P["bg2"], fg=P["mute"],
                                 font=("Segoe UI", 8))
        self.pct_lbl.pack(side="right")

        bar_frame = tk.Frame(self.frame, bg=P["bg2"])
        bar_frame.pack(fill="x", padx=12, pady=(2, 4))

        self.bar = tk.Canvas(bar_frame, height=5, bg=P["bar_bg"],
                             highlightthickness=0, bd=0)
        self.bar.pack(fill="x", side="left", expand=True)

        bot = tk.Frame(self.frame, bg=P["bg2"])
        bot.pack(fill="x", padx=12, pady=(0, 6))

        self.peer_lbl = tk.Label(bot, text=peer, bg=P["bg2"], fg=P["mute"],
                                  font=("Segoe UI", 7))
        self.peer_lbl.pack(side="left")

        self.speed_lbl = tk.Label(bot, text="", bg=P["bg2"], fg=P["mute"],
                                   font=("Segoe UI", 7))
        self.speed_lbl.pack(side="right")

        tk.Frame(self.frame, bg=P["border"], height=1).pack(fill="x")

    def update(self, received, total=None):
        if total:
            self.total = total
        self.received = received

        now = time.time()
        dt  = now - self._last_t
        if dt >= 0.4:
            self._speed  = (received - self._last_b) / dt
            self._last_b = received
            self._last_t = now

        pct = (received / self.total * 100) if self.total else 0
        self.pct_lbl.configure(text=f"{pct:.0f}%")
        self.speed_lbl.configure(text=_fmt_size(self._speed) + "/s")

        # Redraw bar
        self.bar.update_idletasks()
        w = self.bar.winfo_width() or 200
        self.bar.delete("all")
        filled = int(w * pct / 100)
        if filled > 0:
            self.bar.create_rectangle(0, 0, filled, 5,
                                      fill=P["bar_fg"], outline="")

    def mark_done(self, success=True):
        self.done = True
        col = P["green"] if success else P["red"]
        label = "Done" if success else "Failed"
        self.pct_lbl.configure(text=label, fg=col)
        self.speed_lbl.configure(text="")
        self.bar.delete("all")
        w = self.bar.winfo_width() or 200
        self.bar.create_rectangle(0, 0, w, 5, fill=col, outline="")


class FileSharePanel:
    """Floating P2P file share window with discovery + transfer."""

    def __init__(self, master_app):
        self.app   = master_app
        self.alive = True

        # Shared state (written from threads, read from UI via after())
        self._peers     = {}      # name -> {"ip": str, "ts": float}
        self._transfers = {}      # tid -> _TransferRow
        self._server    = None

        self._build_window()
        self._start_server()
        threading.Thread(target=self._discover_loop,  daemon=True).start()
        threading.Thread(target=self._announce_loop,  daemon=True).start()
        self._poll_peers()

    # ── Window ────────────────────────────────────────────────────────────────
    def _build_window(self):
        self.win = tk.Toplevel(self.app.root)
        self.win.title("DeskGoals Share")
        self.win.configure(bg=P["bg"])
        self.win.geometry("420x560")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.overrideredirect(True)
        self.win.protocol("WM_DELETE_WINDOW", self._close)

        # Position near main widget
        mx = self.app.root.winfo_x()
        my = self.app.root.winfo_y()
        mw, _ = self.app._current_wh()
        self.win.geometry(f"420x560+{mx - 430}+{my}")

        # Header
        hdr = tk.Frame(self.win, bg=P["bg3"], height=44, cursor="fleur")
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        hdr.bind("<ButtonPress-1>",   self._drag_start)
        hdr.bind("<B1-Motion>",       self._drag_move)
        self._dx = self._dy = 0

        tk.Label(hdr, text="⇄", bg=P["bg3"], fg=P["accent"],
                 font=("Segoe UI", 14)).pack(side="left", padx=(14, 6))
        tk.Label(hdr, text="File Share", bg=P["bg3"], fg=P["text"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")

        self._status_dot = tk.Label(hdr, text="●", bg=P["bg3"],
                                     fg=P["mute"], font=("Segoe UI", 9))
        self._status_dot.pack(side="left", padx=(8, 0))
        self._status_lbl = tk.Label(hdr, text="Starting...", bg=P["bg3"],
                                     fg=P["mute"], font=("Segoe UI", 8))
        self._status_lbl.pack(side="left", padx=(3, 0))

        close_btn = tk.Label(hdr, text="×", bg=P["bg3"], fg=P["mute"],
                             font=("Segoe UI", 16), cursor="hand2")
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Button-1>", lambda e: self._close())

        tk.Frame(self.win, bg=P["border"], height=1).pack(fill="x")

        body = tk.Frame(self.win, bg=P["bg"])
        body.pack(fill="both", expand=True)

        # ── Peers section ─────────────────────────────────────────────────
        self._section(body, "NEARBY DEVICES")
        
        if not self.app.data["settings"].get("sync_enabled", False):
            warn_lbl = tk.Label(body, text="⚠️ Sync Server is OFF in Settings.\nBrowsers cannot connect to you.",
                                bg=P["bg"], fg=P["red"], font=("Segoe UI", 8, "bold"), justify="left")
            warn_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        self._peers_frame = tk.Frame(body, bg=P["bg"])
        self._peers_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._no_peers_lbl = tk.Label(self._peers_frame,
                                       text="Scanning for devices...",
                                       bg=P["bg"], fg=P["mute"],
                                       font=("Segoe UI", 9))
        self._no_peers_lbl.pack(anchor="w", pady=6)

        # Manual IP entry (fallback when auto-discovery is blocked)
        manual_row = tk.Frame(body, bg=P["bg"])
        manual_row.pack(fill="x", padx=12, pady=(4, 8))
        tk.Label(manual_row, text="Add PC manually (IP):", bg=P["bg"],
                 fg=P["mute"], font=("Segoe UI", 8)).pack(side="left")
        self._manual_ip_var = tk.StringVar()
        manual_entry = tk.Entry(manual_row, textvariable=self._manual_ip_var,
                                bg=P["bg3"], fg=P["text"],
                                insertbackground=P["text"],
                                relief="flat", font=("Segoe UI", 9), width=16)
        manual_entry.pack(side="left", padx=(6, 4))
        manual_entry.insert(0, "192.168.x.x")
        manual_entry.bind("<FocusIn>",
            lambda e: manual_entry.delete(0, "end")
            if manual_entry.get() == "192.168.x.x" else None)
        add_manual_btn = tk.Label(manual_row, text=" Add ", bg=P["accent"],
                                   fg="#fff", font=("Segoe UI", 8, "bold"),
                                   padx=6, pady=3, cursor="hand2")
        add_manual_btn.pack(side="left")
        add_manual_btn.bind("<Button-1>",
            lambda e: self._add_manual_peer(self._manual_ip_var.get().strip()))

        tk.Frame(body, bg=P["border"], height=1).pack(fill="x", padx=12)

        # ── Transfers ─────────────────────────────────────────────────────
        self._section(body, "TRANSFERS")

        outer = tk.Frame(body, bg=P["bg"])
        outer.pack(fill="both", expand=True, padx=12)

        canvas = tk.Canvas(outer, bg=P["bg"], bd=0, highlightthickness=0)
        vsb    = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                              width=4)
        vsb.configure(bg=P["bg"], troughcolor=P["bg"])
        self._tx_inner = tk.Frame(canvas, bg=P["bg"])
        _tx_win_id     = canvas.create_window((0, 0), window=self._tx_inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._tx_inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(_tx_win_id, width=e.width))

        self._no_tx_lbl = tk.Label(self._tx_inner,
                                    text="No active transfers",
                                    bg=P["bg"], fg=P["mute"],
                                    font=("Segoe UI", 9))
        self._no_tx_lbl.pack(anchor="w", pady=10)

    def _section(self, parent, title):
        row = tk.Frame(parent, bg=P["bg"])
        row.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(row, text=title, bg=P["bg"], fg=P["accent"],
                 font=("Segoe UI", 7, "bold")).pack(side="left")
        tk.Frame(row, bg=P["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

    # ── Drag window ───────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - self.win.winfo_x()
        self._dy = e.y_root - self.win.winfo_y()

    def _drag_move(self, e):
        self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── Discovery — UDP broadcast ─────────────────────────────────────────────
    def _announce_loop(self):
        """Broadcast our presence every 4 s."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        msg = json.dumps({"dg": True, "name": DEVICE_NAME,
                          "port": SHARE_PORT}).encode()
        while self.alive:
            try:
                sock.sendto(msg, ("255.255.255.255", DISCOVER_PORT))
            except Exception:
                pass
            time.sleep(4)
        sock.close()

    def _discover_loop(self):
        """Listen for broadcasts from other instances."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(2)
        try:
            sock.bind(("0.0.0.0", DISCOVER_PORT))
        except Exception as e:
            # Port blocked or in use — show in UI and keep thread alive so
            # manually-added peers still work
            self.app.root.after(0, lambda: (
                self._status_dot.configure(fg=P["red"]),
                self._status_lbl.configure(
                    text=f"UDP port {DISCOVER_PORT} blocked — re-run install.bat as Admin")
            ))
            return
        while self.alive:
            try:
                data, addr = sock.recvfrom(512)
                pkt = json.loads(data.decode())
                if pkt.get("dg") and pkt.get("name") != DEVICE_NAME:
                    self._peers[pkt["name"]] = {
                        "ip":   addr[0],
                        "port": pkt.get("port", SHARE_PORT),
                        "ts":   time.time(),
                    }
            except Exception:
                pass
        sock.close()

    def _poll_peers(self):
        if not self.alive:
            return
        now = time.time()
        # Expire UDP peers not seen in 12 s
        self._peers = {n: p for n, p in self._peers.items()
                       if now - p["ts"] < 12}
        # Expire mobile IPs not seen in 15 s (missed ~3 poll cycles)
        MobileHandler._connected_ips = {
            ip: info for ip, info in MobileHandler._connected_ips.items()
            if now - info["ts"] < 15
        }
        self._refresh_peer_ui()
        self.app.root.after(3000, self._poll_peers)

    def _refresh_peer_ui(self):
        for w in self._peers_frame.winfo_children():
            w.destroy()

        # Merge in any browser/mobile devices connected via the sync server
        sync_port = self.app.data["settings"].get("sync_port", 7842)
        if self.app._sync_server:
            for ip, info in MobileHandler._connected_ips.items():
                name = info.get("name", f"Browser ({ip})")
                if name not in self._peers:
                    self._peers[name] = {"ip": ip, "port": sync_port,
                                        "mobile": True, "ts": time.time()}

        if not self._peers:
            tk.Label(self._peers_frame,
                     text="No devices found.\n"
                          "• Other PCs need DeskGoals Share panel open\n"
                          "• Browser/Phone: enable Sync Server and connect\n"
                          "• Add PC manually via IP if discovery is blocked",
                     bg=P["bg"], fg=P["mute"], font=("Segoe UI", 9),
                     wraplength=370, justify="left").pack(anchor="w", pady=6)
            self._status_dot.configure(fg=P["mute"])
            self._status_lbl.configure(text="Scanning…")
        else:
            n = len(self._peers)
            self._status_dot.configure(fg=P["green"])
            self._status_lbl.configure(
                text=f"{n} device{'s' if n > 1 else ''} found")
            for name, info in self._peers.items():
                self._peer_row(name, info)

    def _peer_row(self, name, info):
        row = tk.Frame(self._peers_frame, bg=P["bg2"])
        row.pack(fill="x", pady=2)

        tk.Label(row, text="●", bg=P["bg2"], fg=P["green"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(10, 4), pady=8)
        tk.Label(row, text=name, bg=P["bg2"], fg=P["text"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(row, text=info["ip"], bg=P["bg2"], fg=P["mute"],
                 font=("Segoe UI", 7)).pack(side="left", padx=(6, 0))

        send_btn = tk.Label(row, text="  Send File  ",
                            bg=P["accent"], fg="#fff",
                            font=("Segoe UI", 8, "bold"),
                            padx=6, pady=4, cursor="hand2")
        send_btn.pack(side="right", padx=10, pady=6)
        send_btn.bind("<Button-1>",
                      lambda e, n=name, ip=info["ip"], p=info["port"]:
                          self._pick_and_send(ip, p, n))

    # ── File pick & send ──────────────────────────────────────────────────────
    def _add_manual_peer(self, ip):
        if not ip or ip == "192.168.x.x":
            return
        # Probe the device to get its name
        def probe():
            try:
                conn = _http_client.HTTPConnection(ip, SHARE_PORT, timeout=4)
                conn.request("GET", "/ping")
                r    = conn.getresponse()
                data = json.loads(r.read())
                name = data.get("name", ip)
                conn.close()
            except Exception:
                name = ip
            self._peers[name] = {"ip": ip, "port": SHARE_PORT, "ts": time.time()}
            self.app.root.after(0, self._refresh_peer_ui)
        threading.Thread(target=probe, daemon=True).start()
        self._status_lbl.configure(text=f"Probing {ip}…")

    def _pick_and_send(self, ip, port, peer_name):
        path = _filedialog.askopenfilename(
            parent=self.win, title=f"Choose file to send to {peer_name}")
        if path:
            self._send_file(path, ip, port, peer_name)

    def _send_file(self, filepath, ip, port, peer_name):
        if not os.path.isfile(filepath):
            return
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        tid      = f"s_{time.time():.3f}"
        is_mobile = self._peers.get(peer_name, {}).get("mobile", False)

        row = _TransferRow(self._tx_inner, tid, filename,
                           filesize, peer_name, incoming=False)
        self._transfers[tid] = row
        self._no_tx_lbl.pack_forget()

        if is_mobile:
            def do_push():
                try:
                    MobileHandler.push_file(filepath)
                    self.app.root.after(0, lambda: (
                        row.update(filesize),
                        row.mark_done(True)
                    ))
                except Exception as ex:
                    log_error(f"mobile push failed: {ex}")
                    self.app.root.after(0, lambda: row.mark_done(False))
            threading.Thread(target=do_push, daemon=True).start()
            return

        def do_send():
            try:
                sent  = [0]
                chunk = 65536
                conn  = _http_client.HTTPConnection(ip, port, timeout=60)

                class _ProgressReader:
                    def __init__(self_, f):
                        self_._f = f
                    def read(self_, n=65536):
                        data = self_._f.read(n)
                        sent[0] += len(data)
                        self.app.root.after(
                            0, lambda b=sent[0]: row.update(b))
                        return data

                with open(filepath, "rb") as f:
                    conn.request("POST", "/receive",
                                 body=_ProgressReader(f),
                                 headers={
                                     "Content-Length": filesize,
                                     "Content-Type":
                                         "application/octet-stream",
                                     "X-Filename": filename,
                                     "X-Sender":   DEVICE_NAME,
                                 })
                    resp = conn.getresponse()
                    ok   = (resp.status == 200)
                    conn.close()

                self.app.root.after(0, lambda: row.mark_done(ok))
            except Exception as ex:
                log_error(f"send_file failed: {ex}")
                self.app.root.after(0, lambda: row.mark_done(False))

        threading.Thread(target=do_send, daemon=True).start()

    # ── Receive server ────────────────────────────────────────────────────────
    def _start_server(self):
        panel = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def do_GET(self):
                if self.path == "/ping":
                    body = json.dumps({"name": DEVICE_NAME}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type",   "application/json")
                    self.send_header("Content-Length", len(body))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path != "/receive":
                    self.send_response(404)
                    self.end_headers()
                    return

                filename   = self.headers.get("X-Filename", "received_file")
                sender     = self.headers.get("X-Sender",
                                              self.client_address[0])
                total      = int(self.headers.get("Content-Length", 0))
                tid        = f"r_{time.time():.3f}"
                safe_name  = os.path.basename(filename)

                # ── ASK USER BEFORE DOWNLOADING ──
                if not panel.app._ask_accept_file(safe_name, sender):
                    self.send_response(403)
                    self.end_headers()
                    return

                dest_dir   = os.path.join(os.path.expanduser("~"),
                                          "Downloads")
                os.makedirs(dest_dir, exist_ok=True)
                dest       = os.path.join(dest_dir, safe_name)

                # Avoid overwrite
                base, ext = os.path.splitext(safe_name)
                counter   = 1
                while os.path.exists(dest):
                    dest = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                    counter += 1

                # Create row on UI thread
                panel.app.root.after(0, lambda: panel._add_recv_row(
                    tid, safe_name, total, sender))

                received    = 0
                _last_ui_t  = 0.0   # Fix 5: throttle UI updates to ≤10/sec
                try:
                    with open(dest, "wb") as f:
                        while received < total:
                            n    = min(65536, total - received)
                            data = self.rfile.read(n)
                            if not data:
                                break
                            f.write(data)
                            received += len(data)
                            _now = time.time()
                            if _now - _last_ui_t >= 0.1:
                                _last_ui_t = _now
                                panel.app.root.after(
                                    0, lambda b=received: panel._update_recv(
                                        tid, b, total))
                    panel.app.root.after(
                        0, lambda: panel._finish_recv(tid, True, dest))
                    self.send_response(200)
                except Exception as ex:
                    log_error(f"receive failed: {ex}")
                    panel.app.root.after(
                        0, lambda: panel._finish_recv(tid, False, None))
                    self.send_response(500)
                self.end_headers()

        try:
            self._server = ServerClass(("0.0.0.0", SHARE_PORT), Handler)
            threading.Thread(target=self._server.serve_forever,
                             daemon=True).start()
            self._status_lbl.configure(text="Ready · " + get_local_ip())
            self._status_dot.configure(fg=P["accent"])
        except Exception as e:
            log_error(f"share server failed: {e}")
            self._status_lbl.configure(text=f"Port {SHARE_PORT} busy")
            self._status_dot.configure(fg=P["red"])

    def _add_recv_row(self, tid, filename, total, sender):
        self._no_tx_lbl.pack_forget()
        row = _TransferRow(self._tx_inner, tid, filename,
                           total, sender, incoming=True)
        self._transfers[tid] = row

    def _update_recv(self, tid, received, total):
        if tid in self._transfers:
            self._transfers[tid].update(received, total)

    def _finish_recv(self, tid, success, dest):
        if tid in self._transfers:
            self._transfers[tid].mark_done(success)
        if success and dest:
            # Notify via a brief status flash
            self._status_lbl.configure(
                text=f"Received: {os.path.basename(dest)}", fg=P["green"])
            self.app.root.after(4000, lambda: self._status_lbl.configure(
                text="Ready · " + get_local_ip(), fg=P["mute"]))

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def _cleanup(self):
        self.alive = False
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass

    def _close(self):
        self._cleanup()
        try:
            self.win.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        DeskGoals().run()
    except Exception:
        log_error(traceback.format_exc())
        raise
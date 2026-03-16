#!/usr/bin/env python3
"""Aside — Updated"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import json, os, threading, time, sys, traceback, socket, shutil, uuid, queue, copy, re, webbrowser
from http.server import BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer as ServerClass
except ImportError:
    from http.server import HTTPServer as ServerClass

LOG_FILE = os.path.join(os.path.expanduser("~"), "aside_error.log")
def log_error(msg):
    try:
        with open(LOG_FILE, "a") as f: f.write(f"\n{'='*60}\n{msg}\n")
    except Exception: pass
sys.excepthook = lambda t, v, tb: log_error("".join(traceback.format_exception(t, v, tb)))

try:
    import pystray
    from PIL import Image, ImageDraw, ImageTk, ImageGrab
    HAS_TRAY = True
except ImportError: HAS_TRAY = False; log_error("pystray/Pillow not installed")

try:
    import win32gui, win32process, psutil
    HAS_WIN32 = True
except ImportError: HAS_WIN32 = False

try:
    import keyboard; HAS_HOTKEY = True
except ImportError: HAS_HOTKEY = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD; HAS_DND = True
except ImportError: HAS_DND = False

DATA_FILE = os.path.join(os.path.expanduser("~"), ".aside.json")
MEDIA_DIR = os.path.join(os.path.expanduser("~"), ".aside_media")
os.makedirs(MEDIA_DIR, exist_ok=True)
FONT = "Segoe UI"
SIZE_PRESETS = [(225, 420), (300, 560), (375, 700), (450, 840)]
SIZE_LABELS  = ["75%", "100%", "125%", "150%"]
SHARE_PORT = 7843; DISCOVER_PORT = 7844; DEVICE_NAME = socket.gethostname()

# ── Robust URL detection ─────────────────────────────────────────────────────
_TLDS = (r'co\.uk|co\.jp|co\.kr|co\.in|co\.nz|co\.za|org\.uk|'
         r'com|org|net|io|dev|edu|gov|mil|int|'
         r'co|me|tv|gg|app|xyz|info|biz|pro|site|online|store|tech|'
         r'us|uk|ca|de|fr|jp|au|in|br|ru|it|es|nl|se|no|fi|dk|pl|cz|'
         r'ch|at|be|ie|pt|nz|za|mx|ar|cl|kr|cn|sg|hk|tw|my|th|id|vn|ae|il')
URL_RE = re.compile(
    r'https?://[^\s<>]+'
    r'|www\.[^\s<>]+'
    r'|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+(?:' + _TLDS + r')(?:/[^\s<>]*)?',
    re.IGNORECASE
)

def _clean_url(u):
    """Strip trailing punctuation unlikely to be part of a URL."""
    while u and u[-1] in '.,;:!?)\'"»›':
        u = u[:-1]
    return u

def _normalize_url(u):
    """Clean and ensure URL has a protocol for opening."""
    u = _clean_url(u)
    if not re.match(r'https?://', u, re.IGNORECASE):
        return 'https://' + u
    return u

THEMES = {
    "Dark": {"bg":"#0d0d0d","bg_header":"#141414","bg_row":"#111111","bg_row2":"#141414","bg_input":"#171717","bg_comp":"#111a11",
        "border":"#222222","text":"#d0d0d0","text_mute":"#555555","text_hint":"#2e2e2e","text_done":"#363636","check_on":"#5ddd5d",
        "check_off":"#333333","tab_act":"#ffffff","tab_idle":"#404040","del_idle":"#252525","del_hov":"#888888","sel_bg":"#1a2a3a",
        "link":"#5b9cf0"},
    "Slate": {"bg":"#1a1e24","bg_header":"#1e2330","bg_row":"#1c2028","bg_row2":"#1e2330","bg_input":"#20252e","bg_comp":"#161d1e",
        "border":"#2a3040","text":"#c8d0dc","text_mute":"#4a5570","text_hint":"#2a3040","text_done":"#384050","check_on":"#4ecfcf",
        "check_off":"#2a3550","tab_act":"#8ab4ff","tab_idle":"#3a4560","del_idle":"#232d3a","del_hov":"#7090b0","sel_bg":"#1e3040",
        "link":"#6db8f0"},
    "Warm": {"bg":"#141210","bg_header":"#1a1714","bg_row":"#171412","bg_row2":"#1a1714","bg_input":"#1d1a17","bg_comp":"#141a12",
        "border":"#2a2520","text":"#d4c8b8","text_mute":"#554e44","text_hint":"#302820","text_done":"#3a3028","check_on":"#d4a84b",
        "check_off":"#3a3028","tab_act":"#e8c87a","tab_idle":"#4a4030","del_idle":"#252018","del_hov":"#a08060","sel_bg":"#2a2418",
        "link":"#d4a84b"},
    "Light": {"bg":"#f4f4f4","bg_header":"#ebebeb","bg_row":"#f8f8f8","bg_row2":"#f0f0f0","bg_input":"#eeeeee","bg_comp":"#e8f0e8",
        "border":"#d8d8d8","text":"#1a1a1a","text_mute":"#888888","text_hint":"#bbbbbb","text_done":"#aaaaaa","check_on":"#2a9a2a",
        "check_off":"#bbbbbb","tab_act":"#111111","tab_idle":"#888888","del_idle":"#d0d0d0","del_hov":"#555555","sel_bg":"#cce0ff",
        "link":"#1a6dd4"},
}
S = {"bg":"#1c1c1c","bg2":"#242424","bg3":"#2c2c2c","border":"#333333","text":"#e0e0e0","mute":"#888888",
     "accent":"#5b9cf0","danger":"#e05555","input_bg":"#2a2a2a","input_fg":"#e0e0e0"}
HINTS = {"goal":"Add a goal...","header_sm":"Small header...","header_lg":"BIG HEADER..."}

def default_data():
    return {"position":None,"active_tab":"main","workspaces":{"main":{"name":"Today","goals":[]}},
            "app_rules":{},"completed":[],"settings":{"theme":"Dark","alpha":0.93,"hotkey":"ctrl+alt+g",
            "always_on_top":True,"auto_show":True,"sync_enabled":False,"sync_port":7842}}

def load_data():
    try:
        with open(DATA_FILE) as f:
            d=json.load(f); base=default_data()
            if "settings" in d: base["settings"].update(d.pop("settings"))
            base.update(d)
            if "main" not in base["workspaces"]: base["workspaces"]["main"]={"name":"Today","goals":[]}
            return base
    except Exception: return default_data()

def save_data(data):
    try:
        with open(DATA_FILE,"w") as f: json.dump(data,f,indent=2)
    except Exception as e: log_error(f"save_data failed: {e}")

_LOCAL_IP = None
def get_local_ip():
    global _LOCAL_IP
    if _LOCAL_IP is None:
        try: s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); _LOCAL_IP=s.getsockname()[0]; s.close()
        except Exception: _LOCAL_IP="127.0.0.1"
    return _LOCAL_IP

class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=4)
        self.vsb.configure(bg=bg, troughcolor=bg)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True); self.vsb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_scroll); self.canvas.bind("<Configure>", self._update_width)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_scroll))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.inner.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_scroll))
    def _update_scroll(self, e=None): self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    def _update_width(self, e): self.canvas.itemconfig(self._win, width=e.width)
    def _on_scroll(self, e): self.canvas.yview_scroll(int(-1*(e.delta/120)),"units")
    def reset_inner(self, bg):
        """Destroy and recreate inner frame for a clean render pass."""
        self.canvas.delete(self._win)
        self.inner.destroy()
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        # Fix: Force newly created window to immediately match canvas width
        self.canvas.itemconfig(self._win, width=self.canvas.winfo_width())
        self.inner.bind("<Configure>", self._update_scroll)
        self.inner.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_scroll))

class Tooltip:
    def __init__(self, widget, text):
        self._tip = None
        widget.bind("<Enter>", lambda e: self._show(widget, text), add="+")
        widget.bind("<Leave>", lambda e: self._hide(), add="+")
    def _show(self, widget, text):
        self._hide(); x=widget.winfo_rootx()+widget.winfo_width()//2; y=widget.winfo_rooty()+widget.winfo_height()+4
        self._tip=tw=tk.Toplevel(widget); tw.wm_overrideredirect(True); tw.wm_geometry(f"+{x}+{y}"); tw.attributes("-topmost",True)
        tk.Label(tw,text=text,bg="#1e2230",fg="#c8d4e8",font=(FONT,8),padx=8,pady=4,relief="flat",bd=0).pack()
    def _hide(self):
        if self._tip:
            try: self._tip.destroy()
            except Exception: pass
            self._tip = None

# ── Mobile HTML ───────────────────────────────────────────────────────────────
MOBILE_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aside</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#0d0d0d;color:#d0d0d0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:800px;margin:0 auto;min-height:100vh;padding:0 10px}
header{padding:14px 16px;background:#141414;display:flex;align-items:center;gap:10px;box-shadow:0 1px 10px rgba(0,0,0,0.5)}header h1{font-size:15px;color:#fff;letter-spacing:1px;flex:1}#sync-dot{font-size:11px;color:#5ddd5d}
.tabs{display:flex;background:#141414;overflow-x:auto;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tab{padding:10px 16px;font-size:12px;cursor:pointer;white-space:nowrap;color:#555;border-bottom:2px solid transparent;flex-shrink:0}.tab.active{color:#fff;border-bottom-color:#fff}
.ws-label{padding:4px 16px;font-size:10px;color:#444;letter-spacing:2px;background:#0a0a0a}.goals{padding:4px 0 140px}.goal-row{display:flex;align-items:flex-start;padding:11px 16px;border-bottom:1px solid #181818;gap:12px}.goal-row.alt{background:#141414}
.header-sm,.header-lg{background:#141414;padding:9px 16px;border-bottom:1px solid #1e1e1e}.header-sm .htxt{font-size:12px;font-weight:700;color:#fff}.header-lg .htxt{font-size:18px;font-weight:700;color:#fff}
.circle{width:22px;height:22px;border-radius:50%;border:2px solid #333;cursor:pointer;flex-shrink:0;margin-top:2px}.circle:active{background:#5ddd5d;border-color:#5ddd5d}.goal-text{flex:1;font-size:14px;line-height:1.45}
.goal-text.link{color:#5b9cf0;text-decoration:underline;cursor:pointer}
.empty{text-align:center;padding:50px 20px;color:#333;font-size:16px;line-height:2}.bottom-bar{position:fixed;bottom:0;left:0;right:0;max-width:800px;margin:0 auto;background:#111318;box-shadow:0 -2px 10px rgba(0,0,0,0.5)}
.add-bar{display:flex;padding:10px 12px 4px;gap:8px}.add-bar input{flex:1;background:#111;border:1px solid #222;color:#d0d0d0;font-size:15px;padding:10px 14px;border-radius:10px;outline:none}.add-bar input:focus{border-color:#444}
.add-bar button{background:#5ddd5d;color:#000;border:none;width:42px;height:42px;border-radius:10px;font-size:22px;font-weight:700;cursor:pointer}
.send-bar{display:flex;padding:4px 12px 10px;gap:8px}.send-bar label{flex:1;background:#111;border:1px solid #2a2f3a;color:#6b7280;font-size:13px;padding:9px 14px;border-radius:10px;cursor:pointer;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.send-bar label.ready{color:#d0d0d0;border-color:#4f8ef7;background:#1a1d24}.send-bar input[type=file]{display:none}.send-bar button{background:#4f8ef7;color:#fff;border:none;padding:0 18px;height:40px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer}
.send-bar button:disabled{background:#222;color:#555}.send-section-title{font-size:9px;letter-spacing:1.5px;color:#4f8ef7;font-weight:700;padding:8px 12px 2px}#upload-progress{height:3px;background:#1e2230;margin:0 12px 6px;border-radius:2px;overflow:hidden;display:none}
#upload-bar{height:100%;background:#4f8ef7;width:0;transition:width .2s}#upload-status{text-align:center;font-size:12px;padding:0 12px 6px;display:none}
.files-section{padding:6px 12px 10px;border-top:1px solid #1e1e1e}.files-section h3{font-size:9px;letter-spacing:1.5px;color:#4f8ef7;margin-bottom:6px;font-weight:700}
.file-row{display:flex;align-items:center;background:#1a1d24;border-radius:8px;padding:8px 12px;margin-bottom:4px;gap:10px}.file-row span{flex:1;font-size:12px;color:#d0d0d0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-row a{background:#3ecf6e;color:#000;text-decoration:none;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px}</style></head>
<body><header><h1>&#11041; ASIDE</h1><span id="sync-dot">&#9679;</span></header><div class="tabs" id="tabs"></div><div class="ws-label" id="ws-label"></div><div class="goals" id="goals"></div>
<div class="bottom-bar"><div class="add-bar"><input id="inp" placeholder="Add a goal..." autocomplete="off"><button onclick="addGoal()">+</button></div>
<div style="border-top:1px solid #1e1e1e"><div class="send-section-title">&#8679; SEND FILE TO HOST</div><div class="send-bar"><label id="file-label" for="file-pick">Tap to choose a file</label>
<input type="file" id="file-pick" onchange="fileChosen(this)"><button id="send-btn" disabled onclick="uploadFile()">Send</button></div><div id="upload-progress"><div id="upload-bar"></div></div><div id="upload-status"></div></div>
<div class="files-section" id="files-section" style="display:none"><h3>&#8595; FILES FROM HOST</h3><div id="files-list"></div></div></div>
<script>let state={workspaces:{},active_tab:"main"},activeTab="main",chosenFile=null;
const TLDS='co\\.uk|co\\.jp|co\\.kr|co\\.in|co\\.nz|co\\.za|org\\.uk|com|org|net|io|dev|edu|gov|mil|int|co|me|tv|gg|app|xyz|info|biz|pro|site|online|store|tech|us|uk|ca|de|fr|jp|au|in|br|ru|it|es|nl|se|no|fi|dk|pl|cz|ch|at|be|ie|pt|nz|za|mx|ar|cl|kr|cn|sg|hk|tw|my|th|id|vn|ae|il';
const urlRe=new RegExp('https?://[^\\s<>]+|www\\.[^\\s<>]+|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\\.)+(?:'+TLDS+')(?:/[^\\s<>]*)?','gi');
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}
function cleanUrl(u){while(u.length&&'.,;:!?)]\'"'.includes(u[u.length-1]))u=u.slice(0,-1);return u}
function normUrl(u){u=cleanUrl(u);if(!/^https?:\/\//i.test(u))u='https://'+u;return u}
function linkify(s){return esc(s).replace(urlRe,function(m){var c=cleanUrl(m),h=normUrl(c),trail=m.slice(c.length);return'<a href="'+h+'" target="_blank" rel="noopener" style="color:#5b9cf0;text-decoration:underline">'+esc(c)+'</a>'+esc(trail)})}
async function load(){try{const r=await fetch("/api/state");if(!r.ok)throw 0;state=await r.json();if(!state.workspaces[activeTab])activeTab=state.active_tab||Object.keys(state.workspaces)[0];render();document.getElementById("sync-dot").style.color="#5ddd5d";}catch(e){document.getElementById("sync-dot").style.color="#555";}}
function render(){const t=document.getElementById("tabs");t.innerHTML=Object.entries(state.workspaces).map(([k,ws])=>`<div class="tab${k===activeTab?" active":""}" onclick="switchTab('${k}')">${esc(ws.name)}</div>`).join("");
const ws=state.workspaces[activeTab]||{name:"",goals:[]};document.getElementById("ws-label").textContent=ws.name.toUpperCase();const goals=ws.goals||[],rows=[];let alt=0;
goals.forEach((g,ri)=>{if(g.done)return;if(g.type==="header"){rows.push(`<div class="header-${g.size||'sm'}"><span class="htxt">${esc(g.text)}</span></div>`);return;}
if(g.type==="media"){let ic=g.media_type==="image"?"🖼️":g.media_type==="audio"?"🎵":g.media_type==="video"?"🎬":"📁";rows.push(`<div class="goal-row${alt++%2?" alt":""}"><div class="circle" onclick="complete(${ri})"></div><span class="goal-text" style="color:#4f8ef7">${ic} ${esc(g.filename)}</span></div>`);return;}
const hasUrl=urlRe.test(g.text);urlRe.lastIndex=0;rows.push(`<div class="goal-row${alt++%2?" alt":""}"><div class="circle" onclick="complete(${ri})"></div><span class="goal-text${hasUrl?" link":""}">${linkify(g.text)}</span></div>`);});
document.getElementById("goals").innerHTML=rows.length?rows.join(""):`<div class="empty">Nothing here.<br>Add a goal below.</div>`;}
function switchTab(k){activeTab=k;render();}
async function complete(ri){await fetch("/api/complete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({workspace:activeTab,index:ri})});load();}
async function addGoal(){const inp=document.getElementById("inp"),text=inp.value.trim();if(!text)return;await fetch("/api/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({workspace:activeTab,text})});inp.value="";load();}
function fileChosen(i){chosenFile=i.files[0]||null;const l=document.getElementById("file-label"),b=document.getElementById("send-btn");if(chosenFile){l.textContent=chosenFile.name;l.classList.add("ready");b.disabled=false;}else{l.textContent="Tap to choose a file";l.classList.remove("ready");b.disabled=true;}}
async function uploadFile(){if(!chosenFile)return;const b=document.getElementById("send-btn"),p=document.getElementById("upload-progress"),bar=document.getElementById("upload-bar"),st=document.getElementById("upload-status"),fn=chosenFile.name;
b.disabled=true;p.style.display="block";st.style.display="block";st.style.color="#4f8ef7";st.textContent="Waiting...";bar.style.width="0";const xhr=new XMLHttpRequest();xhr.open("POST","/api/upload");xhr.setRequestHeader("X-Filename",encodeURIComponent(fn));
xhr.upload.onprogress=e=>{if(e.lengthComputable)bar.style.width=(e.loaded/e.total*100)+"%";};
xhr.onload=()=>{const ok=xhr.status===200;bar.style.width="100%";bar.style.background=ok?"#3ecf6e":"#e05555";st.style.color=ok?"#3ecf6e":"#e05555";st.textContent=ok?`✓ ${fn}`:"✗ Failed";
setTimeout(()=>{p.style.display="none";st.style.display="none";bar.style.width="0";bar.style.background="#4f8ef7";},4000);chosenFile=null;document.getElementById("file-pick").value="";
document.getElementById("file-label").textContent="Tap to choose a file";document.getElementById("file-label").classList.remove("ready");b.disabled=true;};xhr.onerror=()=>{st.textContent="✗ Lost";b.disabled=false;};xhr.send(chosenFile);}
document.getElementById("inp").addEventListener("keydown",e=>{if(e.key==="Enter")addGoal();});
async function pollFiles(){try{const r=await fetch("/api/files");if(!r.ok)return;const d=await r.json(),s=document.getElementById("files-section"),l=document.getElementById("files-list");
if(!d.files||!d.files.length){s.style.display="none";return;}s.style.display="block";l.innerHTML=d.files.map(f=>`<div class="file-row"><span>${esc(f)}</span><a href="/api/download/${encodeURIComponent(f)}" download="${esc(f)}">Save</a></div>`).join("");}catch(e){}}
load();pollFiles();setInterval(load,4000);setInterval(pollFiles,3000);</script></body></html>"""

class MobileHandler(BaseHTTPRequestHandler):
    app=None;_pending={};_connected_ips={}
    @classmethod
    def push_file(cls,fp):
        now=time.time();cls._pending={k:v for k,v in cls._pending.items() if now-v.get("ts",now)<600}
        fn=os.path.basename(fp);key=fn;c=1
        while key in cls._pending:b,e=os.path.splitext(fn);key=f"{b}_{c}{e}";c+=1
        cls._pending[key]={"path":fp,"ts":now};return key
    def log_message(self,*a):pass
    def do_GET(self):
        ip=self.client_address[0]
        if ip not in MobileHandler._connected_ips:
            try:n=socket.gethostbyaddr(ip)[0];n=n.split('.')[0] if n.endswith(('.local','.lan')) else n
            except Exception:n=f"Browser ({ip})"
            MobileHandler._connected_ips[ip]={"ts":time.time(),"name":n}
        else:MobileHandler._connected_ips[ip]["ts"]=time.time()
        if self.path=="/api/state":self._json(200,{"active_tab":self.app.data.get("active_tab"),"workspaces":self.app.data.get("workspaces",{})})
        elif self.path=="/api/files":
            now=time.time();MobileHandler._pending={k:v for k,v in MobileHandler._pending.items() if now-v.get("ts",now)<600}
            self._json(200,{"files":list(MobileHandler._pending.keys())})
        elif self.path.startswith("/api/download/"):
            import urllib.parse as _up;key=_up.unquote(self.path[len("/api/download/"):]);entry=MobileHandler._pending.get(key)
            fp=entry["path"] if isinstance(entry,dict) else entry
            if not fp or not os.path.isfile(fp):self.send_response(404);self.end_headers();return
            sz=os.path.getsize(fp);self.send_response(200);self.send_header("Content-Type","application/octet-stream")
            self.send_header("Content-Disposition",f'attachment; filename="{key}"');self.send_header("Content-Length",sz);self.end_headers()
            with open(fp,"rb") as f:
                while True:
                    ch=f.read(65536)
                    if not ch:break
                    self.wfile.write(ch)
            MobileHandler._pending.pop(key,None)
        elif self.path=="/":
            body=MOBILE_HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",len(body));self.end_headers();self.wfile.write(body)
        else:self._json(404,{"error":"not found"})
    def do_POST(self):
        if self.path=="/api/upload":self.do_POST_upload();return
        length=int(self.headers.get("Content-Length",0))
        try:body=json.loads(self.rfile.read(length) or b"{}")
        except Exception:body={}
        if self.path=="/api/add":
            wk=body.get("workspace",self.app.data.get("active_tab"));txt=(body.get("text") or "").strip()
            if txt and wk in self.app.data.get("workspaces",{}):
                def do():self.app.data["workspaces"][wk]["goals"].append({"text":txt,"done":False});save_data(self.app.data);self.app._render_all()
                self.app.root.after(0,do)
            self._json(200,{"ok":True})
        elif self.path=="/api/complete":
            wk=body.get("workspace");idx=body.get("index")
            if wk is not None and idx is not None:
                def do():
                    goals=self.app.data.get("workspaces",{}).get(wk,{}).get("goals",[])
                    if 0<=idx<len(goals) and not goals[idx].get("done"):
                        uid=self.app._ensure_uid(goals[idx]);self.app._complete_goal_in_ws(uid,wk)
                self.app.root.after(0,do)
            self._json(200,{"ok":True})
        else:self._json(404,{"error":"not found"})
    def do_POST_upload(self):
        import urllib.parse as _up
        try:fn=_up.unquote(self.headers.get("X-Filename","upload"))
        except Exception:fn=self.headers.get("X-Filename","upload")
        total=int(self.headers.get("Content-Length",0));sn=os.path.basename(fn) or "upload"
        sip=self.client_address[0];sender=MobileHandler._connected_ips.get(sip,{}).get("name",sip)
        if not self.app._ask_accept_file(sn,sender):self._json(403,{"error":"Declined"});return
        dd=os.path.join(os.path.expanduser("~"),"Downloads");os.makedirs(dd,exist_ok=True)
        dest=os.path.join(dd,sn);b,e=os.path.splitext(sn);c=1
        while os.path.exists(dest):dest=os.path.join(dd,f"{b}_{c}{e}");c+=1
        tid=f"m_{time.time():.3f}";panel=(self.app._share_win if self.app._share_win and self.app._share_win.alive else None)
        if panel:self.app.root.after(0,lambda:panel._add_recv_row(tid,sn,total,f"📱 {sender}"))
        try:
            rcv=0;_lt=0.0
            with open(dest,"wb") as f:
                while rcv<total:
                    ch=self.rfile.read(min(65536,total-rcv))
                    if not ch:break
                    f.write(ch);rcv+=len(ch)
                    if panel:
                        _n=time.time()
                        if _n-_lt>=0.1:_lt=_n;b2=rcv;self.app.root.after(0,lambda b2=b2:panel._update_recv(tid,b2,total))
            if panel:self.app.root.after(0,lambda:panel._finish_recv(tid,True,dest))
            else:self.app.root.after(0,lambda:self.app._flash_share_btn(sn))
            self._json(200,{"ok":True})
        except Exception as ex:
            log_error(f"upload fail: {ex}")
            if panel:self.app.root.after(0,lambda:panel._finish_recv(tid,False,None))
            self._json(500,{"error":str(ex)})
    def _json(self,code,obj):
        body=json.dumps(obj).encode();self.send_response(code);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",len(body));self.end_headers();self.wfile.write(body)


class Aside:
    def __init__(self):
        self.data = load_data()
        self.visible = True; self._drag_x = 0; self._drag_y = 0; self._hotkey_id = None
        self.settings_win = None; self.comp_open = False; self._hint_active = True; self._input_mode = "goal"
        self._sync_server = None; self._settings_rebuild_ws = None; self._settings_rebuild_rules = None
        self._prev_focused_proc = None; self._user_hidden = False; self._app_switch_queue = queue.Queue()
        self._share_win = None; self._size_idx = self.data["settings"].get("size_idx", 1)
        self._image_cache = {}; self._row_widget_map = {}; self._render_order = []
        self._selected_uids = set(); self._clipboard_goals = []
        self._drag_active = False; self._drag_uid = None; self._drag_ghost = None; self._drop_line = None
        self._drag_pending_uid = None; self._drag_press_x = 0; self._drag_press_y = 0

        if HAS_DND: self.root = TkinterDnD.Tk()
        else: self.root = tk.Tk()
        self.root.title("Aside"); self.root.overrideredirect(True); self.root.wm_attributes("-toolwindow",False)
        self.root.attributes("-topmost",self.data["settings"].get("always_on_top",True))
        self.root.attributes("-alpha",self.data["settings"].get("alpha",0.93))
        if HAS_DND: self.root.drop_target_register(DND_FILES); self.root.dnd_bind('<<Drop>>',self._on_drop)
        self.root.bind('<Control-v>',self._on_paste)
        self._restore_position(); self._build_ui()
        self.root.withdraw(); self.visible = False
        try: self._setup_tray()
        except Exception as e: log_error(f"tray fail: {e}")
        self._register_hotkey(); self._cleanup_old_completed()
        if self.data["settings"].get("sync_enabled",False): self._start_sync_server()
        if HAS_WIN32:
            threading.Thread(target=self._app_watch_loop,daemon=True).start()
            self.root.after(200,self._poll_app_switch_queue)
            self.root.after(600,self._initial_app_check)
        self.root.protocol("WM_DELETE_WINDOW",self._toggle_visibility)

    @property
    def T(self): return THEMES.get(self.data["settings"].get("theme","Dark"),THEMES["Dark"])

    def _ensure_uid(self,g):
        if '_uid' not in g: g['_uid']=uuid.uuid4().hex[:12]
        return g['_uid']
    def _find_goal_by_uid(self,uid,wk=None):
        if wk is None:wk=self.data["active_tab"]
        for g in self.data["workspaces"].get(wk,{}).get("goals",[]):
            if g.get('_uid')==uid: return g
        return None
    def _find_goal_index_by_uid(self,uid,wk=None):
        if wk is None:wk=self.data["active_tab"]
        for i,g in enumerate(self.data["workspaces"].get(wk,{}).get("goals",[])):
            if g.get('_uid')==uid: return i
        return -1

    def _ask_accept_file(self,filename,sender):
        result=[False];evt=threading.Event();dlg_ref=[]
        def _show():
            dlg=tk.Toplevel(self.root);dlg_ref.append(dlg);dlg.title("Incoming File");dlg.geometry("320x130")
            dlg.configure(bg=S["bg"]);dlg.attributes("-topmost",True);dlg.resizable(False,False);dlg.update_idletasks()
            dlg.geometry(f"+{(dlg.winfo_screenwidth()//2)-(160)}+{(dlg.winfo_screenheight()//2)-(65)}")
            tk.Label(dlg,text=f"Accept file from {sender}?",bg=S["bg"],fg=S["mute"],font=(FONT,9)).pack(pady=(15,5))
            tk.Label(dlg,text=filename,bg=S["bg"],fg=S["text"],font=(FONT,10,"bold"),wraplength=280).pack(pady=(0,15))
            bf=tk.Frame(dlg,bg=S["bg"]);bf.pack(fill="x",pady=(0,8))
            def yes():result[0]=True;evt.set();dlg.destroy()
            def no():result[0]=False;evt.set();dlg.destroy()
            tk.Button(bf,text="Accept",command=yes,bg=S["accent"],fg="white",relief="flat",font=(FONT,9,"bold"),width=12).pack(side="left",padx=(30,10))
            tk.Button(bf,text="Decline",command=no,bg=S["bg3"],fg=S["text"],relief="flat",font=(FONT,9),width=12).pack(side="right",padx=(10,30))
            dlg.protocol("WM_DELETE_WINDOW",no);dlg.grab_set();dlg.focus_force()
        self.root.after(0,_show);evt.wait(timeout=120)
        if not evt.is_set():
            self.root.after(0,lambda:[dlg_ref[0].destroy() for _ in [1] if dlg_ref and dlg_ref[0].winfo_exists()])
            return False
        return result[0]

    # ── Media ─────────────────────────────────────────────────────────────────
    def _browse_and_add_file(self,event=None):
        from tkinter import filedialog
        fps=filedialog.askopenfilenames(parent=self.root,title="Attach files")
        if fps:
            for fp in fps: self._process_dropped_file(fp)
            self._render_all();self.root.after(50,lambda:self.scroll.canvas.yview_moveto(1.0))
    def _on_paste(self,event=None):
        if self._entry_focused():return
        if self._clipboard_goals:self._paste_goals();return "break"
        try:
            img=ImageGrab.grabclipboard()
            if img:
                fn=f"clipboard_{uuid.uuid4().hex[:8]}.png";fp=os.path.join(MEDIA_DIR,fn)
                if isinstance(img,list):
                    for f in img:self._process_dropped_file(f)
                else:img.save(fp,"PNG");self._add_media_goal("image",fn,dest_path=fp)
        except Exception as e:log_error(f"Paste: {e}")
        return "break"
    def _on_copy(self,event=None):
        if self._entry_focused():return
        if self._selected_uids:self._copy_selected();return "break"
    def _on_drop(self,event):
        for fp in self.root.tk.splitlist(event.data):self._process_dropped_file(fp)
        self._render_all();self.root.after(50,lambda:self.scroll.canvas.yview_moveto(1.0))
    def _process_dropped_file(self,fp):
        if not os.path.isfile(fp):return
        fn=os.path.basename(fp);b,ext=os.path.splitext(fn);dp=os.path.join(MEDIA_DIR,fn);c=1
        while os.path.exists(dp):dp=os.path.join(MEDIA_DIR,f"{b}_{c}{ext}");fn=f"{b}_{c}{ext}";c+=1
        shutil.copy(fp,dp);el=ext.lower()
        if el in ['.png','.jpg','.jpeg','.gif','.bmp','.webp']:mt="image"
        elif el in ['.mp3','.wav','.ogg','.flac']:mt="audio"
        elif el in ['.mp4','.mkv','.avi','.mov']:mt="video"
        elif el=='.pdf':mt="pdf"
        else:mt="file"
        self._add_media_goal(mt,fn,dest_path=dp)
    def _add_media_goal(self,mt,fn,dest_path=None):
        desc=simpledialog.askstring("Attachment Note","Description (blank for none):",parent=self.root)
        if desc is None:
            if dest_path and os.path.exists(dest_path):
                try:os.remove(dest_path)
                except Exception:pass
            return
        item={"type":"media","media_type":mt,"filename":fn,"text":desc.strip() if desc else "","done":False}
        self._ensure_uid(item);self._current_goals().append(item);save_data(self.data)
        self._render_all();self.root.after(50,lambda:self.scroll.canvas.yview_moveto(1.0))
    def _show_image_popup(self,fp):
        if not os.path.exists(fp):return
        top=tk.Toplevel(self.root);top.configure(bg="#000");top.attributes("-topmost",True);top.overrideredirect(True)
        try:
            img=Image.open(fp);img.thumbnail((int(self.root.winfo_screenwidth()*0.8),int(self.root.winfo_screenheight()*0.8)))
            photo=ImageTk.PhotoImage(img);lbl=tk.Label(top,image=photo,bg="#000",cursor="hand2");lbl.image=photo;lbl.pack(padx=2,pady=2)
            lbl.bind("<Button-1>",lambda e:top.destroy());top.bind("<Escape>",lambda e:top.destroy());top.update_idletasks()
            top.geometry(f"+{(self.root.winfo_screenwidth()//2)-(top.winfo_width()//2)}+{(self.root.winfo_screenheight()//2)-(top.winfo_height()//2)}")
        except Exception:top.destroy()

    def _current_wh(self): return SIZE_PRESETS[max(0,min(self._size_idx,len(SIZE_PRESETS)-1))]
    def _restore_position(self):
        pos=self.data.get("position");cw,ch=self._current_wh()
        if pos:x,y=pos
        else:x=self.root.winfo_screenwidth()-cw-28;y=(self.root.winfo_screenheight()-ch)//2
        self.root.geometry(f"{cw}x{ch}+{x}+{y}")
    def _save_position(self):self.data["position"]=[self.root.winfo_x(),self.root.winfo_y()];save_data(self.data)

    def _prune_image_cache(self):
        stale = []
        for key in self._image_cache:
            base_fn = key[:-4] if key.endswith("_pdf") else key
            if not os.path.exists(os.path.join(MEDIA_DIR, base_fn)):
                stale.append(key)
        for k in stale:
            del self._image_cache[k]

    def _get_cached_image(self, key, loader_fn):
        if key not in self._image_cache:
            photo = loader_fn()
            if photo is None:
                return None
            self._image_cache[key] = photo
        return self._image_cache[key]

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        t=self.T
        self.header=tk.Frame(self.root,bg=t["bg_header"],height=42,cursor="fleur");self.header.pack(fill="x");self.header.pack_propagate(False)
        self.header.bind("<ButtonPress-1>",self._wdrag_start);self.header.bind("<B1-Motion>",self._wdrag_move);self.header.bind("<ButtonRelease-1>",lambda e:self._save_position())
        self.ws_label=tk.Label(self.header,text="",bg=t["bg_header"],fg=t["text_mute"],font=(FONT,8,"bold"));self.ws_label.pack(side="left",padx=14)
        self.app_badge=tk.Label(self.header,text="",bg=t["bg_header"],fg=t["check_on"],font=(FONT,7));self.app_badge.pack(side="left",padx=2)
        cog=tk.Label(self.header,text="⚙",bg=t["bg_header"],fg=t["tab_act"],font=(FONT,13),cursor="hand2");cog.pack(side="right",padx=(4,8))
        cog.bind("<Button-1>",lambda e:self._open_settings());cog.bind("<Enter>",lambda e:cog.configure(fg=t["check_on"]));cog.bind("<Leave>",lambda e:cog.configure(fg=t["tab_act"]))
        Tooltip(cog,"Settings  (Ctrl+,)")
        hide=tk.Label(self.header,text="–",bg=t["bg_header"],fg=t["tab_act"],font=(FONT,13),cursor="hand2");hide.pack(side="right",padx=2)
        hide.bind("<Button-1>",lambda e:self._toggle_visibility());hide.bind("<Enter>",lambda e:hide.configure(fg=t["check_on"]));hide.bind("<Leave>",lambda e:hide.configure(fg=t["tab_act"]))
        Tooltip(hide,"Minimise to tray")
        self._share_btn_ref=tk.Label(self.header,text="⇄",bg=t["bg_header"],fg=t["tab_act"],font=(FONT,13),cursor="hand2");self._share_btn_ref.pack(side="right",padx=2)
        self._share_btn_ref.bind("<Button-1>",lambda e:self._open_fileshare());self._share_btn_ref.bind("<Enter>",lambda e:self._share_btn_ref.configure(fg=t["check_on"]))
        self._share_btn_ref.bind("<Leave>",lambda e:self._share_btn_ref.configure(fg=t["tab_act"]));Tooltip(self._share_btn_ref,"File Share")
        self.size_btn=tk.Label(self.header,text=SIZE_LABELS[self._size_idx],bg=t["bg_header"],fg=t["text_mute"],font=(FONT,7),cursor="hand2")
        self.size_btn.pack(side="right",padx=(4,0));self.size_btn.bind("<Button-1>",lambda e:self._cycle_size());Tooltip(self.size_btn,"Resize widget")
        self.count_lbl=tk.Label(self.header,text="",bg=t["bg_header"],fg=t["text_mute"],font=(FONT,8));self.count_lbl.pack(side="right",padx=4)
        tk.Frame(self.root,bg=t["border"],height=1).pack(fill="x")
        tcf=tk.Frame(self.root,bg=t["bg_header"],height=32);tcf.pack(fill="x");tcf.pack_propagate(False)
        self.tab_canvas=tk.Canvas(tcf,bg=t["bg_header"],height=32,bd=0,highlightthickness=0);self.tab_canvas.pack(fill="both",expand=True)
        self.tab_bar=tk.Frame(self.tab_canvas,bg=t["bg_header"]);self._tab_win=self.tab_canvas.create_window((0,0),window=self.tab_bar,anchor="nw")
        self.tab_bar.bind("<Configure>",lambda e:self.tab_canvas.configure(scrollregion=self.tab_canvas.bbox("all")))
        self.tab_canvas.bind("<MouseWheel>",lambda e:self.tab_canvas.xview_scroll(int(-1*(e.delta/120)),"units"))
        self.tab_bar.bind("<MouseWheel>",lambda e:self.tab_canvas.xview_scroll(int(-1*(e.delta/120)),"units"))
        tk.Frame(self.root,bg=t["border"],height=1).pack(fill="x")
        self.scroll=ScrollFrame(self.root,bg=t["bg"]);self.scroll.pack(fill="both",expand=True)
        self.comp_bar=tk.Frame(self.root,bg=t["bg_header"],cursor="hand2");self.comp_bar.pack(fill="x")
        self.comp_arrow=tk.Label(self.comp_bar,text="▶",bg=t["bg_header"],fg=t["text_mute"],font=(FONT,7));self.comp_arrow.pack(side="left",padx=(12,4),pady=6)
        self.comp_lbl=tk.Label(self.comp_bar,text="Completed  (0)",bg=t["bg_header"],fg=t["text_mute"],font=(FONT,8));self.comp_lbl.pack(side="left")
        clr=tk.Label(self.comp_bar,text="Clear",bg=t["bg_header"],fg=t["del_idle"],font=(FONT,7),cursor="hand2");clr.pack(side="right",padx=12)
        clr.bind("<Button-1>",lambda e:self._clear_completed());clr.bind("<Enter>",lambda e:clr.configure(fg=t["del_hov"]));clr.bind("<Leave>",lambda e:clr.configure(fg=t["del_idle"]))
        for w in (self.comp_bar,self.comp_arrow,self.comp_lbl):w.bind("<Button-1>",lambda e:self._toggle_completed())
        self.comp_frame=tk.Frame(self.root,bg=t["bg_comp"]);self._comp_scroll=ScrollFrame(self.comp_frame,bg=t["bg_comp"]);self._comp_scroll.pack(fill="both",expand=True)
        tk.Frame(self.root,bg=t["border"],height=1).pack(fill="x")
        inp=tk.Frame(self.root,bg=t["bg_input"],height=46);inp.pack(fill="x",side="bottom");inp.pack_propagate(False)
        self.mode_btn=tk.Label(inp,text="¶",bg=t["bg_input"],fg=t["text_mute"],font=(FONT,11,"bold"),cursor="hand2",padx=6)
        self.mode_btn.pack(side="left",padx=(8,0));self.mode_btn.bind("<Button-1>",lambda e:self._cycle_input_mode())
        att=tk.Label(inp,text="+",bg=t["bg_input"],fg=t["text_mute"],font=(FONT,16),cursor="hand2");att.pack(side="left",padx=(6,4))
        att.bind("<Button-1>",self._browse_and_add_file);att.bind("<Enter>",lambda e:att.configure(fg=t["tab_act"]));att.bind("<Leave>",lambda e:att.configure(fg=t["text_mute"]))
        self.entry_var=tk.StringVar()
        self.entry=tk.Entry(inp,textvariable=self.entry_var,bg=t["bg_input"],fg=t["text_hint"],insertbackground=t["text"],relief="flat",font=(FONT,11),bd=0)
        self.entry.pack(side="left",fill="both",expand=True,padx=(0,12))
        self.entry.bind("<Return>",self._add_goal);self.entry.bind("<FocusIn>",self._hint_clear);self.entry.bind("<FocusOut>",self._hint_show)
        self.entry_var.trace_add("write",self._on_entry_changed)
        self._hint_active=True;self._input_mode="goal";self.entry_var.set(HINTS["goal"])
        self.scroll.canvas.bind("<Button-1>",self._focus_entry)
        self.root.bind("<Control-comma>",lambda e:self._open_settings());self.root.bind("<Control-t>",lambda e:self._new_workspace())
        self.root.bind("<Control-slash>",lambda e:self._focus_entry());self.root.bind("<Control-c>",self._on_copy)
        self.root.bind("<Escape>",self._on_escape);self.root.bind("<Tab>",lambda e:self._tab_next() if not self._entry_focused() else None)
        self.root.bind("<Return>",self._add_goal);self.root.bind("<KP_Enter>",self._add_goal)
        for i in range(1,10):self.root.bind(f"<Control-Key-{i}>",lambda e,n=i:self._switch_to_ws_by_number(n))
        self._refresh_tabs();self._render_all()

    def _full_redraw(self):
        for w in self.root.winfo_children():w.destroy()
        self.comp_open=False;self._input_mode="goal";self._selected_uids=set();self._clipboard_goals=[]
        self._drag_active=False;self._drag_pending_uid=None;self.root.configure(bg=self.T["bg"]);self._build_ui()

    def _on_escape(self,event=None):self._clear_selection();self._clipboard_goals=[]

    def _cycle_input_mode(self):
        modes=["goal","header_sm","header_lg"];self._input_mode=modes[(modes.index(self._input_mode)+1)%3];t=self.T
        if self._input_mode=="goal":self.mode_btn.configure(text="¶",fg=t["text_mute"],font=(FONT,11,"bold"))
        elif self._input_mode=="header_sm":self.mode_btn.configure(text="H",fg=t["check_on"],font=(FONT,11,"bold"))
        else:self.mode_btn.configure(text="H",fg=t["tab_act"],font=(FONT,14,"bold"))
        if self._hint_active:self.entry_var.set(HINTS[self._input_mode])
    def _current_hint(self):return HINTS.get(self._input_mode,HINTS["goal"])
    def _hint_show(self,_=None):
        if not self.entry_var.get().strip():
            self._hint_active=True;self.entry.configure(fg=self.T["text_hint"]);self.entry_var.set(self._current_hint())
    def _hint_clear(self,_=None):
        if self._hint_active:self._hint_active=False;self.entry_var.set("");self.entry.configure(fg=self.T["text"])
    def _on_entry_changed(self,*_):
        if self._hint_active or getattr(self,'_clearing_hint',False):return
        val=self.entry_var.get();hint=self._current_hint()
        if hint in val:
            clean=val.replace(hint,"");self._clearing_hint=True;self.entry_var.set(clean);self.entry.icursor(len(clean));self.entry.configure(fg=self.T["text"]);self._clearing_hint=False

    def _ensure_entry_works(self):
        try:
            cur = self.entry_var.get().strip()
            if cur in (HINTS["goal"], HINTS["header_sm"], HINTS["header_lg"], ""):
                self._hint_active = True; self.entry.configure(fg=self.T["text_hint"])
                if not cur: self.entry_var.set(self._current_hint())
            else:
                self._hint_active = False; self.entry.configure(fg=self.T["text"])
        except Exception: pass

    # ── Tabs ──────────────────────────────────────────────────────────────────
    def _refresh_tabs(self):
        t=self.T
        for w in self.tab_bar.winfo_children():w.destroy()
        for idx,(key,ws) in enumerate(self.data["workspaces"].items()):
            active=(key==self.data["active_tab"]);nh=f"  Ctrl+{idx+1}" if idx<9 else ""
            lbl=tk.Label(self.tab_bar,text=ws["name"],bg=t["bg_header"],fg=t["tab_act"] if active else t["tab_idle"],
                font=(FONT,8,"bold" if active else "normal"),cursor="hand2",padx=10,pady=8);lbl.pack(side="left")
            lbl.bind("<Button-1>",lambda e,k=key:self._switch_tab(k));lbl.bind("<Button-3>",lambda e,k=key:self._tab_context_menu(e,k))
            lbl.bind("<MouseWheel>",lambda e:self.tab_canvas.xview_scroll(int(-1*(e.delta/120)),"units"))
            ct=len([g for g in ws.get("goals",[]) if not g.get("done") and g.get("type")!="header"])
            Tooltip(lbl,f"{ws['name']}  —  {ct} active{nh}")
            if active:tk.Frame(self.tab_bar,bg=t["tab_act"],height=2,width=max(len(ws["name"])*7,20)).place(in_=lbl,relx=0,rely=1.0,anchor="sw")
        add_tab=tk.Label(self.tab_bar,text="＋",bg=t["bg_header"],fg=t["del_idle"],font=(FONT,10),cursor="hand2",padx=8);add_tab.pack(side="left")
        add_tab.bind("<Button-1>",lambda e:self._new_workspace());add_tab.bind("<Enter>",lambda e:add_tab.configure(fg=t["text_mute"]));add_tab.bind("<Leave>",lambda e:add_tab.configure(fg=t["del_idle"]))
        Tooltip(add_tab,"New workspace  (Ctrl+T)")
    def _switch_tab(self,key):self.data["active_tab"]=key;save_data(self.data);self._selected_uids=set();self._refresh_tabs();self._render_all()
    def _switch_to_ws_by_number(self,n):
        keys=list(self.data["workspaces"].keys())
        if n<=len(keys):self._switch_tab(keys[n-1])
    def _new_workspace(self):
        t=self.T;overlay=tk.Frame(self.root,bg=t["bg_header"]);overlay.place(relx=0,rely=0,relwidth=1.0,height=34,y=self.header.winfo_height()+1);overlay.lift()
        var=tk.StringVar();ent=tk.Entry(overlay,textvariable=var,bg=t["bg_input"],fg=t["text"],insertbackground=t["text"],relief="flat",font=(FONT,9),bd=0)
        ent.pack(side="left",fill="both",expand=True,padx=(10,6),pady=6);ent.insert(0,"Workspace name…");ent.select_range(0,"end");ent.focus_set()
        def confirm(e=None):
            name=var.get().strip();overlay.destroy()
            if not name or name=="Workspace name…":return
            key=f"ws_{len(self.data['workspaces'])}_{name.lower().replace(' ','_')}";self.data["workspaces"][key]={"name":name,"goals":[]}
            self.data["active_tab"]=key;save_data(self.data);self._refresh_tabs();self._render_all();self._sync_settings()
        ent.bind("<Return>",confirm);ent.bind("<Escape>",lambda e:overlay.destroy());ent.bind("<FocusOut>",lambda e:overlay.destroy())
        ok=tk.Label(overlay,text="OK",bg=t["check_on"],fg="#000",font=(FONT,8,"bold"),padx=8,cursor="hand2");ok.pack(side="right",padx=(0,6),pady=6);ok.bind("<Button-1>",confirm)
    def _entry_focused(self):
        try:return self.root.focus_get() is self.entry
        except Exception:return False
    def _focus_entry(self,event=None):self._hint_clear();self.entry.focus_set();return "break"
    def _tab_next(self):
        keys=list(self.data["workspaces"].keys())
        if len(keys)<2:return "break"
        idx=keys.index(self.data["active_tab"]) if self.data["active_tab"] in keys else 0
        self._switch_tab(keys[(idx+1)%len(keys)]);return "break"
    def _current_goals(self):return self.data["workspaces"].get(self.data["active_tab"],{}).get("goals",[])

    # ── Selection / Copy / Paste ──────────────────────────────────────────────
    def _toggle_select(self,uid):
        if uid in self._selected_uids:self._selected_uids.discard(uid)
        else:self._selected_uids.add(uid)
        self._update_selection_visuals()
    def _clear_selection(self):
        if self._selected_uids:self._selected_uids=set();self._update_selection_visuals()
    def _update_selection_visuals(self):
        t=self.T;sel=t.get("sel_bg",t["border"])
        for uid,entry in self._row_widget_map.items():
            bg=sel if uid in self._selected_uids else entry.get("orig_bg",t["bg_row"])
            for w in entry.get("recolor",[]):
                try:w.configure(bg=bg)
                except Exception:pass
    def _copy_selected(self):
        goals=self._current_goals();self._clipboard_goals=[]
        for g in goals:
            uid=g.get('_uid')
            if uid and uid in self._selected_uids:
                c=copy.deepcopy(g);c.pop('_uid',None);c.pop('done',None);self._clipboard_goals.append(c)
        self._clear_selection()
    def _paste_goals(self):
        if not self._clipboard_goals:return
        for g in self._clipboard_goals:
            ng=copy.deepcopy(g);ng['_uid']=uuid.uuid4().hex[:12];ng['done']=False;self._current_goals().append(ng)
        save_data(self.data);self._render_all();self.root.after(50,lambda:self.scroll.canvas.yview_moveto(1.0))

    # ── Render ────────────────────────────────────────────────────────────────
    def _render_all(self):
        t=self.T
        self._prune_image_cache()
        self._row_widget_map={};self._render_order=[]
        # Recreate inner frame cleanly
        self.scroll.reset_inner(t["bg"])
        tab=self.data["active_tab"];ws=self.data["workspaces"].get(tab,{});goals=ws.get("goals",[])
        name=ws.get("name","").upper();mc=max(8,(self._current_wh()[0]-140)//8)
        if len(name)>mc:name=name[:mc-1]+"…"
        self.ws_label.configure(text=name,fg=t["text_mute"])
        has_vis=any(not g.get("done") for g in goals);act_ct=sum(1 for g in goals if not g.get("done") and g.get("type")!="header")
        if not has_vis:
            tk.Label(self.scroll.inner,text="Nothing here.\nAdd a goal below.",bg=t["bg"],fg=t["text_hint"],font=(FONT,10),justify="center").pack(expand=True,pady=36)
        else:
            for i,g in enumerate(goals):
                if not g.get("done"):
                    try:
                        self._render_row(i,g)
                    except Exception as e:
                        log_error(f"_render_row({i}) failed: {traceback.format_exc()}")
                        try:
                            uid=self._ensure_uid(g);ef=tk.Frame(self.scroll.inner,bg=t["bg_row"]);ef.pack(fill="x")
                            tk.Label(ef,text=f"⚠ render error: {g.get('text',g.get('filename','?'))[:40]}",bg=t["bg_row"],fg="#e05555",font=(FONT,8),anchor="w").pack(side="left",padx=10,pady=6)
                            dl=tk.Label(ef,text="×",bg=t["bg_row"],fg=t["del_hov"],font=(FONT,13),cursor="hand2");dl.pack(side="right",padx=8)
                            dl.bind("<Button-1>",lambda e,u=uid:self._delete_goal(u))
                            tk.Frame(self.scroll.inner,bg=t["border"],height=1).pack(fill="x")
                        except Exception:pass
        done_ct=sum(1 for g in goals if g.get("done"));self._update_count(act_ct,act_ct+done_ct)
        self._render_completed_section()
        if self._selected_uids:self._update_selection_visuals()
        self.scroll.inner.update_idletasks()
        self.scroll._update_scroll()

    def _bind_row_drag(self, widgets, uid):
        for w in widgets:
            w.bind("<ButtonPress-1>", lambda e, u=uid: self._row_press(e, u), add="+")
            w.bind("<B1-Motion>", self._row_motion, add="+")
            w.bind("<ButtonRelease-1>", self._row_release, add="+")

    def _render_row(self,index,goal):
        t=self.T;uid=self._ensure_uid(goal);self._render_order.append(uid)

        if goal.get("type")=="header":
            sz=goal.get("size","sm");fs=15 if sz=="lg" else 10;py=(10,10) if sz=="lg" else (7,7)
            bg=t["bg_comp"] if sz=="sm" else t["bg_header"]
            row=tk.Frame(self.scroll.inner,bg=bg);row.pack(fill="x")
            tk.Frame(row,bg=t["check_on"],width=3).pack(side="left",fill="y")
            inner=tk.Frame(row,bg=bg);inner.pack(fill="x",padx=(4,10),pady=py)
            hlbl=tk.Label(inner,text=goal["text"],bg=bg,fg=t["tab_act"],font=(FONT,fs,"bold"),anchor="w",wraplength=210,justify="left")
            hlbl.pack(side="left",fill="x",expand=True)
            d=tk.Label(inner,text="×",bg=bg,fg=t["del_idle"],font=(FONT,13),cursor="hand2");d.pack(side="right")
            d.bind("<Button-1>",lambda e,u=uid:self._delete_goal(u));d.bind("<Enter>",lambda e,b=d:b.configure(fg=t["del_hov"]));d.bind("<Leave>",lambda e,b=d:b.configure(fg=t["del_idle"]))
            def _hctx(e,u=uid):
                m=tk.Menu(self.root,tearoff=0,bg=t["bg_row2"],fg=t["text"],font=(FONT,9));m.add_command(label="Edit",command=lambda:self._edit_goal_inline(u))
                try:m.tk_popup(e.x_root,e.y_root)
                finally:m.grab_release()
            for w in (row,inner,hlbl):w.bind("<Button-3>",_hctx);w.bind("<Control-Button-1>",lambda e,u=uid:self._toggle_select(u))
            self._bind_row_drag([row, inner, hlbl], uid)
            sep=tk.Frame(self.scroll.inner,bg=t["border"],height=1);sep.pack(fill="x")
            self._row_widget_map[uid]={"row_type":"header","frame":row,"sep":sep,"orig_bg":bg,"recolor":[row,inner,hlbl,d],"label":hlbl,"inner":inner}
            return

        if goal.get("type")=="media":
            mt=goal.get("media_type","file");fn=goal.get("filename","");fp=os.path.join(MEDIA_DIR,fn);cbg=t["bg_header"]
            card=tk.Frame(self.scroll.inner,bg=t["border"]);card.pack(fill="x",padx=12,pady=6)
            inner=tk.Frame(card,bg=cbg);inner.pack(fill="x",padx=1,pady=1)
            top=tk.Frame(inner,bg=cbg);top.pack(fill="x",padx=6,pady=6)
            icons={"image":"🖼️","audio":"🎵","video":"🎬","pdf":"📄","file":"📁"}
            nlbl=tk.Label(top,text=f"{icons.get(mt,'📁')}  {fn}",bg=cbg,fg=t["text"],font=(FONT,9,"bold"),cursor="hand2",anchor="w")
            nlbl.pack(side="left",fill="x",expand=True,padx=(4,0))
            nlbl.bind("<Button-1>",lambda e,f=fp:os.startfile(f) if hasattr(os,'startfile') and os.path.exists(f) else None)
            nlbl.bind("<Enter>",lambda e:nlbl.configure(fg=t["tab_act"]));nlbl.bind("<Leave>",lambda e:nlbl.configure(fg=t["text"]))
            d=tk.Label(top,text="×",bg=cbg,fg=t["del_idle"],font=(FONT,13),cursor="hand2");d.pack(side="right",padx=(4,0))
            d.bind("<Button-1>",lambda e,u=uid:self._delete_goal(u));d.bind("<Enter>",lambda e,b=d:b.configure(fg=t["del_hov"]));d.bind("<Leave>",lambda e,b=d:b.configure(fg=t["del_idle"]))
            if mt=="image" and os.path.exists(fp):
                imf=tk.Frame(inner,bg=cbg);imf.pack(fill="x",padx=10,pady=(0,10))
                try:
                    def _load_img(fp=fp):
                        img=Image.open(fp)
                        try:img.thumbnail((280,200),Image.Resampling.LANCZOS)
                        except:img.thumbnail((280,200),Image.ANTIALIAS)
                        return ImageTk.PhotoImage(img)
                    photo=self._get_cached_image(fn, _load_img)
                    if photo:
                        il=tk.Label(imf,image=photo,bg="#000",cursor="hand2");il.image=photo;il.pack(pady=2);il.bind("<Button-1>",lambda e,f=fp:self._show_image_popup(f))
                    else:
                        tk.Label(imf,text="(Preview unavailable)",bg=cbg,fg=t["text_mute"],font=(FONT,8)).pack()
                except:tk.Label(imf,text="(Preview unavailable)",bg=cbg,fg=t["text_mute"],font=(FONT,8)).pack()
            elif mt=="pdf" and os.path.exists(fp):
                pf=tk.Frame(inner,bg=cbg);pf.pack(fill="x",padx=10,pady=(0,10))
                try:
                    cache_key=fn+"_pdf"
                    def _load_pdf(fp=fp):
                        import fitz;from io import BytesIO;doc=fitz.open(fp);pix=doc[0].get_pixmap(matrix=fitz.Matrix(0.6,0.6))
                        img=Image.open(BytesIO(pix.tobytes("png")))
                        try:img.thumbnail((280,360),Image.Resampling.LANCZOS)
                        except:img.thumbnail((280,360),Image.ANTIALIAS)
                        p=ImageTk.PhotoImage(img);doc.close();return p
                    photo=self._get_cached_image(cache_key, _load_pdf)
                    if photo:
                        il=tk.Label(pf,image=photo,bg="#1a1a1a",cursor="hand2");il.image=photo;il.pack(pady=2)
                        il.bind("<Button-1>",lambda e,f=fp:os.startfile(f) if hasattr(os,'startfile') else None)
                    else:
                        tk.Label(pf,text="(PDF preview unavailable)",bg=cbg,fg=t["text_mute"],font=(FONT,8)).pack()
                except ImportError:tk.Label(pf,text="pip install pymupdf",bg=cbg,fg=t["text_mute"],font=(FONT,8)).pack(pady=4)
                except:tk.Label(pf,text="(PDF preview unavailable)",bg=cbg,fg=t["text_mute"],font=(FONT,8)).pack()
            desc=goal.get("text","");dlbl=None
            if desc:dlbl=tk.Label(inner,text=desc,bg=cbg,fg=t["text"],font=(FONT,10),justify="left",wraplength=220);dlbl.pack(anchor="w",padx=10,pady=(0,10))
            def _mctx(e,u=uid):
                m=tk.Menu(self.root,tearoff=0,bg=t["bg_row2"],fg=t["text"],font=(FONT,9))
                if u in self._selected_uids and len(self._selected_uids)>1:m.add_command(label=f"Copy {len(self._selected_uids)} items",command=self._copy_selected);m.add_separator()
                m.add_command(label="Edit description",command=lambda:self._edit_goal_inline(u))
                try:m.tk_popup(e.x_root,e.y_root)
                finally:m.grab_release()
            for w in (card,inner,top):w.bind("<Button-3>",_mctx);w.bind("<Control-Button-1>",lambda e,u=uid:self._toggle_select(u))
            self._bind_row_drag([card, inner, top], uid)
            self._row_widget_map[uid]={"row_type":"media","frame":card,"sep":None,"orig_bg":cbg,"recolor":[card,inner,top,nlbl,d],"label":dlbl,"inner":inner}
            return

        # ── Goal ──────────────────────────────────────────────────────────────
        all_g=self._current_goals();vis_idx=sum(1 for g in all_g[:index] if not g.get("done") and g.get("type") not in ("header","media"))
        orig_bg=t["bg_row2"] if vis_idx%2==1 else t["bg_row"];bg=t.get("sel_bg",t["border"]) if uid in self._selected_uids else orig_bg
        row=tk.Frame(self.scroll.inner,bg=bg);row.pack(fill="x")
        inner=tk.Frame(row,bg=bg);inner.pack(fill="x",padx=10,pady=7)
        cz=tk.Frame(inner,bg=bg,cursor="hand2",highlightbackground=t["check_off"],highlightthickness=1);cz.pack(side="left",padx=(0,6),pady=1)
        chk=tk.Label(cz,text="○",bg=bg,fg=t["check_off"],font=(FONT,12),cursor="hand2",padx=3,pady=1);chk.pack()
        for w in (cz,chk):
            w.bind("<Button-1>",lambda e,u=uid:self._complete_goal(u))
            w.bind("<Enter>",lambda e:(cz.configure(highlightbackground=t["check_on"]),chk.configure(fg=t["check_on"])))
            w.bind("<Leave>",lambda e:(cz.configure(highlightbackground=t["check_off"]),chk.configure(fg=t["check_off"])))

        text=goal["text"];raw_urls=URL_RE.findall(text);urls=[_clean_url(u) for u in raw_urls if _clean_url(u)]
        link_fg=t.get("link","#5b9cf0")
        if urls:
            first_url=urls[0];norm=_normalize_url(first_url)
            is_pure_url = text.strip()==first_url or text.strip()==raw_urls[0]
            lbl_font = (FONT, 10, "underline") if is_pure_url else (FONT, 10)
            lbl=tk.Label(inner,text=text,bg=bg,fg=link_fg,font=lbl_font,anchor="w",wraplength=210,justify="left",cursor="hand2")
            lbl.pack(side="left",fill="x",expand=True)
            lbl.bind("<Button-1>",lambda e,u=norm:webbrowser.open(u))
            if not is_pure_url:
                tip_text=norm if len(norm)<60 else norm[:57]+"…"
                Tooltip(lbl, tip_text)
        else:
            lbl=tk.Label(inner,text=text,bg=bg,fg=t["text"],font=(FONT,10),anchor="w",wraplength=210,justify="left")
            lbl.pack(side="left",fill="x",expand=True)

        d=tk.Label(inner,text="×",bg=bg,fg=t["del_idle"],font=(FONT,13),cursor="hand2");d.pack(side="right")
        d.bind("<Button-1>",lambda e,u=uid:self._delete_goal(u));d.bind("<Enter>",lambda e,b=d:b.configure(fg=t["del_hov"]));d.bind("<Leave>",lambda e,b=d:b.configure(fg=t["del_idle"]))
        def _gctx(e,u=uid,g=goal):
            m=tk.Menu(self.root,tearoff=0,bg=t["bg_row2"],fg=t["text"],activebackground=t["check_off"],activeforeground=t["text"],font=(FONT,9))
            if u in self._selected_uids and len(self._selected_uids)>1:m.add_command(label=f"Copy {len(self._selected_uids)} goals",command=self._copy_selected);m.add_separator()
            m.add_command(label="Copy text",command=lambda:self._copy_goal_text(g.get("text","")))
            gu=[_clean_url(x) for x in URL_RE.findall(g.get("text","")) if _clean_url(x)]
            if gu:m.add_command(label="Copy link",command=lambda:self._copy_goal_text(gu[0]));m.add_command(label="Open link",command=lambda:webbrowser.open(_normalize_url(gu[0])))
            m.add_command(label="Edit",command=lambda:self._edit_goal_inline(u))
            try:m.tk_popup(e.x_root,e.y_root)
            finally:m.grab_release()
        for w in (row,inner,lbl):w.bind("<Button-3>",_gctx);w.bind("<Control-Button-1>",lambda e,u=uid:self._toggle_select(u))
        if urls:
            self._bind_row_drag([row, inner], uid)
        else:
            self._bind_row_drag([row, inner, lbl], uid)
        sep=tk.Frame(self.scroll.inner,bg=t["border"],height=1);sep.pack(fill="x")
        self._row_widget_map[uid]={"row_type":"goal","frame":row,"sep":sep,"orig_bg":orig_bg,"recolor":[row,inner,chk,cz,lbl,d],"label":lbl,"inner":inner}

    def _render_completed_section(self):
        t=self.T;tab=self.data["active_tab"];inner=self._comp_scroll.inner
        for w in inner.winfo_children():w.destroy()
        ws_done=[c for c in self.data.get("completed",[]) if c.get("workspace")==tab]
        self.comp_lbl.configure(text=f"Completed  ({len(ws_done)})")
        if not self.comp_open or not ws_done:return
        for g in ws_done:
            bg=t["bg_comp"];row=tk.Frame(inner,bg=bg);row.pack(fill="x");ir=tk.Frame(row,bg=bg);ir.pack(fill="x",padx=10,pady=5)
            tk.Label(ir,text="✓",bg=bg,fg=t["check_on"],font=(FONT,10),width=2).pack(side="left")
            if g.get("type")=="media":
                icons={"image":"🖼️","audio":"🎵","video":"🎬","pdf":"📄","file":"📁"};dt=f"{icons.get(g.get('media_type','file'),'📁')} {g.get('filename','')}"
            else:dt=g.get("text","")
            tk.Label(ir,text=dt,bg=bg,fg=t["text_done"],font=(FONT,9,"overstrike"),anchor="w",wraplength=175,justify="left").pack(side="left",fill="x",expand=True,padx=(4,0))
            rb=tk.Label(ir,text="↩",bg=bg,fg=t["text_mute"],font=(FONT,11),cursor="hand2");rb.pack(side="right",padx=(0,4))
            rb.bind("<Button-1>",lambda e,gi=g:self._restore_goal(gi));rb.bind("<Enter>",lambda e,b=rb:b.configure(fg=t["check_on"]));rb.bind("<Leave>",lambda e,b=rb:b.configure(fg=t["text_mute"]))
            dl=tk.Label(ir,text="×",bg=bg,fg=t["del_idle"],font=(FONT,11),cursor="hand2");dl.pack(side="right")
            dl.bind("<Button-1>",lambda e,gi=g:self._remove_completed(gi));dl.bind("<Enter>",lambda e,b=dl:b.configure(fg=t["del_hov"]));dl.bind("<Leave>",lambda e,b=dl:b.configure(fg=t["del_idle"]))
            tk.Frame(inner,bg=t["border"],height=1).pack(fill="x")
    def _toggle_completed(self):
        self.comp_open=not self.comp_open;self.comp_arrow.configure(text="▼" if self.comp_open else "▶")
        if self.comp_open:
            _,wh=self._current_wh();self.comp_frame.configure(height=min(160,wh//3));self.comp_frame.pack_propagate(False)
            self.comp_frame.pack(fill="x",after=self.comp_bar);self._render_completed_section()
        else:self.comp_frame.pack_forget()
    def _update_count(self,active,total):self.count_lbl.configure(fg=self.T["text_hint"],text=f"{total-active}/{total}" if total else "")

    # ── Goal actions ──────────────────────────────────────────────────────────
    def _complete_goal(self,uid):self._complete_goal_in_ws(uid,self.data["active_tab"])
    def _complete_goal_in_ws(self,uid,wk):
        goals=self.data["workspaces"].get(wk,{}).get("goals",[]);index=-1
        for i,g in enumerate(goals):
            if g.get('_uid')==uid:index=i;break
        if index<0:return
        g=goals.pop(index);g["done"]=True;g["workspace"]=wk;g["completed_at"]=time.time()
        self.data.setdefault("completed",[]).insert(0,g);self.data["completed"]=self.data["completed"][:200];save_data(self.data)
        if wk==self.data["active_tab"]:self._render_all()
        if self.comp_open:self._render_completed_section()
    def _restore_goal(self,go):
        self.data["completed"]=[c for c in self.data["completed"] if c is not go]
        wk=go.pop("workspace",self.data["active_tab"]);go.pop("done",None);go.pop("completed_at",None)
        ws=self.data["workspaces"].get(wk)
        if ws is None:wk=self.data["active_tab"];ws=self.data["workspaces"].setdefault(wk,{"name":"Today","goals":[]})
        ws.setdefault("goals",[]).append(go);save_data(self.data);self._render_all();self._render_completed_section()
    def _delete_goal(self,uid):
        goals=self._current_goals();idx=self._find_goal_index_by_uid(uid)
        if idx<0:return
        g=goals[idx]
        if g.get("type")=="media":
            fn=g.get("filename","");fp=os.path.join(MEDIA_DIR,fn)
            if os.path.exists(fp):
                try:os.remove(fp)
                except Exception:pass
            self._image_cache.pop(fn, None)
            self._image_cache.pop(fn + "_pdf", None)
        goals.pop(idx);save_data(self.data);self._selected_uids.discard(uid);self._render_all()
    def _copy_goal_text(self,text):self.root.clipboard_clear();self.root.clipboard_append(text)

    # ── Inline edit — multiline Text widget ───────────────────────────────────
    def _edit_goal_inline(self,uid):
        ei=self._row_widget_map.get(uid);goal=self._find_goal_by_uid(uid)
        if not ei or not goal:return
        lbl=ei.get("label");inner=ei.get("inner")
        if not lbl or not inner:return
        t=self.T;current=goal.get("text","")
        try:bg=lbl.cget("bg")
        except Exception:bg=t["bg_row"]

        lbl.pack_forget()
        _done=[False]

        # Fix: Estimate chars per line from available pixel width
        cpl = max(12, (self._current_wh()[0] - 90) // 8)
        est_h = max(1, min((len(current) + cpl - 1) // cpl, 8))

        # width=cpl instead of width=1 prevents it from shrinking or stretching off screen
        ee = tk.Text(inner, bg=bg, fg=t["text"], insertbackground=t["text"],
                     relief="flat", font=(FONT, 10), bd=0, wrap="word",
                     width=cpl, height=est_h,
                     padx=2, pady=0, undo=True,
                     selectbackground=t.get("sel_bg", t["border"]),
                     selectforeground=t["text"],
                     highlightthickness=0, spacing1=0, spacing3=0)
        ee.insert("1.0", current)
        ee.pack(side="left", fill="x", expand=True)
        ee.focus_set()
        # Fix: Cursor at end — no selection so typing doesn't instantly delete text
        ee.mark_set("insert", "end")
        ee.see("end")

        def _resize(event=None):
            content = ee.get("1.0", "end-1c")
            h = max(1, min((len(content) + cpl - 1) // cpl, 8))
            ee.configure(height=h)
            self.scroll._update_scroll()
        ee.bind("<KeyRelease>", _resize)

        def confirm(e=None):
            if _done[0]: return "break"
            _done[0] = True
            nt = ee.get("1.0", "end-1c").strip()
            try: ee.destroy()
            except Exception: pass
            g = self._find_goal_by_uid(uid)
            if g and nt:
                g["text"] = nt; save_data(self.data)
            self._render_all()
            return "break"

        def cancel(e=None):
            if _done[0]: return "break"
            _done[0] = True
            try: ee.destroy()
            except Exception: pass
            try:
                if lbl.winfo_exists(): lbl.pack(side="left", fill="x", expand=True)
            except Exception: pass
            return "break"

        ee.bind("<Return>", confirm)
        ee.bind("<Escape>", cancel)
        ee.bind("<FocusOut>", confirm)
        ee.bind("<Tab>", lambda e: (confirm(), "break")[-1])

    def _add_goal(self,event=None):
        text=self.entry_var.get().strip()
        if not text or text in (HINTS["goal"],HINTS["header_sm"],HINTS["header_lg"]):
            self._hint_active = True
            self._focus_entry();return
        self._hint_active = False
        if self._input_mode=="header_sm":item={"type":"header","size":"sm","text":text}
        elif self._input_mode=="header_lg":item={"type":"header","size":"lg","text":text}
        else:item={"text":text,"done":False}
        self._ensure_uid(item);self._current_goals().append(item);save_data(self.data)
        self.entry_var.set("");self.entry.configure(fg=self.T["text"]);self.entry.focus_set()
        self._render_all();self.root.after(50,lambda:self.scroll.canvas.yview_moveto(1.0))

    def _remove_completed(self,go):
        self.data["completed"]=[c for c in self.data["completed"] if c is not go];save_data(self.data);self._render_completed_section();self._render_all()
    def _clear_completed(self):
        tab=self.data["active_tab"];self.data["completed"]=[c for c in self.data.get("completed",[]) if c.get("workspace")!=tab]
        save_data(self.data)
        if self.comp_open:self._render_completed_section()
        self._render_all()
    def _cleanup_old_completed(self):
        cutoff=time.time()-86400;before=len(self.data.get("completed",[]))
        self.data["completed"]=[c for c in self.data.get("completed",[]) if c.get("completed_at",time.time())>cutoff]
        if len(self.data["completed"])!=before:
            save_data(self.data)
            try:
                if self.comp_open:self._render_completed_section()
                self._render_all()
            except Exception:pass
        self.root.after(3_600_000,self._cleanup_old_completed)

    # ── Drag reorder ──────────────────────────────────────────────────────────
    def _row_press(self, event, uid):
        if event.state & 0x4: return
        self._drag_pending_uid = uid
        self._drag_press_x = event.x_root
        self._drag_press_y = event.y_root

    def _row_motion(self, event):
        if self._drag_pending_uid and not self._drag_active:
            dx = abs(event.x_root - self._drag_press_x)
            dy = abs(event.y_root - self._drag_press_y)
            if dx > 6 or dy > 6:
                self._start_row_drag(event, self._drag_pending_uid)
                self._drag_pending_uid = None
        if self._drag_active:
            if self._drag_ghost:
                try: self._drag_ghost.geometry(f"+{event.x_root+10}+{event.y_root-8}")
                except Exception: pass
            self._show_drop_line(self._calc_drop_idx(event.y_root))

    def _row_release(self, event):
        self._drag_pending_uid = None
        if not self._drag_active: return
        self._drag_active = False
        if self._drag_ghost:
            try: self._drag_ghost.destroy()
            except Exception: pass
            self._drag_ghost = None
        if self._drop_line:
            try: self._drop_line.place_forget(); self._drop_line.destroy()
            except Exception: pass
            self._drop_line = None
        di = self._calc_drop_idx(event.y_root)
        if self._drag_uid: self._reorder_goal(self._drag_uid, di)
        self._drag_uid = None

    def _start_row_drag(self, event, uid):
        self._drag_active = True; self._drag_uid = uid
        goal = self._find_goal_by_uid(uid)
        if not goal: self._drag_active = False; return
        text = goal.get("text", goal.get("filename", "?"))
        if len(text) > 30: text = text[:27] + "..."
        t = self.T
        self._drag_ghost = tk.Toplevel(self.root); self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes("-alpha", 0.75); self._drag_ghost.attributes("-topmost", True)
        tk.Label(self._drag_ghost, text=f"  {text}  ", bg=t["check_on"], fg="#000", font=(FONT, 9, "bold"), padx=6, pady=3).pack()
        self._drag_ghost.geometry(f"+{event.x_root+10}+{event.y_root-8}")
        self._drop_line = tk.Frame(self.scroll.inner, bg=t["check_on"], height=3)

    def _calc_drop_idx(self, y_root):
        for i, uid in enumerate(self._render_order):
            entry = self._row_widget_map.get(uid)
            if not entry: continue
            fr = entry["frame"]
            try:
                if y_root < fr.winfo_rooty() + fr.winfo_height() / 2: return i
            except Exception: pass
        return len(self._render_order)

    def _show_drop_line(self, di):
        if not self._drop_line or not self._render_order: return
        y = 0
        if di <= 0:
            e = self._row_widget_map.get(self._render_order[0])
            if e: y = e["frame"].winfo_y()
        elif di >= len(self._render_order):
            e = self._row_widget_map.get(self._render_order[-1])
            if e: y = e["frame"].winfo_y() + e["frame"].winfo_height()
        else:
            e = self._row_widget_map.get(self._render_order[di])
            if e: y = e["frame"].winfo_y()
        try: self._drop_line.place(in_=self.scroll.inner, x=0, y=max(0, y - 1), relwidth=1.0, height=3)
        except Exception: pass

    def _reorder_goal(self, uid, target_di):
        goals = self._current_goals()
        active_before = [(i, g) for i, g in enumerate(goals) if not g.get("done")]
        src_di = None; src_data_idx = None
        for di, (data_idx, g) in enumerate(active_before):
            if g.get('_uid') == uid: src_di = di; src_data_idx = data_idx; break
        if src_data_idx is None: return
        if src_di is not None and src_di < target_di: target_di -= 1
        if src_di == target_di: return
        goal = goals.pop(src_data_idx)
        active_after = [(i, g) for i, g in enumerate(goals) if not g.get("done")]
        target_di = max(0, min(target_di, len(active_after)))
        if target_di >= len(active_after):
            insert_idx = active_after[-1][0] + 1 if active_after else 0
        else: insert_idx = active_after[target_di][0]
        goals.insert(insert_idx, goal); save_data(self.data); self._render_all()

    # ── Window drag ───────────────────────────────────────────────────────────
    def _wdrag_start(self, e): self._drag_x = e.x_root - self.root.winfo_x(); self._drag_y = e.y_root - self.root.winfo_y()
    def _wdrag_move(self, e): self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ── Visibility ────────────────────────────────────────────────────────────
    def _toggle_visibility(self):
        if self.visible:
            self.root.withdraw(); self.visible = False; self._user_hidden = True
        else:
            self._check_focused_app_workspace()
            self.root.deiconify(); self.root.lift()
            self.root.update_idletasks(); self.root.focus_force()
            self.visible = True; self._user_hidden = False
            self.root.after(50, self._ensure_entry_works)

    def _show(self):
        self._check_focused_app_workspace()
        self.root.deiconify(); self.root.lift()
        self.root.update_idletasks(); self.root.focus_force()
        self.visible = True; self._user_hidden = False
        self.root.after(50, self._ensure_entry_works)

    def _check_focused_app_workspace(self):
        if not HAS_WIN32 or not self.data.get("app_rules"): return
        proc = self._prev_focused_proc
        if not proc:
            try:
                hwnd = win32gui.GetForegroundWindow(); _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid).name().lower()
            except Exception: return
        for pat, wk in self.data.get("app_rules", {}).items():
            if pat.lower() in proc and wk in self.data["workspaces"]:
                if wk != self.data["active_tab"]:
                    self.data["active_tab"] = wk; save_data(self.data); self._refresh_tabs(); self._render_all()
                return

    def _initial_app_check(self):
        if not HAS_WIN32 or not self.data.get("app_rules"): return
        try:
            hwnd = win32gui.GetForegroundWindow(); _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid).name().lower(); self._prev_focused_proc = proc
            for pat, wk in self.data.get("app_rules", {}).items():
                if pat.lower() in proc and wk in self.data["workspaces"]:
                    self.data["active_tab"] = wk; save_data(self.data); self._refresh_tabs(); self._render_all()
                    if self.data["settings"].get("auto_show", True):
                        self.root.deiconify(); self.root.lift(); self.visible = True; self._user_hidden = False
                    return
        except Exception: pass

    def _cycle_size(self):
        self._size_idx=(self._size_idx+1)%len(SIZE_PRESETS);self.data["settings"]["size_idx"]=self._size_idx;save_data(self.data)
        cw,ch=self._current_wh();self.root.geometry(f"{cw}x{ch}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self.size_btn.configure(text=SIZE_LABELS[self._size_idx]);self._render_all()
    def _open_fileshare(self):
        if self._share_win and self._share_win.alive:self._share_win.win.lift();return
        self._share_win=FileSharePanel(self)
    def _flash_share_btn(self,fn=""):
        try:
            btn=self._share_btn_ref;t=self.T;btn.configure(fg=t["check_on"])
            tip=tk.Label(self.root,text=f"📱 {fn} saved",bg=t["check_on"],fg="#000",font=(FONT,8),padx=8,pady=4);tip.place(relx=1.0,rely=0.0,anchor="ne",x=-4,y=46)
            self.root.after(3500,lambda:[btn.configure(fg=t["tab_act"]),tip.destroy()])
        except Exception:pass

    # ── Settings ──────────────────────────────────────────────────────────────
    def _open_settings(self):
        if self.settings_win and self.settings_win.winfo_exists():self.settings_win.lift();return
        win=tk.Toplevel(self.root);self.settings_win=win;win.title("Aside — Settings");win.configure(bg=S["bg"])
        win.geometry("400x640");win.resizable(False,False);win.attributes("-topmost",True)
        hdr=tk.Frame(win,bg=S["bg"]);hdr.pack(fill="x",padx=20,pady=(18,6))
        tk.Label(hdr,text="Settings",bg=S["bg"],fg=S["text"],font=(FONT,14,"bold")).pack(side="left")
        tk.Label(hdr,text="Changes apply instantly",bg=S["bg"],fg=S["mute"],font=(FONT,8)).pack(side="left",padx=10)
        tk.Frame(win,bg=S["border"],height=1).pack(fill="x")
        body=ScrollFrame(win,bg=S["bg"]);body.pack(fill="both",expand=True);f=body.inner
        def slbl(p,t,sz=9,mute=False,**kw):return tk.Label(p,text=t,bg=S["bg"],fg=S["mute"] if mute else S["text"],font=(FONT,sz),**kw)
        def sep():tk.Frame(f,bg=S["border"],height=1).pack(fill="x",padx=16,pady=10)
        def section(title):
            r=tk.Frame(f,bg=S["bg"]);r.pack(fill="x",padx=16,pady=(12,4))
            tk.Label(r,text=title.upper(),bg=S["bg"],fg=S["accent"],font=(FONT,7,"bold")).pack(side="left")
            tk.Frame(r,bg=S["border"],height=1).pack(side="left",fill="x",expand=True,padx=(8,0))
        section("Appearance")
        tr=tk.Frame(f,bg=S["bg"]);tr.pack(fill="x",padx=16,pady=4);slbl(tr,"Theme").pack(side="left")
        for nm,sw in THEMES.items():
            act=(nm==self.data["settings"].get("theme","Dark"))
            b=tk.Label(tr,text=nm,bg=sw["bg_header"],fg=sw["tab_act"] if act else sw["tab_idle"],font=(FONT,8,"bold" if act else "normal"),
                relief="solid" if act else "flat",bd=1 if act else 0,padx=8,pady=4,cursor="hand2");b.pack(side="right",padx=3)
            b.bind("<Button-1>",lambda e,n=nm:self._set_theme(n))
        ar=tk.Frame(f,bg=S["bg"]);ar.pack(fill="x",padx=16,pady=(10,2));slbl(ar,"Transparency").pack(side="left")
        av=tk.Label(ar,bg=S["bg"],fg=S["mute"],font=(FONT,8),width=16);av.pack(side="right")
        ca=self.data["settings"].get("alpha",0.93);av.configure(text=f"{int((1-ca)*100)}%")
        _asid=[None]
        def on_a(val):
            a=round(float(val),2);self.data["settings"]["alpha"]=a;self.root.attributes("-alpha",a);av.configure(text=f"{int((1-a)*100)}%")
            if _asid[0]:win.after_cancel(_asid[0])
            _asid[0]=win.after(400,lambda:save_data(self.data))
        asc=tk.Scale(f,from_=0.3,to=1.0,resolution=0.01,orient="horizontal",command=on_a,bg=S["bg"],fg=S["text"],troughcolor=S["bg3"],highlightthickness=0,bd=0,showvalue=False,sliderlength=14,width=6)
        asc.set(ca);asc.pack(fill="x",padx=16,pady=(0,6))
        aor=tk.Frame(f,bg=S["bg"]);aor.pack(fill="x",padx=16,pady=4);slbl(aor,"Always on top").pack(side="left")
        aov=tk.BooleanVar(value=self.data["settings"].get("always_on_top",True))
        aol=tk.Label(aor,bg=S["bg"],font=(FONT,9,"bold"),cursor="hand2",width=4);aol.pack(side="right")
        def raot():aol.configure(text="ON" if aov.get() else "OFF",fg=S["accent"] if aov.get() else S["mute"])
        def taot(e=None):aov.set(not aov.get());self.data["settings"]["always_on_top"]=aov.get();self.root.attributes("-topmost",aov.get());save_data(self.data);raot()
        aol.bind("<Button-1>",taot);raot();sep()
        section("Global Hotkey");slbl(f,"Click Record, then press your combo.",mute=True).pack(anchor="w",padx=16,pady=(0,6))
        hkr=tk.Frame(f,bg=S["bg"]);hkr.pack(fill="x",padx=16);chk_=self.data["settings"].get("hotkey","ctrl+alt+g")
        hkd=tk.Label(hkr,text=chk_,bg=S["bg3"],fg=S["text"],font=(FONT,10),padx=10,pady=6,width=20,anchor="w");hkd.pack(side="left")
        rb=tk.Label(hkr,text="  Record  ",bg=S["accent"],fg="#fff",font=(FONT,9,"bold"),padx=6,pady=6,cursor="hand2");rb.pack(side="left",padx=(8,0))
        hks=slbl(f,"",mute=True);hks.pack(anchor="w",padx=16,pady=(4,0));self._recording=False;self._hk_parts=[]
        def okp(e):
            if not self._recording:return
            sym=e.keysym.lower();sym={"control_l":"ctrl","control_r":"ctrl","alt_l":"alt","alt_r":"alt","shift_l":"shift","shift_r":"shift","super_l":"win","super_r":"win"}.get(sym,sym)
            if sym not in self._hk_parts:self._hk_parts.append(sym);hkd.configure(text="+".join(self._hk_parts))
        def okr(e):
            if not self._recording:return
            if e.keysym.lower() in ("control_l","control_r","alt_l","alt_r","shift_l","shift_r","super_l","super_r"):return
            self._recording=False;win.unbind("<KeyPress>");win.unbind("<KeyRelease>");combo="+".join(self._hk_parts)
            self.data["settings"]["hotkey"]=combo;save_data(self.data);hkd.configure(text=combo);rb.configure(bg=S["accent"],text="  Record  ");hks.configure(text=f"✓ {combo}");self._register_hotkey()
        def srec(e=None):self._recording=True;self._hk_parts=[];rb.configure(bg="#c44444",text="● Rec");hkd.configure(text="...");win.bind("<KeyPress>",okp);win.bind("<KeyRelease>",okr)
        rb.bind("<Button-1>",srec);sep()
        section("Workspaces")
        wsc=tk.Frame(f,bg=S["bg"]);wsc.pack(fill="x",padx=16)
        def bws():
            for w in wsc.winfo_children():w.destroy()
            for key,ws in self.data["workspaces"].items():
                r=tk.Frame(wsc,bg=S["bg2"]);r.pack(fill="x",pady=2)
                ct=len([g for g in ws.get("goals",[]) if not g.get("done")])
                tk.Label(r,text=ws["name"],bg=S["bg2"],fg=S["text"],font=(FONT,9),anchor="w").pack(side="left",padx=10,pady=6,fill="x",expand=True)
                tk.Label(r,text=f"{ct}",bg=S["bg2"],fg=S["mute"],font=(FONT,7)).pack(side="left",padx=6)
                if key!="main":
                    dl=tk.Label(r,text="Delete",bg=S["bg2"],fg=S["danger"],font=(FONT,8),cursor="hand2");dl.pack(side="right",padx=10)
                    dl.bind("<Button-1>",lambda e,k=key:self._delete_workspace(k,bws))
        bws();self._settings_rebuild_ws=bws
        nwr=tk.Frame(f,bg=S["bg"]);nwr.pack(fill="x",padx=16,pady=(6,0));nwv=tk.StringVar()
        nwe=tk.Entry(nwr,textvariable=nwv,bg=S["input_bg"],fg=S["mute"],insertbackground=S["input_fg"],relief="flat",font=(FONT,9),width=18)
        nwe.pack(side="left",padx=(0,6),ipady=4);nwe.insert(0,"New workspace name")
        nwe.bind("<FocusIn>",lambda e:([nwe.delete(0,"end"),nwe.configure(fg=S["input_fg"])] if nwe.get()=="New workspace name" else None))
        nwe.bind("<FocusOut>",lambda e:([nwe.delete(0,"end"),nwe.insert(0,"New workspace name"),nwe.configure(fg=S["mute"])] if not nwe.get().strip() else None))
        def cws():
            name=nwv.get().strip()
            if not name or name=="New workspace name":return
            key=f"ws_{len(self.data['workspaces'])}_{name.lower().replace(' ','_')}";self.data["workspaces"][key]={"name":name,"goals":[]}
            self.data["active_tab"]=key;save_data(self.data);nwe.delete(0,"end");nwe.insert(0,"New workspace name");nwe.configure(fg=S["mute"])
            bws();self._refresh_tabs();self._render_all();self._sync_settings()
        nwe.bind("<Return>",lambda e:cws());cb=tk.Label(nwr,text=" Create ",bg=S["accent"],fg="#fff",font=(FONT,8,"bold"),padx=6,pady=4,cursor="hand2");cb.pack(side="left");cb.bind("<Button-1>",lambda e:cws())
        sep()
        section("App-Sensitive Workspaces");slbl(f,"Auto-switch workspace when an app gains focus.",mute=True).pack(anchor="w",padx=16,pady=(0,2))
        slbl(f,"You can type a process name or use Browse.",mute=True).pack(anchor="w",padx=16,pady=(0,6))
        asr=tk.Frame(f,bg=S["bg"]);asr.pack(fill="x",padx=16,pady=(0,8));slbl(asr,"Auto-show widget on app focus").pack(side="left")
        asv=tk.BooleanVar(value=self.data["settings"].get("auto_show",True))
        asl=tk.Label(asr,bg=S["bg"],font=(FONT,9,"bold"),cursor="hand2",width=4);asl.pack(side="right")
        def ras():asl.configure(text="ON" if asv.get() else "OFF",fg=S["accent"] if asv.get() else S["mute"])
        def tas(e=None):asv.set(not asv.get());self.data["settings"]["auto_show"]=asv.get();save_data(self.data);ras()
        asl.bind("<Button-1>",tas);ras()
        rc=tk.Frame(f,bg=S["bg"]);rc.pack(fill="x",padx=16);arc=tk.Frame(f,bg=S["bg"]);arc.pack(fill="x",padx=16)
        def brl():
            for w in rc.winfo_children():w.destroy()
            rules=self.data.get("app_rules",{})
            if not rules:tk.Label(rc,text="No rules yet.",bg=S["bg"],fg=S["mute"],font=(FONT,8)).pack(anchor="w",pady=2)
            else:
                for proc,wsk in list(rules.items()):
                    wsn=self.data["workspaces"].get(wsk,{}).get("name",wsk);r=tk.Frame(rc,bg=S["bg2"]);r.pack(fill="x",pady=2)
                    tk.Label(r,text=proc,bg=S["bg2"],fg=S["text"],font=(FONT,9,"bold"),width=16,anchor="w").pack(side="left",padx=8,pady=5)
                    tk.Label(r,text=f"→ {wsn}",bg=S["bg2"],fg=S["mute"],font=(FONT,8)).pack(side="left")
                    xb=tk.Label(r,text="×",bg=S["bg2"],fg=S["mute"],font=(FONT,11),cursor="hand2");xb.pack(side="right",padx=8)
                    xb.bind("<Button-1>",lambda e,p=proc:[self.data["app_rules"].pop(p,None),save_data(self.data),brl()])
            for w in arc.winfo_children():w.destroy()
            pv=tk.StringVar();wsn_map={v["name"]:k for k,v in self.data["workspaces"].items()};wv=tk.StringVar()
            if wsn_map:wv.set(list(wsn_map)[0])
            r1=tk.Frame(arc,bg=S["bg"]);r1.pack(fill="x",pady=2)
            tk.Label(r1,text="Process:",bg=S["bg"],fg=S["mute"],font=(FONT,8),width=10,anchor="w").pack(side="left")
            pe=tk.Entry(r1,textvariable=pv,bg=S["input_bg"],fg=S["input_fg"],insertbackground=S["input_fg"],relief="flat",font=(FONT,9),width=14)
            pe.pack(side="left",padx=(4,0))
            def _browse_procs():
                if not HAS_WIN32: return
                procs = set()
                try:
                    def enum_cb(hwnd, _):
                        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                procs.add(psutil.Process(pid).name().lower())
                            except Exception: pass
                    win32gui.EnumWindows(enum_cb, None)
                except Exception: pass
                if not procs: return
                pick = tk.Toplevel(win); pick.title("Pick Process"); pick.configure(bg=S["bg"])
                pick.geometry("280x350"); pick.attributes("-topmost", True); pick.resizable(False, False)
                tk.Label(pick, text="Running processes with windows:", bg=S["bg"], fg=S["mute"], font=(FONT, 8)).pack(padx=10, pady=(10,4))
                sf = ScrollFrame(pick, bg=S["bg"]); sf.pack(fill="both", expand=True, padx=6, pady=6)
                for p in sorted(procs):
                    pb = tk.Label(sf.inner, text=p, bg=S["bg2"], fg=S["text"], font=(FONT, 9), anchor="w", padx=10, pady=6, cursor="hand2")
                    pb.pack(fill="x", pady=1)
                    pb.bind("<Enter>", lambda e, b=pb: b.configure(bg=S["bg3"]))
                    pb.bind("<Leave>", lambda e, b=pb: b.configure(bg=S["bg2"]))
                    pb.bind("<Button-1>", lambda e, name=p: [pv.set(name), pick.destroy()])
            bbtn = tk.Label(r1, text=" Browse ", bg=S["accent"], fg="#fff", font=(FONT, 7, "bold"), padx=4, pady=2, cursor="hand2")
            bbtn.pack(side="left", padx=(4,0)); bbtn.bind("<Button-1>", lambda e: _browse_procs())
            r2=tk.Frame(arc,bg=S["bg"]);r2.pack(fill="x",pady=2)
            tk.Label(r2,text="Workspace:",bg=S["bg"],fg=S["mute"],font=(FONT,8),width=10,anchor="w").pack(side="left")
            wo=list(wsn_map.keys()) if wsn_map else ["Today"];om=tk.OptionMenu(r2,wv,*wo)
            om.configure(bg=S["input_bg"],fg=S["input_fg"],activebackground=S["bg3"],relief="flat",font=(FONT,9),bd=0);om.pack(side="left",padx=(4,0))
            def addrl():
                p=pv.get().strip();wk=wsn_map.get(wv.get())
                if p and wk:self.data.setdefault("app_rules",{})[p]=wk;save_data(self.data);pv.set("");brl()
            arb=tk.Label(arc,text="  Add Rule  ",bg=S["accent"],fg="#fff",font=(FONT,8,"bold"),padx=10,pady=4,cursor="hand2");arb.pack(anchor="e",pady=6);arb.bind("<Button-1>",lambda e:addrl())
        brl();self._settings_rebuild_rules=brl;sep()
        section("Phone Sync");slbl(f,"Access goals from any device on same network.",mute=True).pack(anchor="w",padx=16,pady=(0,6))
        sv=tk.BooleanVar(value=self.data["settings"].get("sync_enabled",False))
        sr_=tk.Frame(f,bg=S["bg"]);sr_.pack(fill="x",padx=16,pady=4);slbl(sr_,"Enable sync server").pack(side="left")
        sl=tk.Label(sr_,bg=S["bg"],font=(FONT,9,"bold"),cursor="hand2",width=4);sl.pack(side="right")
        pv_=tk.IntVar(value=self.data["settings"].get("sync_port",7842));ips=get_local_ip()
        ul=tk.Label(f,bg=S["bg2"],fg=S["accent"],font=(FONT,10),padx=12,pady=8);ul.pack(fill="x",padx=16,pady=(4,2))
        def rsu():sl.configure(text="ON" if sv.get() else "OFF",fg=S["accent"] if sv.get() else S["mute"]);ul.configure(text=f"http://{ips}:{pv_.get()}" if sv.get() else "Server off")
        def tsync(e=None):
            sv.set(not sv.get());self.data["settings"]["sync_enabled"]=sv.get();save_data(self.data)
            if sv.get():self._start_sync_server()
            else:self._stop_sync_server()
            rsu()
        sl.bind("<Button-1>",tsync);rsu()
        pr=tk.Frame(f,bg=S["bg"]);pr.pack(fill="x",padx=16,pady=(2,0));slbl(pr,"Port",mute=True).pack(side="left")
        pe2=tk.Entry(pr,textvariable=pv_,bg=S["input_bg"],fg=S["input_fg"],insertbackground=S["input_fg"],relief="flat",font=(FONT,9),width=8);pe2.pack(side="left",padx=(8,0))
        def ap(e=None):
            try:p=int(pv_.get());assert 1024<=p<=65535;self.data["settings"]["sync_port"]=p;save_data(self.data)
            except:pv_.set(self.data["settings"].get("sync_port",7842))
            if sv.get():self._stop_sync_server();self._start_sync_server()
            rsu()
        pe2.bind("<Return>",ap);pe2.bind("<FocusOut>",ap);tk.Frame(f,bg=S["bg"],height=30).pack()

    def _sync_settings(self):
        if not(self.settings_win and self.settings_win.winfo_exists()):return
        for fn in(self._settings_rebuild_ws,self._settings_rebuild_rules):
            if fn:
                try:fn()
                except Exception:pass
    def _set_theme(self,name):
        self.data["settings"]["theme"]=name;save_data(self.data)
        if self.settings_win and self.settings_win.winfo_exists():self.settings_win.destroy();self.settings_win=None
        self._full_redraw();self.root.after(80,self._open_settings)
    def _register_hotkey(self):
        if not HAS_HOTKEY:return
        try:
            if self._hotkey_id is not None:keyboard.remove_hotkey(self._hotkey_id);self._hotkey_id=None
        except Exception:pass
        combo=self.data["settings"].get("hotkey","ctrl+alt+g")
        try:self._hotkey_id=keyboard.add_hotkey(combo,lambda:self.root.after(0,self._toggle_visibility))
        except Exception as e:log_error(f"hotkey fail ({combo}): {e}")
    def _app_watch_loop(self):
        try:_own=psutil.Process(os.getpid()).name().lower()
        except Exception:_own="python.exe"
        while True:
            if not self.data.get("app_rules"):time.sleep(5);continue
            try:
                hwnd=win32gui.GetForegroundWindow();_,pid=win32process.GetWindowThreadProcessId(hwnd);proc=psutil.Process(pid).name().lower()
                if proc==_own:time.sleep(1.5);continue
                if proc!=self._prev_focused_proc:
                    self._prev_focused_proc=proc
                    for pat,wk in list(self.data.get("app_rules",{}).items()):
                        if pat.lower() in proc:
                            if wk!=self.data["active_tab"] and wk in self.data["workspaces"]:
                                self._user_hidden=False;self.data["active_tab"]=wk;self._app_switch_queue.put(("switch",wk))
                            elif not self.visible and not self._user_hidden and self.data["settings"].get("auto_show",True):
                                self._app_switch_queue.put(("show",None))
                            break
            except Exception:pass
            time.sleep(1.5)
    def _poll_app_switch_queue(self):
        try:
            while True:
                ev,wk=self._app_switch_queue.get_nowait()
                if ev=="switch":self._on_app_switch(wk)
                elif ev=="show":self.root.deiconify();self.visible=True
        except queue.Empty:pass
        self.root.after(200,self._poll_app_switch_queue)
    def _on_app_switch(self,wk):
        wsn=self.data["workspaces"].get(wk,{}).get("name","");self.app_badge.configure(text=f"● {wsn}")
        self._refresh_tabs();self._render_all();save_data(self.data)
        if self.data["settings"].get("auto_show",True) and not self.visible and not self._user_hidden:self.root.deiconify();self.visible=True
    def _delete_workspace(self,key,rebuild_fn=None):
        if key=="main":return
        if messagebox.askyesno("Delete",f"Delete '{self.data['workspaces'][key]['name']}'?",parent=self.settings_win or self.root):
            del self.data["workspaces"][key]
            if self.data["active_tab"]==key:self.data["active_tab"]="main"
            save_data(self.data)
            if rebuild_fn:rebuild_fn()
            self._refresh_tabs();self._render_all()
    def _rename_workspace(self,key):
        ws=self.data["workspaces"].get(key)
        if not ws:return
        nn=simpledialog.askstring("Rename","New name:",initialvalue=ws["name"],parent=self.root)
        if nn and nn.strip():ws["name"]=nn.strip();save_data(self.data);self._refresh_tabs();self._render_all();self._sync_settings()
    def _tab_context_menu(self,event,key):
        t=self.T;m=tk.Menu(self.root,tearoff=0,bg=t["bg_header"],fg=t["text"],font=(FONT,9))
        m.add_command(label="Rename",command=lambda:self._rename_workspace(key))
        if key!="main":m.add_separator();m.add_command(label="Delete",command=lambda:self._delete_workspace(key))
        try:m.tk_popup(event.x_root,event.y_root)
        finally:m.grab_release()
    def _start_sync_server(self):
        if self._sync_server:return
        try:
            port=self.data["settings"].get("sync_port",7842);MobileHandler.app=self
            self._sync_server=ServerClass(("0.0.0.0",port),MobileHandler);threading.Thread(target=self._sync_server.serve_forever,daemon=True).start()
        except Exception as e:log_error(f"sync fail: {e}");self._sync_server=None
    def _stop_sync_server(self):
        if self._sync_server:
            try:self._sync_server.shutdown()
            except Exception:pass
            self._sync_server=None
    def _setup_tray(self):
        if not HAS_TRAY:return
        sz=64;img=Image.new("RGBA",(sz,sz),(0,0,0,0));d=ImageDraw.Draw(img)
        try:d.rounded_rectangle([4,4,60,60],radius=12,fill=(18,18,18,240),outline=(70,70,70),width=2)
        except:d.rectangle([4,4,60,60],fill=(18,18,18,240),outline=(70,70,70),width=2)
        for y_,w_ in[(20,36),(30,28),(40,20)]:d.line([13,y_,13+w_,y_],fill=(180,180,180),width=2)
        d.ellipse([10,16,17,23],fill=(90,220,90));hk=self.data["settings"].get("hotkey","ctrl+alt+g")
        menu=pystray.Menu(pystray.MenuItem("Show / Hide",lambda*_:self.root.after(0,self._toggle_visibility),default=True),
            pystray.MenuItem("Settings",lambda*_:self.root.after(0,self._open_settings)),pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",lambda*_:self.root.after(0,self._quit)))
        self.tray=pystray.Icon("Aside",img,f"Aside  ({hk})",menu);threading.Thread(target=self.tray.run,daemon=True).start()
    def _quit(self):
        self._save_position();self._stop_sync_server()
        if self._share_win and self._share_win.alive:
            try:self._share_win._cleanup()
            except Exception:pass
        if HAS_TRAY:
            try:self.tray.stop()
            except Exception:pass
        self.root.destroy()
    def run(self):self.root.mainloop()

# ── File Share Panel ──────────────────────────────────────────────────────────
import http.client as _http_client
from tkinter import filedialog as _filedialog
P={"bg":"#111318","bg2":"#1a1d24","bg3":"#22262f","border":"#2a2f3a","text":"#dde2ec","mute":"#6b7280","accent":"#4f8ef7","green":"#3ecf6e","red":"#e05555","bar_bg":"#1e2230","bar_fg":"#4f8ef7","send_fg":"#3ecf6e","recv_fg":"#c97bf7"}
def _fmt_size(n):
    for u in("B","KB","MB","GB"):
        if n<1024:return f"{n:.1f} {u}"
        n/=1024
    return f"{n:.1f} TB"
class _TransferRow:
    def __init__(self,parent,tid,fn,total,peer,inc):
        self.tid=tid;self.total=total;self.received=0;self.done=False;self._last_b=0;self._last_t=time.time();self._speed=0.0
        dc=P["recv_fg"] if inc else P["send_fg"];ar="↓" if inc else "↑"
        self.frame=tk.Frame(parent,bg=P["bg2"]);self.frame.pack(fill="x",pady=(0,2))
        top=tk.Frame(self.frame,bg=P["bg2"]);top.pack(fill="x",padx=12,pady=(8,2))
        tk.Label(top,text=ar,bg=P["bg2"],fg=dc,font=("Segoe UI",11,"bold"),width=2).pack(side="left")
        tk.Label(top,text=fn,bg=P["bg2"],fg=P["text"],font=("Segoe UI",9,"bold"),anchor="w").pack(side="left",fill="x",expand=True)
        self.pct=tk.Label(top,text="0%",bg=P["bg2"],fg=P["mute"],font=("Segoe UI",8));self.pct.pack(side="right")
        bf=tk.Frame(self.frame,bg=P["bg2"]);bf.pack(fill="x",padx=12,pady=(2,4))
        self.bar=tk.Canvas(bf,height=5,bg=P["bar_bg"],highlightthickness=0,bd=0);self.bar.pack(fill="x",side="left",expand=True)
        bot=tk.Frame(self.frame,bg=P["bg2"]);bot.pack(fill="x",padx=12,pady=(0,6))
        tk.Label(bot,text=peer,bg=P["bg2"],fg=P["mute"],font=("Segoe UI",7)).pack(side="left")
        self.spd=tk.Label(bot,text="",bg=P["bg2"],fg=P["mute"],font=("Segoe UI",7));self.spd.pack(side="right")
        tk.Frame(self.frame,bg=P["border"],height=1).pack(fill="x")
    def update(self,rcv,total=None):
        if total:self.total=total
        self.received=rcv;now=time.time();dt=now-self._last_t
        if dt>=0.4:self._speed=(rcv-self._last_b)/dt;self._last_b=rcv;self._last_t=now
        pct=(rcv/self.total*100) if self.total else 0;self.pct.configure(text=f"{pct:.0f}%");self.spd.configure(text=_fmt_size(self._speed)+"/s")
        self.bar.update_idletasks();w=self.bar.winfo_width() or 200;self.bar.delete("all")
        fl=int(w*pct/100)
        if fl>0:self.bar.create_rectangle(0,0,fl,5,fill=P["bar_fg"],outline="")
    def mark_done(self,ok=True):
        self.done=True;c=P["green"] if ok else P["red"];self.pct.configure(text="Done" if ok else "Failed",fg=c);self.spd.configure(text="")
        self.bar.delete("all");w=self.bar.winfo_width() or 200;self.bar.create_rectangle(0,0,w,5,fill=c,outline="")

class FileSharePanel:
    def __init__(self,app):
        self.app=app;self.alive=True;self._peers={};self._transfers={};self._server=None
        self._build_window();self._start_server()
        threading.Thread(target=self._discover_loop,daemon=True).start();threading.Thread(target=self._announce_loop,daemon=True).start();self._poll_peers()
    def _build_window(self):
        self.win=tk.Toplevel(self.app.root);self.win.title("Share");self.win.configure(bg=P["bg"]);self.win.geometry("420x560")
        self.win.resizable(False,False);self.win.attributes("-topmost",True);self.win.overrideredirect(True);self.win.protocol("WM_DELETE_WINDOW",self._close)
        mx=self.app.root.winfo_x();my=self.app.root.winfo_y();self.win.geometry(f"420x560+{mx-430}+{my}")
        hdr=tk.Frame(self.win,bg=P["bg3"],height=44,cursor="fleur");hdr.pack(fill="x");hdr.pack_propagate(False)
        hdr.bind("<ButtonPress-1>",self._ds);hdr.bind("<B1-Motion>",self._dm);self._dx=self._dy=0
        tk.Label(hdr,text="⇄",bg=P["bg3"],fg=P["accent"],font=("Segoe UI",14)).pack(side="left",padx=(14,6))
        tk.Label(hdr,text="File Share",bg=P["bg3"],fg=P["text"],font=("Segoe UI",11,"bold")).pack(side="left")
        self._sd=tk.Label(hdr,text="●",bg=P["bg3"],fg=P["mute"],font=("Segoe UI",9));self._sd.pack(side="left",padx=(8,0))
        self._sl=tk.Label(hdr,text="Starting...",bg=P["bg3"],fg=P["mute"],font=("Segoe UI",8));self._sl.pack(side="left",padx=(3,0))
        cb=tk.Label(hdr,text="×",bg=P["bg3"],fg=P["mute"],font=("Segoe UI",16),cursor="hand2");cb.pack(side="right",padx=10);cb.bind("<Button-1>",lambda e:self._close())
        tk.Frame(self.win,bg=P["border"],height=1).pack(fill="x");body=tk.Frame(self.win,bg=P["bg"]);body.pack(fill="both",expand=True)
        self._sec(body,"NEARBY DEVICES")
        if not self.app.data["settings"].get("sync_enabled",False):tk.Label(body,text="⚠️ Sync OFF",bg=P["bg"],fg=P["red"],font=("Segoe UI",8,"bold")).pack(anchor="w",padx=12,pady=(0,6))
        self._pf=tk.Frame(body,bg=P["bg"]);self._pf.pack(fill="x",padx=12,pady=(0,4))
        tk.Label(self._pf,text="Scanning...",bg=P["bg"],fg=P["mute"],font=("Segoe UI",9)).pack(anchor="w",pady=6)
        mr=tk.Frame(body,bg=P["bg"]);mr.pack(fill="x",padx=12,pady=(4,8));tk.Label(mr,text="Add IP:",bg=P["bg"],fg=P["mute"],font=("Segoe UI",8)).pack(side="left")
        self._miv=tk.StringVar();me=tk.Entry(mr,textvariable=self._miv,bg=P["bg3"],fg=P["text"],insertbackground=P["text"],relief="flat",font=("Segoe UI",9),width=16)
        me.pack(side="left",padx=(6,4));me.insert(0,"192.168.x.x");me.bind("<FocusIn>",lambda e:me.delete(0,"end") if me.get()=="192.168.x.x" else None)
        ab=tk.Label(mr,text=" Add ",bg=P["accent"],fg="#fff",font=("Segoe UI",8,"bold"),padx=6,pady=3,cursor="hand2");ab.pack(side="left");ab.bind("<Button-1>",lambda e:self._amp(self._miv.get().strip()))
        tk.Frame(body,bg=P["border"],height=1).pack(fill="x",padx=12);self._sec(body,"TRANSFERS")
        outer=tk.Frame(body,bg=P["bg"]);outer.pack(fill="both",expand=True,padx=12)
        canvas=tk.Canvas(outer,bg=P["bg"],bd=0,highlightthickness=0);vsb=tk.Scrollbar(outer,orient="vertical",command=canvas.yview,width=4)
        self._ti=tk.Frame(canvas,bg=P["bg"]);twi=canvas.create_window((0,0),window=self._ti,anchor="nw");canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left",fill="both",expand=True);vsb.pack(side="right",fill="y")
        self._ti.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")));canvas.bind("<Configure>",lambda e:canvas.itemconfig(twi,width=e.width))
        self._ntl=tk.Label(self._ti,text="No transfers",bg=P["bg"],fg=P["mute"],font=("Segoe UI",9));self._ntl.pack(anchor="w",pady=10)
    def _sec(self,p,t):
        r=tk.Frame(p,bg=P["bg"]);r.pack(fill="x",padx=12,pady=(10,4));tk.Label(r,text=t,bg=P["bg"],fg=P["accent"],font=("Segoe UI",7,"bold")).pack(side="left")
        tk.Frame(r,bg=P["border"],height=1).pack(side="left",fill="x",expand=True,padx=(8,0))
    def _ds(self,e):self._dx=e.x_root-self.win.winfo_x();self._dy=e.y_root-self.win.winfo_y()
    def _dm(self,e):self.win.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")
    def _announce_loop(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1);sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        msg=json.dumps({"dg":True,"name":DEVICE_NAME,"port":SHARE_PORT}).encode()
        while self.alive:
            try:sock.sendto(msg,("255.255.255.255",DISCOVER_PORT))
            except:pass
            time.sleep(4)
        sock.close()
    def _discover_loop(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.settimeout(2)
        try:sock.bind(("0.0.0.0",DISCOVER_PORT))
        except:self.app.root.after(0,lambda:(self._sd.configure(fg=P["red"]),self._sl.configure(text=f"UDP {DISCOVER_PORT} blocked")));return
        while self.alive:
            try:
                data,addr=sock.recvfrom(512);pkt=json.loads(data.decode())
                if pkt.get("dg") and pkt.get("name")!=DEVICE_NAME:self._peers[pkt["name"]]={"ip":addr[0],"port":pkt.get("port",SHARE_PORT),"ts":time.time()}
            except:pass
        sock.close()
    def _poll_peers(self):
        if not self.alive:return
        now=time.time();self._peers={n:p for n,p in self._peers.items() if now-p["ts"]<12}
        MobileHandler._connected_ips={ip:i for ip,i in MobileHandler._connected_ips.items() if now-i["ts"]<15};self._rpu();self.app.root.after(3000,self._poll_peers)
    def _rpu(self):
        for w in self._pf.winfo_children():w.destroy()
        sp=self.app.data["settings"].get("sync_port",7842)
        if self.app._sync_server:
            for ip,info in MobileHandler._connected_ips.items():
                nm=info.get("name",f"Browser ({ip})")
                if nm not in self._peers:self._peers[nm]={"ip":ip,"port":sp,"mobile":True,"ts":time.time()}
        if not self._peers:
            tk.Label(self._pf,text="No devices found.",bg=P["bg"],fg=P["mute"],font=("Segoe UI",9)).pack(anchor="w",pady=6);self._sd.configure(fg=P["mute"]);self._sl.configure(text="Scanning…")
        else:
            n=len(self._peers);self._sd.configure(fg=P["green"]);self._sl.configure(text=f"{n} device{'s' if n>1 else ''}")
            for nm,info in self._peers.items():self._pr(nm,info)
    def _pr(self,name,info):
        r=tk.Frame(self._pf,bg=P["bg2"]);r.pack(fill="x",pady=2);tk.Label(r,text="●",bg=P["bg2"],fg=P["green"],font=("Segoe UI",8)).pack(side="left",padx=(10,4),pady=8)
        tk.Label(r,text=name,bg=P["bg2"],fg=P["text"],font=("Segoe UI",9,"bold")).pack(side="left");tk.Label(r,text=info["ip"],bg=P["bg2"],fg=P["mute"],font=("Segoe UI",7)).pack(side="left",padx=(6,0))
        sb=tk.Label(r,text="  Send  ",bg=P["accent"],fg="#fff",font=("Segoe UI",8,"bold"),padx=6,pady=4,cursor="hand2");sb.pack(side="right",padx=10,pady=6)
        sb.bind("<Button-1>",lambda e,ip=info["ip"],p=info["port"]:self._pas(ip,p,name))
    def _amp(self,ip):
        if not ip or ip=="192.168.x.x":return
        def probe():
            try:c=_http_client.HTTPConnection(ip,SHARE_PORT,timeout=4);c.request("GET","/ping");r=c.getresponse();nm=json.loads(r.read()).get("name",ip);c.close()
            except:nm=ip
            self._peers[nm]={"ip":ip,"port":SHARE_PORT,"ts":time.time()};self.app.root.after(0,self._rpu)
        threading.Thread(target=probe,daemon=True).start()
    def _pas(self,ip,port,pn):
        path=_filedialog.askopenfilename(parent=self.win,title=f"Send to {pn}")
        if path:self._sf(path,ip,port,pn)
    def _sf(self,fp,ip,port,pn):
        if not os.path.isfile(fp):return
        fn=os.path.basename(fp);fs=os.path.getsize(fp);tid=f"s_{time.time():.3f}";mob=self._peers.get(pn,{}).get("mobile",False)
        row=_TransferRow(self._ti,tid,fn,fs,pn,inc=False);self._transfers[tid]=row;self._ntl.pack_forget()
        if mob:
            def dp():
                try:MobileHandler.push_file(fp);self.app.root.after(0,lambda:(row.update(fs),row.mark_done(True)))
                except Exception as ex:log_error(f"push fail: {ex}");self.app.root.after(0,lambda:row.mark_done(False))
            threading.Thread(target=dp,daemon=True).start();return
        def ds():
            try:
                sent=[0];conn=_http_client.HTTPConnection(ip,port,timeout=60)
                class PR:
                    def __init__(s,f):s._f=f
                    def read(s,n=65536):d=s._f.read(n);sent[0]+=len(d);self.app.root.after(0,lambda b=sent[0]:row.update(b));return d
                with open(fp,"rb") as f:
                    conn.request("POST","/receive",body=PR(f),headers={"Content-Length":fs,"Content-Type":"application/octet-stream","X-Filename":fn,"X-Sender":DEVICE_NAME})
                    ok=(conn.getresponse().status==200);conn.close()
                self.app.root.after(0,lambda:row.mark_done(ok))
            except Exception as ex:log_error(f"send fail: {ex}");self.app.root.after(0,lambda:row.mark_done(False))
        threading.Thread(target=ds,daemon=True).start()
    def _start_server(self):
        panel=self
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                if self.path=="/ping":b=json.dumps({"name":DEVICE_NAME}).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",len(b));self.end_headers();self.wfile.write(b)
                else:self.send_response(404);self.end_headers()
            def do_POST(self):
                if self.path!="/receive":self.send_response(404);self.end_headers();return
                fn=self.headers.get("X-Filename","file");sender=self.headers.get("X-Sender",self.client_address[0]);total=int(self.headers.get("Content-Length",0))
                tid=f"r_{time.time():.3f}";sn=os.path.basename(fn)
                if not panel.app._ask_accept_file(sn,sender):self.send_response(403);self.end_headers();return
                dd=os.path.join(os.path.expanduser("~"),"Downloads");os.makedirs(dd,exist_ok=True);dest=os.path.join(dd,sn)
                b,ext=os.path.splitext(sn);c=1
                while os.path.exists(dest):dest=os.path.join(dd,f"{b}_{c}{ext}");c+=1
                panel.app.root.after(0,lambda:panel._add_recv_row(tid,sn,total,sender))
                rcv=0;_lt=0.0
                try:
                    with open(dest,"wb") as f:
                        while rcv<total:
                            d=self.rfile.read(min(65536,total-rcv))
                            if not d:break
                            f.write(d);rcv+=len(d);_n=time.time()
                            if _n-_lt>=0.1:_lt=_n;panel.app.root.after(0,lambda b=rcv:panel._update_recv(tid,b,total))
                    panel.app.root.after(0,lambda:panel._finish_recv(tid,True,dest));self.send_response(200)
                except Exception as ex:log_error(f"recv fail: {ex}");panel.app.root.after(0,lambda:panel._finish_recv(tid,False,None));self.send_response(500)
                self.end_headers()
        try:self._server=ServerClass(("0.0.0.0",SHARE_PORT),H);threading.Thread(target=self._server.serve_forever,daemon=True).start();self._sl.configure(text="Ready · "+get_local_ip());self._sd.configure(fg=P["accent"])
        except Exception as e:log_error(f"share fail: {e}");self._sl.configure(text=f"Port {SHARE_PORT} busy");self._sd.configure(fg=P["red"])
    def _add_recv_row(self,tid,fn,total,sender):self._ntl.pack_forget();self._transfers[tid]=_TransferRow(self._ti,tid,fn,total,sender,inc=True)
    def _update_recv(self,tid,rcv,total):
        if tid in self._transfers:self._transfers[tid].update(rcv,total)
    def _finish_recv(self,tid,ok,dest):
        if tid in self._transfers:self._transfers[tid].mark_done(ok)
        if ok and dest:self._sl.configure(text=f"Got: {os.path.basename(dest)}",fg=P["green"]);self.app.root.after(4000,lambda:self._sl.configure(text="Ready · "+get_local_ip(),fg=P["mute"]))
    def _cleanup(self):
        self.alive=False
        if self._server:
            try:self. _server.shutdown()
            except:pass
    def _close(self):
        self._cleanup()
        try:self.win.destroy()
        except:pass

if __name__=="__main__":
    try:Aside().run()
    except Exception:log_error(traceback.format_exc());raise
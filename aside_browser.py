import os
import time
import json
import socket
import urllib.parse as _up
from http.server import BaseHTTPRequestHandler

# --- OPTIMIZED HTML/JS ---
MOBILE_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aside</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d0d0d;color:#d0d0d0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px 20px;gap:12px}
#drop-zone{width:100%;max-width:400px;border:2px dashed #2a2f3a;border-radius:18px;padding:44px 24px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
#drop-zone.hover,#drop-zone.has-files{border-color:#4f8ef7;background:#0a0f1a;border-style:solid}
#drop-zone p{font-size:15px;color:#888;margin-top:6px;font-size:13px}
#file-pick{display:none}
#send-btn{width:100%;max-width:400px;background:#4f8ef7;color:#fff;border:none;padding:15px;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;display:none}
#send-btn:disabled{opacity:.4;cursor:default}
#progress-wrap{width:100%;max-width:400px;display:none;flex-direction:column;gap:6px}
.p-row{background:#141414;border-radius:10px;padding:10px 14px}
.p-name{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:6px}
.p-track{height:3px;background:#222;border-radius:2px;overflow:hidden}
.p-bar{height:100%;width:0;background:#4f8ef7;border-radius:2px;transition:width .1s}
.p-status{font-size:11px;margin-top:4px;color:#555}
#from-host{width:100%;max-width:400px;display:none;flex-direction:column;gap:6px}
.divider{width:100%;max-width:400px;height:1px;background:#1a1a1a}
.f-row{display:flex;align-items:center;background:#141414;border-radius:10px;padding:10px 14px;gap:10px}
.f-name{flex:1;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.f-save{background:#3ecf6e;color:#000;text-decoration:none;font-size:11px;font-weight:700;padding:5px 14px;border-radius:7px;flex-shrink:0}
</style></head>
<body>

<div id="drop-zone" onclick="document.getElementById('file-pick').click()">
  <div style="font-size:32px;margin-bottom:8px">&#8679;</div>
  <div style="font-size:15px;font-weight:600">Send files to host</div>
  <p>Tap to choose &nbsp;·&nbsp; or drop here</p>
  <input type="file" id="file-pick" multiple onchange="pick(this.files)">
</div>

<button id="send-btn" onclick="sendAll()">Send</button>
<div id="progress-wrap"></div>
<div class="divider" id="divider" style="display:none"></div>
<div id="from-host"></div>

<script>
let queue=[], sending=false, uid=0, fileTimer, lastFileListJson = "";

const dz=document.getElementById('drop-zone');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('hover')});
dz.addEventListener('dragleave',()=>dz.classList.remove('hover'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('hover');pick(e.dataTransfer.files)});

function pick(files){
  if(sending) return;
  for(const f of files) queue.push({f,id:'u'+(uid++)});
  document.getElementById('file-pick').value='';
  renderQueueState();
}

function renderQueueState() {
  const n=queue.length;
  const btn=document.getElementById('send-btn');
  if(n > 0) {
    dz.classList.add('has-files');
    dz.querySelector('div:nth-child(2)').textContent=n+' file'+(n>1?'s':'')+' ready';
    btn.style.display='block';
    btn.disabled=false;
    btn.textContent=n>1?'Send '+n+' Files':'Send File';
  } else {
    dz.classList.remove('has-files');
    dz.querySelector('div:nth-child(2)').textContent='Send files to host';
    btn.style.display='none';
  }
}

async function sendAll(){
  if(sending||!queue.length)return;
  sending=true;
  const btn=document.getElementById('send-btn');
  btn.disabled=true;
  const wrap=document.getElementById('progress-wrap');
  wrap.style.display='flex';
  wrap.innerHTML='';
  
  for(const item of queue){
    const d=document.createElement('div');
    d.className='p-row'; d.id=item.id;
    d.innerHTML=`<div class="p-name">${esc(item.f.name)}</div><div class="p-track"><div class="p-bar" id="${item.id}b"></div></div><div class="p-status" id="${item.id}s">Waiting…</div>`;
    wrap.appendChild(d);
  }

  for(const item of queue) await upload(item);

  setTimeout(()=>{
    queue=[]; sending=false;
    wrap.style.display='none';
    renderQueueState();
  },2500);
}

function upload(item){
  return new Promise(res=>{
    const bar=document.getElementById(item.id+'b'), st=document.getElementById(item.id+'s');
    st.style.color='#4f8ef7'; st.textContent='Sending…';
    const xhr=new XMLHttpRequest();
    xhr.open('POST','/api/upload');
    xhr.setRequestHeader('X-Filename',encodeURIComponent(item.f.name));
    xhr.upload.onprogress=e=>{if(e.lengthComputable)bar.style.width=(e.loaded/e.total*100)+'%'};
    xhr.onload=()=>{
      const ok=xhr.status===200;
      bar.style.width='100%'; bar.style.background=ok?'#3ecf6e':'#e05555';
      st.style.color=ok?'#3ecf6e':'#e05555';
      st.textContent=ok?'✓ Sent':xhr.status===403?'✗ Declined':'✗ Failed';
      res();
    };
    xhr.onerror=()=>{st.style.color='#e05555';st.textContent='✗ Lost';res()};
    xhr.send(item.f);
  });
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

async function pollFiles(){
  try{
    const r=await fetch('/api/files'); if(!r.ok)return;
    const d=await r.json();
    const currentJson = JSON.stringify(d.files);
    if(currentJson === lastFileListJson) return; // FIX: No flickering if list is same
    lastFileListJson = currentJson;

    const el=document.getElementById('from-host'), dv=document.getElementById('divider');
    if(!d.files||!d.files.length){el.style.display='none';dv.style.display='none';return;}
    el.style.display='flex'; dv.style.display='block';
    el.innerHTML=d.files.map(f=>`<div class="f-row"><span class="f-name">${esc(f)}</span><a class="f-save" href="/api/download/${encodeURIComponent(f)}" download="${esc(f)}">Save</a></div>`).join('');
  }catch(e){}
}

document.addEventListener('visibilitychange',()=>{
  if(document.hidden)clearInterval(fileTimer);
  else{pollFiles();fileTimer=setInterval(pollFiles,3000);}
});
pollFiles(); fileTimer=setInterval(pollFiles,3000);
</script>
</body></html>"""


class MobileHandler(BaseHTTPRequestHandler):
    app = None
    _pending = {}
    _connected_ips = {}
    _dns_cache = {} # FIX: Speed up loading by caching DNS lookups

    @classmethod
    def push_file(cls, fp):
        now = time.time()
        cls._pending = {k: v for k, v in cls._pending.items() if now - v.get("ts", now) < 600}
        fn = os.path.basename(fp)
        key = fn
        c = 1
        while key in cls._pending:
            b, e = os.path.splitext(fn)
            key = f"{b}_{c}{e}"
            c += 1
        cls._pending[key] = {"path": fp, "ts": now}
        return key

    def log_message(self, *a): pass

    def get_peer_name(self, ip):
        if ip in self._dns_cache:
            return self._dns_cache[ip]
        try:
            # Short timeout lookup to prevent page hang
            n = socket.gethostbyaddr(ip)[0]
            n = n.split('.')[0] if n.endswith(('.local', '.lan')) else n
            self._dns_cache[ip] = n
            return n
        except Exception:
            return f"Browser ({ip})"

    def do_GET(self):
        ip = self.client_address[0]
        if ip not in MobileHandler._connected_ips:
            n = self.get_peer_name(ip)
            MobileHandler._connected_ips[ip] = {"ts": time.time(), "name": n}
        else:
            MobileHandler._connected_ips[ip]["ts"] = time.time()

        if self.path == "/api/files":
            now = time.time()
            MobileHandler._pending = {k: v for k, v in MobileHandler._pending.items() if now - v.get("ts", now) < 600}
            self._json(200, {"files": list(MobileHandler._pending.keys())})

        elif self.path.startswith("/api/download/"):
            key = _up.unquote(self.path[len("/api/download/"):])
            entry = MobileHandler._pending.get(key)
            if not entry:
                self.send_response(404); self.end_headers(); return
            
            fp = entry["path"] if isinstance(entry, dict) else entry
            if not fp or not os.path.isfile(fp):
                self.send_response(404); self.end_headers(); return
            
            sz = os.path.getsize(fp)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{key}"')
            self.send_header("Content-Length", sz)
            self.end_headers()
            with open(fp, "rb") as f:
                while True:
                    ch = f.read(1024*128) # Increased buffer for faster local transfer
                    if not ch: break
                    self.wfile.write(ch)
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
        else:
            self._json(404, {"error": "not found"})

    def do_POST_upload(self):
        try:
            fn = _up.unquote(self.headers.get("X-Filename", "upload"))
        except Exception:
            fn = self.headers.get("X-Filename", "upload")

        total = int(self.headers.get("Content-Length", 0))
        sn = os.path.basename(fn) or "upload"
        sip = self.client_address[0]
        sender = MobileHandler._connected_ips.get(sip, {}).get("name", sip)

        # FIX: Even if declined, we MUST read the stream to prevent connection hanging
        if not self.app._ask_accept_file(sn, sender):
            # Drain the body
            remaining = total
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk: break
                remaining -= len(chunk)
            self._json(403, {"error": "Declined"})
            return

        dd = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(dd, exist_ok=True)
        dest = os.path.join(dd, sn)
        b, e = os.path.splitext(sn)
        c = 1
        while os.path.exists(dest):
            dest = os.path.join(dd, f"{b}_{c}{e}")
            c += 1

        tid = f"m_{time.time():.3f}"
        panel = self.app._share_win if self.app._share_win and self.app._share_win.alive else None

        if panel:
            self.app.root.after(0, lambda: panel._add_recv_row(tid, sn, total, f"📱 {sender}"))

        try:
            rcv = 0
            _lt = 0.0
            with open(dest, "wb") as f:
                while rcv < total:
                    # Increased buffer to 128KB for better speed
                    ch = self.rfile.read(min(128*1024, total - rcv))
                    if not ch: break
                    f.write(ch)
                    rcv += len(ch)
                    if panel:
                        _n = time.time()
                        if _n - _lt >= 0.1:
                            _lt = _n
                            b2 = rcv
                            self.app.root.after(0, lambda b2=b2: panel._update_recv(tid, b2, total))
            
            if panel:
                self.app.root.after(0, lambda: panel._finish_recv(tid, True, dest))
            else:
                self.app.root.after(0, lambda: self.app._flash_share_btn(sn))
            self._json(200, {"ok": True})
        except Exception as ex:
            self.app.log_error(f"upload fail: {ex}")
            if panel:
                self.app.root.after(0, lambda: panel._finish_recv(tid, False, None))
            self._json(500, {"error": str(ex)})

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
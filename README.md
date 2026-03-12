# DeskGoals

A lightweight, always-on-screen goal tracker that lives on your Windows desktop. No browser, no accounts — just a clean floating widget to keep your goals, media, and file transfers in view.

---

## Quick Start (First Time Setup)

To get DeskGoals running at its absolute fullest with all features enabled, follow these steps exactly:

1. **Install Python:** Download Python 3.8+ from [python.org](https://www.python.org/downloads/). 
   * *CRITICAL:* During the installation wizard, you **must** check the box that says **"Add Python to PATH"** before clicking Install.
2. **Install Dependencies:** Right-click `install.bat` and select **"Run as administrator"**. This downloads the required libraries and automatically configures your Windows Firewall so phone syncing and file sharing will work.
3. **Create Shortcuts:** Double-click `setup_windows.bat`. This automatically adds DeskGoals to your Windows startup folder so it launches seamlessly when you log in.
4. **Launch:** Run `start.bat` to open the app silently!
5. **bring forward**(ctrl + alt + g ) or (tap in tray menu)
---

## Running

| File | What it does |
|---|---|
| `start.bat` | Launches the app silently (no console window) |
| `debug.bat` | Launches with a console — use this if the app won't open to see error codes |
| `setup_windows.bat` | Registers startup + Start Menu shortcuts |

---

## Features

### Goals & Workspaces
- Add text goals by typing in the bottom bar and pressing Enter.
- Mark goals done by clicking the circle — they move to the Completed tray.
- Delete any item with the × button.
- Create multiple **workspaces** (tabs) to separate contexts (e.g., work, personal, a specific project).
- Completed goals are kept per workspace for **24 hours**, then automatically cleared from the list.

### Files, Media, and Notes
DeskGoals allows you to attach context directly to your tasks:
- **Drag and Drop:** Drag images, PDFs, or files directly onto the DeskGoals window.
- **Paste Screenshots:** Hit `Ctrl+V` to paste an image directly from your clipboard.
- **Manual Attach:** Click the `+` button to browse your PC for files to attach.
- Whenever you add a file, you will be prompted to add an optional text description to it. 
- *Note:* DeskGoals creates a physical copy of attached files in your `~/.deskgoals_media` folder. Deleting the card in the app removes it from your list, but the file remains safely on your hard drive.

### P2P File Sharing
Click the `⇄` icon in the top right to open the File Share panel:
- **PC-to-PC & PC-to-Phone:** Instantly send files between devices on the same Wi-Fi network. 
- **Respectful Receiving:** DeskGoals will never force a file onto your computer. You will always get a pop-up prompting you to "Accept" or "Decline" incoming files.
- Accepted files are automatically saved to your standard Windows `Downloads` folder.

### App-Sensitive Workspaces
- Automatically switch to a workspace when a specific app gains focus!
- If DeskGoals is hidden when the matched app opens, it **auto-shows** on screen.
- Set rules in **Settings → App-Sensitive Workspaces** (e.g., set `chrome.exe` to trigger your "Browsing" workspace).

### Phone Sync (Local Wi-Fi)
Access and edit goals from your phone (or another PC's browser) while on the same Wi-Fi network:
1. Open **Settings → Phone Sync**
2. Toggle the server **ON**
3. Open the URL shown (e.g. `http://192.168.1.x:7842`) in your phone or browser.

From the web page, you can switch workspaces, check off goals, add new ones, and even upload/download files to the host PC. 

### Appearance & Controls
- **Themes:** 4 built-in themes (Dark, Slate, Warm, Light) with adjustable transparency.
- **Always-on-top:** Toggleable in settings.
- **Global Hotkey:** Default is `Ctrl+Alt+G` to instantly show/hide the widget from anywhere. (Customizable in Settings).
- **System Tray:** DeskGoals lives quietly in your system tray (bottom-right of taskbar). Right-click it to Show/Hide, open Settings, or Quit.

---

## Troubleshooting

**App doesn't open at all** Run `debug.bat` — errors print in the console and are saved to `%USERPROFILE%\deskgoals_error.log`.

**`install.bat` shows errors** Make sure Python is installed and that you checked the "Add to PATH" box during installation.

**Drag and Drop isn't working** Run `install.bat` again to ensure `tkinterdnd2` was installed properly. 

**Phone Sync or Share Panel isn't finding devices** Both devices must be on the same Wi-Fi network. Right-click `install.bat` and "Run as administrator" to ensure the firewall rules are properly applied. 

---

## Data & Storage

Your data is kept strictly local. Nothing is sent to the cloud.

* **Settings and Goals:** `%USERPROFILE%\.deskgoals_v3.json`
* **Media and Pasted Files:** `%USERPROFILE%\.deskgoals_media`

---

## Uninstall

1. Close DeskGoals (right-click the tray icon → Quit)
2. Delete the downloaded DeskGoals folder
3. Delete the startup shortcut: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeskGoals.lnk`
4. Delete your saved data and media 
   * `%USERPROFILE%\.deskgoals_v3.json`
   * `%USERPROFILE%\.deskgoals_media`



or right click the unistall and run as admin - this removes all dependancies and firewall rules that were installed.
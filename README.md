leave me a comment --- https://form.jotform.com/260813575104150


# Aside

Your notes should follow your focus. Aside is a floating notepad that switches context the moment you do.

---

## Setup

1. Install **Python 3.8+** from [python.org](https://www.python.org/downloads/) — check **"Add Python to PATH"** during install.
2. Right-click `install.bat` → **Run as administrator**
3. Double-click `setup_windows.bat` to add Aside to Windows startup
4. Run `start.bat` to launch
5. **Ctrl+Alt+G** or the tray icon to show/hide

---

## App-Sensitive Workspaces

This is the core feature. Go to **Settings → App Switching**, assign a workspace to an `.exe`, and Aside takes it from there.

```
figma.exe      → "Design"    your open questions, feedback notes, ref links
code.exe       → "Dev"       the current task, bugs, PR checklist
slack.exe      → "Comms"     people to follow up with
premiere.exe   → "Edit"      cut notes, client feedback, export checklist
```

When that app comes into focus, Aside switches to the matched workspace — and if Aside was hidden, it auto-shows on screen. When you're done and switch away, it follows you to the next context.

Each workspace is completely isolated: its own goals, attached files, and notes.

---

## Everything Else

**Goals** — Type in the bottom bar, press Enter. Click the circle to complete. Completed goals are visible in the tray at the bottom and are cleared automatically after 24 hours.

**Headers** — Organize goals inside a workspace with small or large section headers. Click the `¶` button at the left of the input bar to cycle between goal / small header / large header mode.

**Attach anything** — Drag files onto the window, paste a screenshot with Ctrl+V, or click `+` to browse. Add an optional note to any attachment. Files are copied to `~/.aside_media` and removed from disk when you delete the card.

**Links** — Paste a URL into a goal and it becomes clickable. Works in the desktop app and on phone.

**Workspaces** — Add as many as you like with the `＋` tab or Ctrl+T. Right-click a tab to rename, delete, or set a color. Switch by clicking or with Ctrl+1–9.

**Phone / browser access** — Settings → Sync → toggle on. Open the URL shown on any device on the same Wi-Fi. You can add goals, check things off, and send files to the host PC.

**P2P file sharing** — Click `⇄` to open the Share panel. Send to any device on the same network. Incoming files always prompt Accept/Decline and land in your Downloads folder.

**Appearance** — 4 themes (Dark, Slate, Warm, Light), adjustable transparency, always-on-top toggle, and a dim-when-unfocused option. Hotkey is customizable in Settings. Resize the widget with the `75%/100%/125%/150%` button in the header.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| App won't open | Run `debug.bat` — errors log to `~/aside_error.log` |
| Install errors | Confirm Python installed with "Add to PATH" checked |
| Drag & Drop broken | Re-run `install.bat` to reinstall `tkinterdnd2` |
| App-Sensitive rules not triggering | Requires `pywin32` + `psutil` — re-run `install.bat` |
| Phone Sync / Share not finding devices | Both devices must be on the same Wi-Fi; re-run `install.bat` as admin |

---

## Data

Everything stays local. Nothing is sent to the cloud.

- **Settings & Goals:** `%USERPROFILE%\.aside.json`
- **Attached Files:** `%USERPROFILE%\.aside_media`

---

## Uninstall

1. Right-click tray icon → Quit
2. Right-click `uninstall.bat` → **Run as administrator**

The uninstaller stops the app, removes Python dependencies, clears firewall rules, removes the startup shortcut, and optionally deletes your saved data and the program folder.

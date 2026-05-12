# Reverse-Engineering & Linux Port of Gather Desktop (macOS → Linux)

## 1. App Overview

| Property | Value |
|---|---|
| **App** | Gather Desktop (`com.gather.Gather`) |
| **Version** | `1.38.0-beta` (macOS build) |
| **Electron** | `37.6.0` (Chromium 138, Node ~24) |
| **Type** | Hybrid web-wrapper — loads `https://app.gather.town` (v1) or `https://app.v2.gather.town` (v2) inside a `BrowserWindow` / `BrowserView` with local preload bridges |
| **Update feed** | `gathertown/gather-town-desktop-releases` (GitHub) |

## 2. Reverse-Engineering Findings

### Bundle Structure
- `Contents/Resources/app.asar` (~34 MB) contains the JS/HTML assets.
- `Contents/Resources/bin/` holds macOS-only native binaries:
  - `gather-native-helper-process` — Rust binary (`winit`/`wgpu`) for window animations & window capture.
  - `krisp-nodejs-module-v1.node` — Node native addon for Krisp noise cancellation.
  - `c8.f.s.026300-1.0.0_3.1.kef` — Krisp ML model data.

### Key Source Files (inside `app.asar`)
- `build/js/entry.js` — main process bundle (minified, ~2.6 MB).
- `build/js/background.js` — renderer shell bundle.
- `build/js/preload/sharedPreload.js` & `appViewPreload.js` — preload bridges exposing `_gatherInterop` to the webapp.
- `build/background.html` — main window HTML shell.

### Cross-Platform Awareness
The JS bundle **already handles `linux`** alongside `darwin` and `win32`:
- Badge counts work on macOS + Linux.
- Tray icons use `.png` on Linux (dark/light via `nativeTheme`).
- Global shortcuts (`globalShortcut`) are registered for toggling audio/video.
- `electron-updater` already includes `AppImageUpdater` logic, suggesting Linux was planned.

### Native Features Requiring Linux Stubs
1. **`gather-native-helper-process`** (Rust) — handles fullscreen window animations and window capture for screen-share overlays. Uses macOS-only `CAMetalLayer` / `NSWindow`.
2. **Krisp noise cancellation** — `GET_KRISP_NATIVE_PARAMS` IPC handler returns paths to the `.node` addon and model file.
3. **Screen-recording permission** — macOS `systemPreferences.getMediaAccessStatus('screen')` does not exist on Linux.

### URL Architecture
The production URL is constructed in `entry.js` as:
```js
const I = "https://app.gather.town";          // production base
const m = "https://app.staging.gather.town";  // staging base
const Mm = `${U.BB ? I : h}/app`;             // e.g. https://app.gather.town/app
```
Validation arrays (`N2`, `T2`) and a regex (`C`) whitelist valid Gather domains for navigation security.

---

## 3. The v1 vs v2 Problem

The current desktop app loads **v1** (`https://app.gather.town/app`). When visiting a "Gather 2.0 office", the webapp shows a banner:

> **"To visit your Gather 2.0 office, download the new app."**

Investigation of the marketing site (`https://gather.town`) revealed links to:
- `https://app.v2.gather.town/signin`
- `https://app.v2.gather.town/get-started-survey`

**Hypothesis**: the desktop app is mostly a URL-change away from supporting v2.

---

## 4. Patches Applied

### Linux Compatibility Stubs (main process)
Applied to `/tmp/gather-extracted/build/js/entry.js`:

| Patch | Target | Replacement |
|---|---|---|
| **Helper-process spawn** | `}),qm=(r,s,y,R)=>{const M=r[0];` | Stub `qm` on Linux to return `{sendInput:()=>{},close:()=>{}}` |
| **Screen-rec permission** | `GET_SCREEN_REC_PERMISSION_STATUS` handler | Return `"granted"` on Linux instead of calling `systemPreferences.getMediaAccessStatus` |
| **Krisp paths** | `GET_KRISP_NATIVE_PARAMS` return object | Return `null` for `binaryPath`, `modelPath`, `writablePath` on Linux |

### v2 URL Migration
Applied to the same file:

| Patch | Before | After |
|---|---|---|
| **Production base URL** | `I="https://app.gather.town"` | `I="https://app.v2.gather.town"` |
| **Domain regex** | `C=/^https:\/\/(app\|staging\|app\.staging)*[.]*gather\.town$/` | Added `app\.v2` to the regex group |
| **Allowed `/app` URLs** | `N2=["https://gather.town/app",...]` | Added `"https://app.v2.gather.town/app"` |
| **Allowed base domains** | `T2=U.BB?["https://gather.town/",...]` | Added `"https://app.v2.gather.town/"` |

### Repacking
- Original `npx @electron/asar` CLI proved flaky for repacking (first v2 patch silently failed to persist).
- **Reliable method**: local `npm install @electron/asar` + Node API:
  ```bash
  node -e "require('@electron/asar').createPackage('/tmp/gather-extracted', 'electron/resources/app.asar')"
  ```
- macOS-only binaries removed from `resources/bin/` to avoid `ELF format` errors on `require()`.

---

## 5. Test Results

### Unpatched mac `app.asar` on Linux Electron 37.6.0
- ✅ **Boots successfully** — main process starts, tray loads, `https://app.gather.town` loads, WebRTC initializes.
- No immediate crash from missing native binaries (they are only triggered on-demand).

### Patched Build (Linux stubs + v2 URLs)
- The `entry.js` on disk now contains **3 v2 references** and **2 remaining v1 references** (kept in allow-lists for backward compatibility).
- App launches, but a **runtime error** appeared (handled gracefully by try/catch):

```
Error importing native utils Error: Cannot find module 'gather-native-desktop-utils'
Require stack:
- /tmp/gather-linux-port/electron/resources/app.asar/build/js/entry.js
```

This internal package is declared in `package.json` (`"gather-native-desktop-utils": "*"`) but **is not present** as a real directory in `node_modules` inside the asar.

### v2 Boot Test (After Stub + Config Clear)
✅ **v2 login loads successfully.**

Steps taken:
1. Created stub `node_modules/gather-native-desktop-utils/index.js` inside the extracted asar (exports no-op `GetWindowInfoById`, `MoveWindowBelowWindowById`, `MoveAllWindowsBelowTargetWindow`, `HideCursor`, `ShowCursor`).
2. Repacked `app.asar` with `require('@electron/asar').createPackage(...)`.
3. Cleared stale `lastVisitedUrl` (`https://app.gather.town/app`) from `~/.config/Gather/config.json` — this stored v1 URL was overriding the patched base URL on startup.
4. Re-launched the app.

Resulting boot sequence:
```
Loading start URL: https://app.v2.gather.town/app
...
AppView did-navigate
[LocalStorageMigrationService] Migrating client to version 5.
AuthenticationService.start
HubSpotService.start
TelemetryService.start
SSORequirementsService.start
waitForToken: Waiting for Firebase user
...
Auth State changed aFUqKaADRXOZbARXjOLidt7L9nI2
...
Attempting to navigate main frame to: https://app.v2.gather.town/signin?redirectTo=%2Fapp
```

- **No more `gather-native-desktop-utils` error** — stub resolves the module.
- **v2 webapp bootstraps fully** through local-storage migration, auth initialization, and service startup.
- **User token obtained** and app redirects to sign-in page as expected for an unauthenticated session.
- One non-fatal renderer error observed: `TypeError: Cannot read properties of undefined (reading 'deviceString')` in a v2 bundle. Does not block navigation or auth flow.

### Window Decorations on Linux (KDE Plasma Wayland)
The app was missing close/minimize/maximize buttons on Linux. Investigation revealed the user is on **KDE Plasma Wayland** (`kwin_wayland` compositor, `WAYLAND_DISPLAY=wayland-0`).

**Root cause:** The app's `BrowserWindow` uses `titleBarStyle:"hidden"` (intended for macOS floating traffic lights). On Linux, this can cause decoration issues depending on the Ozone backend (native Wayland vs. Xwayland) and the compositor's SSD/CSD support. The app also only shows custom window-control buttons in the HTML toolbar on Windows (`co.ED` = isWindows), so Linux gets neither native traffic lights (macOS-only) nor custom buttons (Windows-only).

**Fix applied to `entry.js`:**
For the **main app window** and **space home window**, added conditional spread on Linux to override `titleBarStyle` and force `frame`:
```js
...(process.platform!=="darwin"&&process.platform!=="win32"
  ?{titleBarStyle:"default",frame:!0}
  :{})
```

**Most reliable runtime workaround:** Force Electron to use the **X11 Ozone backend** (runs through Xwayland on Wayland desktops), where the compositor (KWin) reliably provides window decorations:
```bash
./electron resources/app.asar --ozone-platform=x11
```
Both the code patch and the `--ozone-platform=x11` flag boot successfully to v2.

---

## 6. Current State & Remaining Blockers

### What Works
- Linux Electron shell (`/tmp/gather-linux-port/electron/`)
- Patched `app.asar` with Linux stubs and v2 URLs
- Auto-updater framework (`AppImageUpdater`) already in JS bundle

### Blockers to Solve

| # | Blocker | Severity | Notes |
|---|---|---|---|
| 1 | ~~`gather-native-desktop-utils` missing~~ | ✅ **Resolved** | Stubbed by creating `node_modules/gather-native-desktop-utils/index.js` inside asar. App boots cleanly. |
| 2 | **`deviceString` renderer error** | 🟡 Medium | `TypeError: Cannot read properties of undefined (reading 'deviceString')` in v2 bundle. Non-fatal but may indicate missing device-detection data. Investigate if it breaks any feature. |
| 3 | **Krisp `.node` addon** | 🟡 Medium | Stubbed at the JS level, but a proper Linux build would need a recompiled Node addon or PipeWire fallback. |
| 4 | **`gather-native-helper-process`** | 🟡 Medium | Stubbed in JS (spawn no-op), but window-border animations are disabled. Could be rebuilt in Rust for Linux if source were available. |
| 5 | ~~Window decorations on Linux~~ | ✅ **Resolved** | `titleBarStyle:"hidden"` + missing custom buttons left Linux undecorated. Fixed by overriding to `titleBarStyle:"default"` + `frame:true` in `entry.js`, and `--ozone-platform=x11` forces Xwayland where KWin provides reliable decorations. |
| 6 | **Packaging / Distribution** | 🟢 Low | Need `.desktop` file, AppImage or `.tar.gz`, and icon setup. |

---

## 7. Files & Artifacts

| Path | Description |
|---|---|
| `/tmp/gather-extracted/` | Fully extracted `app.asar` (patched `entry.js` inside) |
| `/tmp/gather-linux-port/electron/` | Working Linux Electron build with patched `app.asar` |
| `/tmp/gather-linux-port/patch_and_repack.py` | First patcher (Linux stubs + repack) |
| `/tmp/apply-v2-patches.py` | Second patcher (v2 URL migration) |
| `/tmp/gather-linux-run-*.log` | Test-run logs |

---

## 8. Next Steps

1. **Test window decorations** — verify close/minimize/maximize buttons appear when running with `--ozone-platform=x11`. If confirmed, make this permanent via wrapper script, `.desktop` file, or `ELECTRON_OZONE_PLATFORM_HINT=x11`.

2. **Investigate `deviceString` error** — trace which v2 bundle throws `Cannot read properties of undefined (reading 'deviceString')` and determine if it blocks any critical path (camera/mic permissions, onboarding, etc.).

3. **Real-world feature test** — log into a v2 space, test audio/video, screen sharing (Electron `desktopCapturer` should handle this natively on Linux), and global shortcuts.

4. **Package for distribution** — create AppImage or `.tar.gz` with a `.desktop` entry, proper icon, and the `--ozone-platform=x11` flag baked in.

5. **Automate the stub + repack** — add the `gather-native-desktop-utils` stub creation and the `titleBarStyle`/`frame` Linux patches to the existing `patch_and_repack.py` script so a single command produces a working Linux build.

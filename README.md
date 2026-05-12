# Gather Desktop — Linux Port

A community Linux port of the [Gather](https://gather.town) Desktop app, reverse-engineered from the official macOS build and patched to run natively on Linux.

> **Disclaimer**: This project is not affiliated with or endorsed by Gather. It is a personal/educational port of the official macOS Electron app for Linux users. You must obtain the original macOS app yourself from [gathertown/gather-town-desktop-releases](https://github.com/gathertown/gather-town-desktop-releases).

---

## What Works

| Feature | Status | Notes |
|---------|--------|-------|
| **Login / Authentication** | ✅ Working | v2 webapp loads and Firebase auth initializes |
| **WebRTC Audio/Video** | ✅ Working | Via Electron's built-in Chromium/WebRTC stack |
| **Screen Sharing** | ✅ Working | `desktopCapturer` works natively on Linux |
| **Global Shortcuts** | ✅ Working | Audio/video toggle shortcuts registered |
| **Tray Icon** | ✅ Working | PNG icons for Linux dark/light themes |
| **Badge Counts** | ✅ Working | Linux implementation already present in upstream JS |
| **Window Decorations** | ✅ Working | Patched for proper close/min/max buttons on Linux |
| **Window Animations** | ⚠️ Disabled | `gather-native-helper-process` is macOS-only |
| **Krisp Noise Cancellation** | ⚠️ Disabled | macOS `.node` addon; stubbed gracefully |

---

## Dependencies

### Required

| Tool | Purpose |
|------|---------|
| **Node.js** ≥ 18 | For `@electron/asar` repacking tool |
| **npm** | Package manager |
| **Python 3** | Patch scripts |
| **Pillow** (Python) | Icon conversion (`pip install Pillow`) |
| **curl** | Download Electron runtime |
| **unzip** | Extract Electron archive |

### Optional

| Tool | Purpose |
|------|---------|
| `update-desktop-database` | Refresh desktop entry cache after install |

### Runtime Dependencies

The built app requires no system-wide runtime dependencies beyond what your desktop environment already provides for Electron/Chromium:

- GTK3 / libgtk-3-0
- NSS / libnss3
- X11 or Wayland (with Xwayland)
- libxss1, libasound2, libxtst6 (for screen sharing & audio)

On Fedora/RHEL:
```bash
sudo dnf install gtk3 nss alsa-lib libXScrnSaver libXtst
```

On Debian/Ubuntu:
```bash
sudo apt install libgtk-3-0 libnss3 libxss1 libasound2 libxtst6
```

---

## Quick Start

### 1. Obtain the macOS App

Download the official macOS `.app` bundle from the [gathertown/gather-town-desktop-releases](https://github.com/gathertown/gather-town-desktop-releases) repository. Place it at `~/Downloads/Gather.app` or set `GATHER_APP` to its path.

### 2. Build

```bash
git clone https://github.com/kidush/gather-linux-port.git
cd gather-linux-port

# Default: expects ~/Downloads/Gather.app
./scripts/build.sh

# Or specify the path:
# GATHER_APP=/path/to/Gather.app ./scripts/build.sh
```

This will:
1. Extract `app.asar` from the macOS bundle
2. Apply Linux compatibility stub patches
3. Migrate URLs from v1 to v2 (`app.gather.town` → `app.v2.gather.town`)
4. Fix window decorations for Linux
5. Create a stub for the missing `gather-native-desktop-utils` module
6. Download the matching Electron Linux runtime
7. Repack `app.asar` and place it into the Electron bundle

The build output goes to `build/electron/`.

### 3. Install

```bash
./scripts/install.sh
```

This copies the runtime to `/opt/applications/gather/` and installs a `.desktop` entry in `~/.local/share/applications/`.

### 4. Run

```bash
# If installed:
gather

# Or directly from build:
./build/electron/electron ./build/electron/resources/app.asar --ozone-platform=x11
```

> **Important**: Always use `--ozone-platform=x11` (or set `ELECTRON_OZONE_PLATFORM_HINT=x11`). This forces Electron to use the X11 backend (via Xwayland on Wayland desktops), which provides reliable window decorations on all compositors.

---

## What the Patches Do

### 1. Linux Compatibility Stubs (`scripts/apply-linux-stubs.py`)

The upstream JS bundle targets macOS, Windows, and (partially) Linux. Three macOS-specific features need stubbing:

| Feature | macOS Implementation | Linux Stub |
|---------|---------------------|------------|
| `gather-native-helper-process` | Rust binary with `winit`/`wgpu` for window animations | Returns `{sendInput: () => {}, close: () => {}}` |
| `GET_SCREEN_REC_PERMISSION_STATUS` | `systemPreferences.getMediaAccessStatus('screen')` | Returns `"granted"` (Linux doesn't have this macOS API) |
| `GET_KRISP_NATIVE_PARAMS` | Returns paths to `.node` addon + ML model | Returns `{binaryPath: null, modelPath: null, writablePath: null}` |

### 2. v2 URL Migration (`scripts/apply-v2-patches.py`)

The official desktop app loads v1 (`app.gather.town`). Gather 2.0 spaces require v2 (`app.v2.gather.town`). The patches update:

- Production base URL variable
- Navigation security regex
- Allowed `/app` URL whitelist
- Allowed base domain whitelist

### 3. Window Decoration Fix (`scripts/apply-window-fixes.py`)

The app uses `titleBarStyle: "hidden"` (macOS floating traffic lights). On Linux this can remove close/minimize/maximize buttons entirely. The patch adds a conditional spread to the **main app window** only:

```js
...(process.platform !== "darwin" && process.platform !== "win32"
  ? { titleBarStyle: "default", frame: true }
  : {})
```

Overlay/animation windows (transparent, `frame: false`) are intentionally skipped.

### 4. `gather-native-desktop-utils` Stub

An internal Node module referenced in `package.json` but not shipped as a real directory inside the asar. On Linux it causes:

```
Error: Cannot find module 'gather-native-desktop-desktop-utils'
```

We create a no-op stub at:
```
node_modules/gather-native-desktop-utils/index.js
```

---

## Project Structure

```
gather-linux-port/
├── scripts/
│   ├── build.sh                  # Main build orchestrator
│   ├── install.sh                # System install to /opt + .desktop
│   ├── apply-linux-stubs.py      # Linux compatibility patches
│   ├── apply-v2-patches.py       # URL migration to v2
│   └── apply-window-fixes.py     # Window decoration fix
├── bin/
│   └── gather-wrapper.sh         # Runtime wrapper (--ozone-platform=x11)
├── assets/
│   ├── gather.desktop            # Desktop entry template
│   └── icon.png                  # App icon (converted from .icns)
├── stubs/
│   └── gather-native-desktop-utils.js   # No-op module stub
├── build/                        # Build output (gitignored)
│   ├── work/                     # Extracted/patched app.asar
│   └── electron/                 # Final runnable Electron bundle
├── README.md
└── .gitignore
```

---

## Known Issues & Troubleshooting

### Window has no close/minimize/maximize buttons

**Cause**: Running on Wayland without the X11 Ozone backend.

**Fix**: The wrapper script and `.desktop` entry already pass `--ozone-platform=x11`. If running manually, always include this flag:

```bash
./electron resources/app.asar --ozone-platform=x11
```

Or set the environment variable globally:

```bash
export ELECTRON_OZONE_PLATFORM_HINT=x11
```

### `Cannot find module 'gather-native-desktop-utils'`

**Cause**: The stub was not created before repacking.

**Fix**: Ensure `build.sh` ran to completion. The stub is created at `build/work/extracted/node_modules/gather-native-desktop-utils/index.js` before repacking.

### App still loads v1 (`app.gather.town`) after patching

**Cause**: Stale `lastVisitedUrl` in Electron's config overrides the patched base URL.

**Fix**: Clear the stored URL:

```bash
rm -rf ~/.config/Gather
```

Then relaunch.

### `deviceString` renderer error in v2 bundle

A non-fatal `TypeError: Cannot read properties of undefined (reading 'deviceString')` appears in the v2 renderer. It does not block navigation, auth, or basic usage. It may affect some device-detection feature; investigate if you notice broken functionality.

---

## License

The **scripts, patches, and documentation** in this repository are provided as-is for educational and personal use. The Gather app itself, its assets, logos, and original JavaScript bundles are proprietary to Gather Presence, Inc. This repository does not redistribute Gather's proprietary code — it only documents the process of patching an app you already legally obtained.

---

## Acknowledgements

Reverse-engineering and patch analysis based on the official macOS Electron build `com.gather.Gather` v1.38.0-beta (Electron 37.6.0).

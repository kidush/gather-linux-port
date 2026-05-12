#!/usr/bin/env python3
"""
Apply window decoration fixes for Linux.
The app uses titleBarStyle:"hidden" (macOS floating traffic lights).
On Linux with Wayland, this can leave windows without close/minimize/maximize buttons.
We add conditional spreads to force default decorations on Linux main windows,
while intentionally skipping overlay/animation windows (transparent, frame:!1).
"""
import sys

def main():
    entry_js = sys.argv[1] if len(sys.argv) > 1 else 'build/js/entry.js'
    
    with open(entry_js, 'r', encoding='utf-8', errors='ignore') as f:
        data = f.read()
    
    print(f"Patching {entry_js} for Linux window decorations...")
    
    count = data.count('titleBarStyle:"hidden"')
    print(f"Found {count} occurrence(s) of titleBarStyle:'hidden'")
    
    patched = 0
    start = 0
    while True:
        idx = data.find('titleBarStyle:"hidden"', start)
        if idx == -1:
            break
        
        # Inspect context after this occurrence (120 chars)
        context = data[idx:idx+120]
        
        # Skip overlay windows: they intentionally have transparent:!0 and frame:!1
        # for borderless floating overlays. Changing their decorations would break them.
        if 'transparent:!0' in context and 'frame:!1' in context:
            print(f"  [SKIP] Overlay window at offset {idx} (transparent, frame:!1)")
            start = idx + 1
            continue
        
        # This is likely the main app window - add Linux decoration override.
        # The spread object with titleBarStyle:"default" and frame:!0 will
        # override the earlier hidden setting on Linux only.
        old = 'titleBarStyle:"hidden"'
        new = 'titleBarStyle:"hidden",...(process.platform!=="darwin"&&process.platform!=="win32"?{titleBarStyle:"default",frame:!0}:{})'
        
        # Replace only this specific occurrence
        data = data[:idx] + new + data[idx+len(old):]
        patched += 1
        print(f"  [OK] Patched main window at offset {idx}")
        
        # Advance past the replacement to avoid infinite loops
        start = idx + len(new)
    
    with open(entry_js, 'w', encoding='utf-8') as f:
        f.write(data)
    
    print(f"Patched {patched} main window(s). Overlay windows intentionally skipped.")

if __name__ == '__main__':
    main()

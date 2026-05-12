#!/usr/bin/env python3
"""
Apply Linux compatibility stub patches to Gather's entry.js.
These patches disable macOS-only native features that crash or error on Linux.
"""
import sys

def main():
    entry_js = sys.argv[1] if len(sys.argv) > 1 else 'build/js/entry.js'
    
    with open(entry_js, 'r', encoding='utf-8', errors='ignore') as f:
        data = f.read()
    
    print(f"Patching {entry_js} for Linux compatibility...")
    print(f"File size: {len(data)} bytes")
    
    # Patch 1: Helper process spawn - stub on Linux
    # The qm function spawns gather-native-helper-process (macOS Rust binary).
    # We stub it to return no-op handles on Linux.
    old1 = '}),qm=(r,s,y,R)=>{const M=r[0];'
    new1 = '}),qm=(r,s,y,R)=>{if(process.platform==="linux")return{sendInput:()=>{},close:()=>{}};const M=r[0];'
    if old1 in data:
        data = data.replace(old1, new1)
        print("  [OK] P1: Helper process stubbed for Linux")
    else:
        print("  [WARN] P1: Could not find helper-process pattern.")
        print("         Manual patching may be needed. Search for 'qm=(r,s,y,R)=>' in entry.js")
    
    # Patch 2: Screen recording permission - return "granted" on Linux
    # macOS systemPreferences.getMediaAccessStatus('screen') does not exist on Linux.
    # Electron's desktopCapturer works on Linux without this permission check.
    old2 = ';const y=a.systemPreferences.getMediaAccessStatus("screen");return nt.info("Screenshare permission status:",y),y}),a.ipcMain.handle("REQUEST_SCREEN_REC_PERMISSION"'
    new2 = ';return nt.info("Screenshare permission status: granted (Linux stub)"),"granted"}),a.ipcMain.handle("REQUEST_SCREEN_REC_PERMISSION"'
    if old2 in data:
        data = data.replace(old2, new2)
        print("  [OK] P2: Screen recording permission stubbed for Linux")
    else:
        idx = data.find('a.ipcMain.handle("GET_SCREEN_REC_PERMISSION_STATUS"')
        if idx != -1:
            print("  [WARN] P2: Found GET_SCREEN_REC_PERMISSION_STATUS but exact pattern mismatch.")
            print("         Manual patch: replace the handler body to return 'granted' on Linux.")
        else:
            print("  [WARN] P2: Could not find screen recording permission handler")
    
    # Patch 3: Krisp noise cancellation - null paths on Linux
    # The Krisp .node addon and model files are macOS-only binaries.
    # We stub the handler to return null paths so the app disables Krisp gracefully.
    idx = data.find('a.ipcMain.handle("GET_KRISP_NATIVE_PARAMS"')
    if idx != -1:
        # Find the return block within ~600 chars after the handler start
        window = data[idx:idx+900]
        # Look for the return statement pattern in the minified code
        # Typical pattern: return{binaryPath:H,modelPath:ie,writablePath:de}
        # We replace the entire return to return nulls on Linux
        import re
        # Try to match return{...} with the three Krisp paths
        krisp_return = re.search(r'return\{binaryPath:[^,]+,modelPath:[^,]+,writablePath:[^}]+\}', window)
        if krisp_return:
            old3 = krisp_return.group(0)
            # Build a conditional return that gives null on Linux
            new3 = 'return process.platform==="linux"?{binaryPath:null,modelPath:null,writablePath:null}:' + old3[len('return'):]
            data = data.replace(old3, new3, 1)
            print("  [OK] P3: Krisp paths stubbed for Linux")
        else:
            print("  [WARN] P3: Found GET_KRISP_NATIVE_PARAMS but could not match return pattern.")
            print("         Manual patch: ensure binaryPath, modelPath, writablePath return null on Linux.")
    else:
        print("  [WARN] P3: Could not find Krisp params handler")
    
    with open(entry_js, 'w', encoding='utf-8') as f:
        f.write(data)
    
    print("Linux stub patches applied.")

if __name__ == '__main__':
    main()

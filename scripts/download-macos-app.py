#!/usr/bin/env python3
"""
Download the latest macOS Gather Desktop release from GitHub and extract Gather.app.
Usage: download-macos-app.py [output_dir]
Prints the path to the extracted Gather.app on success.
"""
import json
import os
import sys
import urllib.request
import zipfile
import tempfile
import shutil

REPO = "gathertown/gather-town-desktop-releases"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads")
    os.makedirs(out_dir, exist_ok=True)

    print(f"Querying {API_URL} ...", file=sys.stderr)
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "gather-linux-port/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.reason}", file=sys.stderr)
        if e.code == 403:
            print("Rate limit may have been exceeded. Try again later or provide a GITHUB_TOKEN.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

    assets = [
        a
        for a in data.get("assets", [])
        if "mac" in a["name"].lower() and a["name"].endswith(".zip")
    ]

    if not assets:
        # Fallback: also check for .dmg and warn
        dmg_assets = [
            a
            for a in data.get("assets", [])
            if "mac" in a["name"].lower() and a["name"].endswith(".dmg")
        ]
        if dmg_assets:
            print(
                f"ERROR: Latest release only has a .dmg ({dmg_assets[0]['name']}). "
                "DMG extraction is not supported on Linux. Please download and extract manually.",
                file=sys.stderr,
            )
        else:
            print(
                "ERROR: No macOS .zip asset found in the latest release.",
                file=sys.stderr,
            )
        sys.exit(1)

    asset = assets[0]
    name = asset["name"]
    url = asset["browser_download_url"]
    zip_path = os.path.join(out_dir, name)

    # Skip download if already present
    if os.path.exists(zip_path):
        print(f"Using existing download: {zip_path}", file=sys.stderr)
    else:
        print(f"Downloading {name} ...", file=sys.stderr)
        urllib.request.urlretrieve(url, zip_path)
        print(f"Saved to {zip_path}", file=sys.stderr)

    # Extract
    extract_dir = tempfile.mkdtemp(prefix="gather-mac-")
    print(f"Extracting to {extract_dir} ...", file=sys.stderr)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # Find Gather.app
    for root, dirs, _files in os.walk(extract_dir):
        if "Gather.app" in dirs:
            app_path = os.path.join(root, "Gather.app")
            # Move to a stable location inside out_dir so we don't lose it on tmp cleanup
            stable_path = os.path.join(out_dir, "Gather.app")
            if os.path.exists(stable_path):
                shutil.rmtree(stable_path)
            shutil.move(app_path, stable_path)
            shutil.rmtree(extract_dir, ignore_errors=True)
            print(stable_path)
            return

    print("ERROR: Gather.app not found inside the downloaded archive.", file=sys.stderr)
    shutil.rmtree(extract_dir, ignore_errors=True)
    sys.exit(1)


if __name__ == "__main__":
    main()

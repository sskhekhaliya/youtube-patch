#!/usr/bin/env python3
"""
Android YouTube Auto-Patcher Engine
Automates the lifecycle of checking, downloading, and patching YouTube APKs
with ad-blocking, background playback, and Google login support.
"""

import os
import sys
import json
import shutil
import platform
import argparse
import subprocess
import urllib.request
import re
from pathlib import Path

# Repository configurations
CLI_REPO = "inotia00/revanced-cli"
PATCHES_REPO = "inotia00/revanced-patches"
APKEDITOR_REPO = "REAndroid/APKEditor"
APKEEP_REPO = "EFForg/apkeep"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def log(msg: str):
    print(f"\n[AutoPatcher] >>> {msg}", flush=True)

def error_exit(msg: str):
    print(f"\n[AutoPatcher ERROR] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)

def http_get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_file(url: str, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        return
    log(f"Downloading: {url} -> {dest_path.name}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, "wb") as f:
        shutil.copyfileobj(resp, f)

def get_latest_github_release(repo: str):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    return http_get_json(url)

def fetch_tools(tools_dir: Path):
    tools_dir.mkdir(parents=True, exist_ok=True)

    # 1. ReVanced CLI
    log("Checking latest ReVanced CLI...")
    cli_rel = get_latest_github_release(CLI_REPO)
    cli_asset = next(a for a in cli_rel["assets"] if a["name"].endswith(".jar"))
    cli_path = tools_dir / f"cli-{cli_rel['tag_name']}.jar"
    download_file(cli_asset["browser_download_url"], cli_path)

    # 2. ReVanced Patches (.rvp)
    log("Checking latest ReVanced Patches...")
    patches_rel = get_latest_github_release(PATCHES_REPO)
    patches_asset = next(a for a in patches_rel["assets"] if a["name"].endswith(".rvp"))
    patches_path = tools_dir / f"patches-{patches_rel['tag_name']}.rvp"
    download_file(patches_asset["browser_download_url"], patches_path)

    # 3. APKEditor
    log("Checking latest APKEditor...")
    apkeditor_rel = get_latest_github_release(APKEDITOR_REPO)
    apkeditor_asset = next(a for a in apkeditor_rel["assets"] if a["name"].endswith(".jar"))
    apkeditor_path = tools_dir / f"APKEditor-{apkeditor_rel['tag_name']}.jar"
    download_file(apkeditor_asset["browser_download_url"], apkeditor_path)

    # 4. apkeep
    log("Checking latest apkeep...")
    apkeep_rel = get_latest_github_release(APKEEP_REPO)
    os_name = platform.system().lower()
    if os_name == "windows":
        apkeep_name = "apkeep-x86_64-pc-windows-msvc.exe"
        target_name = "apkeep.exe"
    elif os_name == "linux":
        apkeep_name = "apkeep-x86_64-unknown-linux-gnu"
        target_name = "apkeep"
    else:
        error_exit(f"Unsupported OS: {os_name}")

    apkeep_asset = next(a for a in apkeep_rel["assets"] if a["name"] == apkeep_name)
    apkeep_path = tools_dir / target_name
    download_file(apkeep_asset["browser_download_url"], apkeep_path)
    if os_name != "windows":
        apkeep_path.chmod(0o755)

    return {
        "cli_path": cli_path,
        "patches_path": patches_path,
        "apkeditor_path": apkeditor_path,
        "apkeep_path": apkeep_path,
        "cli_version": cli_rel["tag_name"],
        "patches_version": patches_rel["tag_name"],
    }

def get_compatible_youtube_versions(cli_jar: Path, patches_rvp: Path) -> list:
    log("Detecting compatible YouTube versions from patch bundle...")
    cmd = ["java", "-jar", str(cli_jar), "list-versions", str(patches_rvp)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    lines = proc.stdout.splitlines()
    in_yt = False
    compatible_versions = []
    for line in lines:
        if "Package name: com.google.android.youtube" in line:
            in_yt = True
            continue
        if in_yt:
            if line.startswith("Package name:"):
                break
            m = re.search(r"(\d+\.\d+\.\d+)", line)
            if m:
                compatible_versions.append(m.group(1))

    log(f"Compatible YouTube versions in patch bundle: {compatible_versions}")
    return compatible_versions

def get_available_apkpure_versions(apkeep_bin: Path) -> list:
    log("Checking available YouTube versions on APKPure...")
    cmd = [str(apkeep_bin), "-a", "com.google.android.youtube", "-d", "apk-pure", "-l", "."]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    versions = []
    for line in proc.stdout.splitlines():
        if "|" in line or "," in line:
            parts = [p.strip() for p in line.replace("|", "").split(",") if p.strip()]
            for p in parts:
                m = re.match(r"^(\d+\.\d+\.\d+)$", p)
                if m:
                    versions.append(m.group(1))
    return versions

def select_best_version(compatible_versions: list, apkpure_versions: list, requested_version: str = None) -> str:
    if requested_version:
        log(f"Using user-specified target version: {requested_version}")
        return requested_version

    # Match versions available on APKPure that are in the patch bundle
    matched = [v for v in compatible_versions if v in apkpure_versions]
    if matched:
        # Pick the highest version
        best = matched[0]  # list-versions lists descending or top versions
        log(f"Selected best compatible version available on APKPure: {best}")
        return best

    if compatible_versions:
        fallback = compatible_versions[0]
        log(f"Warning: None of the compatible versions found in direct listing, attempting highest compatible: {fallback}")
        return fallback

    error_exit("No compatible YouTube version could be identified!")

def check_if_already_released(version: str) -> bool:
    github_repo = os.environ.get("GITHUB_REPOSITORY")
    if not github_repo:
        return False
    
    try:
        url = f"https://api.github.com/repos/{github_repo}/releases"
        releases = http_get_json(url)
        target_tag = f"v{version}"
        for r in releases:
            if r.get("tag_name") == target_tag:
                return True
    except Exception as e:
        log(f"Note: Could not check existing releases ({e}). Continuing build.")
    return False

def download_youtube_package(apkeep_bin: Path, version: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    log(f"Downloading YouTube APK/XAPK version {version}...")
    cmd = [
        str(apkeep_bin),
        "-a", f"com.google.android.youtube@{version}",
        "-d", "apk-pure",
        "-o", "acknowledge_dangers=true",
        str(dest_dir)
    ]
    subprocess.run(cmd, check=True)

    # Find downloaded file
    for item in dest_dir.iterdir():
        if item.name.startswith("com.google.android.youtube") and (item.suffix in [".xapk", ".apk"]):
            log(f"Found downloaded package: {item.name}")
            return item
    
    error_exit("Downloaded package not found in output directory!")

def merge_if_split(apkeditor_jar: Path, package_file: Path, output_stock_apk: Path) -> Path:
    if package_file.suffix == ".xapk":
        log("Downloaded file is split XAPK bundle. Merging into standalone APK with APKEditor...")
        cmd = [
            "java", "-jar", str(apkeditor_jar),
            "m",
            "-i", str(package_file),
            "-o", str(output_stock_apk)
        ]
        subprocess.run(cmd, check=True)
        return output_stock_apk
    else:
        return package_file

def run_patcher(cli_jar: Path, patches_rvp: Path, stock_apk: Path, keystore_path: Path, output_apk: Path):
    log("Running ReVanced CLI patch engine...")
    cmd = [
        "java", "-jar", str(cli_jar),
        "patch",
        "-p", str(patches_rvp),
        "-o", str(output_apk),
    ]

    if keystore_path.exists():
        log(f"Using persistent release keystore: {keystore_path}")
        cmd.extend(["--keystore", str(keystore_path)])
    else:
        log("No existing keystore specified; default keystore will be generated.")

    cmd.append(str(stock_apk))

    log(f"Executing: {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        error_exit(f"Patching failed with exit code {proc.returncode}")

    # If keystore was newly generated by CLI in current or output dir, copy it to persistent keystore path
    if not keystore_path.exists():
        keystore_candidate = output_apk.parent / f"{output_apk.stem}.keystore"
        if keystore_candidate.exists():
            keystore_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(keystore_candidate, keystore_path)
            log(f"Preserved newly generated keystore to: {keystore_path}")

    log(f"Successfully generated patched APK: {output_apk}")

def write_release_metadata(output_dir: Path, version: str, tools_meta: dict, apk_path: Path):
    notes = f"""# YouTube ReVanced Auto-Build (v{version})

Automated build produced by **Android YouTube Auto-Patcher**.

### 📦 Build Details
- **YouTube Base Version:** `{version}`
- **Patches Version:** `{tools_meta['patches_version']}`
- **CLI Version:** `{tools_meta['cli_version']}`
- **APK Filename:** `{apk_path.name}`
- **File Size:** `{round(apk_path.stat().st_size / (1024 * 1024), 2)} MB`

### ✨ Included Enhancements
- 🚫 **Full Ad-Blocking:** Blocks video ads, feed banners, sponsor overlays, and promo tiles.
- 🎵 **Background Playback:** Listen to videos with the screen turned off or in picture-in-picture.
- ⏩ **SponsorBlock:** Automatically skips sponsor segments, intros, and reminders.
- 👎 **Return YouTube Dislike:** Restores real-time dislike counts.
- 🔄 **Spoof App Version / Playback Fix:** Prevents video buffering loops and playback errors.
- 🔑 **GmsCore Support:** Enables full Google Account sign-in (via ReVanced GmsCore).
- 🔐 **Persistent Signing:** Every release uses the same signature, allowing direct in-place updates via Obtainium.

### 📱 Installation Instructions (Automatic via Obtainium)
1. Open **Obtainium** on your phone.
2. If already added, tap **Update**.
3. If setting up for the first time, add this repository URL into Obtainium and enable **Shizuku** for 100% silent background updates.
4. If you have not installed **ReVanced GmsCore** for Google login yet, download it [here](https://github.com/ReVanced/GmsCore/releases/latest).
"""
    notes_path = output_dir / "release_notes.md"
    notes_path.write_text(notes, encoding="utf-8")
    
    meta = {
        "youtube_version": version,
        "patches_version": tools_meta["patches_version"],
        "cli_version": tools_meta["cli_version"],
        "apk_filename": apk_path.name,
        "tag_name": f"v{version}",
    }
    meta_path = output_dir / "build_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    
    # Write GitHub Actions outputs if applicable
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"version={version}\n")
            f.write(f"tag_name=v{version}\n")
            f.write(f"apk_path={apk_path.resolve()}\n")
            f.write(f"release_notes={notes_path.resolve()}\n")
            f.write("should_release=true\n")

def main():
    parser = argparse.ArgumentParser(description="Android YouTube Auto-Patcher Engine")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if version was already released")
    parser.add_argument("--target-version", type=str, help="Specific YouTube version to build")
    parser.add_argument("--check-only", action="store_true", help="Only check for updates and exit")
    parser.add_argument("--keystore", type=str, default="keystore/release.keystore", help="Path to release keystore")
    parser.add_argument("--output-dir", type=str, default="build", help="Directory to output final APK")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    tools_dir = root_dir / "tools"
    temp_dir = root_dir / "temp_workspace"
    build_dir = root_dir / args.output_dir
    keystore_path = root_dir / args.keystore

    # Step 1: Download & verify build tools
    tools = fetch_tools(tools_dir)

    # Step 2: Determine target YouTube version
    compat_versions = get_compatible_youtube_versions(tools["cli_path"], tools["patches_path"])
    apkpure_versions = get_available_apkpure_versions(tools["apkeep_path"])
    target_version = select_best_version(compat_versions, apkpure_versions, args.target_version)

    log(f"Target YouTube version determined: {target_version}")

    # Step 3: Check if update is needed
    if not args.force and check_if_already_released(target_version):
        log(f"Version {target_version} is already built and released on GitHub. Nothing to do!")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("should_release=false\n")
        return

    if args.check_only:
        log(f"Check completed: Update available ({target_version}).")
        return

    # Step 4: Download base YouTube APK/XAPK
    download_dir = temp_dir / "download"
    downloaded_pkg = download_youtube_package(tools["apkeep_path"], target_version, download_dir)

    # Step 5: Merge splits if necessary
    merged_apk = temp_dir / f"youtube-{target_version}-merged.apk"
    stock_apk = merge_if_split(tools["apkeditor_path"], downloaded_pkg, merged_apk)

    # Step 6: Patch and sign
    build_dir.mkdir(parents=True, exist_ok=True)
    output_apk = build_dir / f"YouTube-v{target_version}-Patched.apk"
    run_patcher(tools["cli_path"], tools["patches_path"], stock_apk, keystore_path, output_apk)

    # Step 7: Generate metadata and release notes
    write_release_metadata(build_dir, target_version, tools, output_apk)

    # Clean up workspace
    shutil.rmtree(temp_dir, ignore_errors=True)
    log("Build process completed successfully!")

if __name__ == "__main__":
    main()

# 🚀 Android YouTube Auto-Patcher & Updater

An automated, hands-off cloud engine that monitors YouTube updates, applies supported ad-blocking and playback patches, and silently delivers updates to your Android phone via **Obtainium** and **Shizuku**.

---

## 🌟 How It Works

```
┌──────────────────────────────────────────────┐
│  GitHub Actions (Runs in Cloud Weekly)       │
│  - Checks latest patches & YouTube target ver│
│  - Downloads base YouTube APK                │
│  - Merges splits with APKEditor              │
│  - Applies adblock, SponsorBlock, & fixes    │
│  - Signs with persistent keystore            │
│  - Publishes GitHub Release                  │
└──────────────────────┬───────────────────────┘
                       │ (Background notification)
                       ▼
┌──────────────────────────────────────────────┐
│  Your Android Phone (Obtainium + Shizuku)    │
│  - Obtainium detects the new GitHub Release  │
│  - Downloads the APK automatically           │
│  - Shizuku performs silent background update │
│  - ✨ You always have the newest working app │
└──────────────────────────────────────────────┘
```

---

## 📋 What's Included

* 🚫 **Ad-Free Experience:** Removes all video ads, home feed banners, and promo tiles.
* 🎵 **Background Playback:** Keeps playing when your screen is locked or in picture-in-picture mode.
* ⏩ **SponsorBlock:** Automatically skips sponsor shoutouts, intros, and reminders.
* 👎 **Return YouTube Dislike:** Re-enables dislike counts in real time.
* 🔄 **Playback Buffering Fix:** Spoofs client version to prevent endless buffering issues.
* 🔑 **Google Account Login:** Seamless MicroG / GmsCore support.
* 🔐 **Persistent Signature:** Comes pre-configured with a permanent signing keystore (`keystore/release.keystore`) so you can update over existing installations without signature conflicts or losing settings.

---

## 🛠️ Step-by-Step Setup Guide

### 1. Push This Repository to GitHub

Create a new repository on your GitHub account (it can be **Public** or **Private**):

```bash
git add .
git commit -m "Initial commit: Android YouTube Auto-Patcher"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
```

> **Note:** If you make the repository **Private**, you can generate a [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` scope and provide it to Obtainium so it can check private releases.

---

### 2. Trigger Your First Build

1. Open your repository on GitHub in your browser.
2. Click on the **Actions** tab at the top.
3. On the left sidebar, click **Auto-Patch YouTube**.
4. Click **Run workflow** -> Select `main` branch -> Click the green **Run workflow** button.
5. In ~3 to 4 minutes, the job will finish and publish a ready-to-install APK in your repository's **Releases** tab.

*(Going forward, GitHub Actions will automatically run on schedule every Sunday at 04:00 UTC to check for updates).*

---

### 3. Setup on Your Android Phone

#### A. Install ReVanced GmsCore (One-Time Setup for Google Login)
1. Download and install **ReVanced GmsCore** on your phone:
   👉 [Download GmsCore Latest APK](https://github.com/ReVanced/GmsCore/releases/latest)
2. Open GmsCore once to ensure battery optimization is disabled so notifications work.

#### B. Install Obtainium (The In-App Auto-Updater)
1. Download and install **Obtainium** on your phone:
   👉 [Download Obtainium APK](https://github.com/ImranR98/Obtainium/releases/latest)
2. Open Obtainium and tap **Add App**.
3. In the **App Source URL** field, enter your GitHub repository link:
   `https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>`
4. Tap **Add**. Obtainium will automatically pull your latest patched YouTube APK and offer to install it.

---

### 4. Enable 100% Silent Background Updates (Shizuku)

By default, Android prompts you with an "Update this app?" popup. To make updates **100% automatic in the background without you having to touch anything**:

1. Install **Shizuku** from Google Play Store or GitHub:
   👉 [Shizuku on Google Play](https://play.google.com/store/apps/details?id=moe.shizuku.privileged.api)
2. Open Shizuku and tap **Start via Wireless Debugging** (requires Android 11+ and takes 30 seconds following the on-screen pairing steps; no computer needed).
3. Open **Obtainium** -> go to **Settings** -> **Package Installer** -> Select **Shizuku**.
4. In Obtainium settings, turn on **Automatic Background Updates**.

🎉 **Done!** Whenever a new YouTube update is patched by your GitHub workflow, your phone will download and install it silently in the background.

---

## 💻 Optional: Running Locally on Your PC

If you ever want to patch an APK locally on your computer instead of using GitHub Actions:

```bash
python scripts/builder.py
```

Options:
* `--force`: Force rebuild even if already built.
* `--target-version 19.47.53`: Manually pin a specific YouTube version.
* `--check-only`: Check compatible versions without building.

The finished APK will be saved inside the `build/` folder.

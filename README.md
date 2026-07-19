🌐 **English** | [简体中文](README_CN.md)

<div align="center">

# ComfyUI-ModelFinder

### Legacy open-source Python tool for finding missing ComfyUI models.

[**Download the maintained Windows launcher**](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) · [**Wonderful Launcher release repo**](https://github.com/hu-haibin/wonderful-launcher-comfyui) · [**Website**](https://wonderfullauncher.com/) · [**Docs**](https://wonderfullauncher.com/docs)

</div>

---

## Which one should you use?

If you are here because a ComfyUI workflow is missing models, you probably want **Wonderful Launcher**, not this old Python utility.

| Your situation | Recommended path |
|----------------|------------------|
| You want a Windows app that starts ComfyUI, reads startup logs, matches missing models, and downloads available models | Use [Wonderful Launcher](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) |
| You want to inspect or modify the older standalone Python model-finder code | Use this repository |
| You need a packaged installer | Use the Wonderful Launcher release repo |
| You are comfortable with Python, Chrome automation, and manual folder setup | This repository can still be useful |

This repository is kept as an open-source historical tool. The actively maintained user-facing release channel is:

**<https://github.com/hu-haibin/wonderful-launcher-comfyui>**

---

## What this repository does

ComfyUI-ModelFinder is a standalone Python/Tkinter utility. It can help you:

- scan ComfyUI workflow JSON files and extract referenced model names
- compare those model names with your local ComfyUI `models` folder
- open browser-based searches for missing model files
- generate local result reports
- move or organize downloaded model files into ComfyUI model directories

It was built for users who were comfortable managing their own Python environment and local ComfyUI folders.

## Important limitations

- It is not the current Wonderful Launcher desktop app.
- It does not provide the packaged Windows installer.
- It requires Python and Chrome.
- Search results depend on browser automation and public search pages, so matches can be incomplete or noisy.
- It does not use the maintained Wonderful Launcher cloud model catalog and download workflow.
- If your goal is simply “make this workflow run,” the maintained launcher is the cleaner path.

---

## Run the legacy Python tool

### Requirements

- Windows
- Python available as `python` in PATH
- Google Chrome
- Python packages from `requirements.txt`

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

Or run:

```powershell
.\install_requirements.bat
```

### Start

```powershell
python run_model_finder.py
```

Or run:

```powershell
.\run_model_finder.bat
```

After startup, choose your ComfyUI path and model folders in the app UI.

---

## Relationship with Wonderful Launcher

The naming is easy to confuse, so here is the clean version:

- **ComfyUI-ModelFinder**: this repository; old standalone Python model-finder utility.
- **Wonderful Launcher**: maintained Windows desktop launcher for ComfyUI; current installer and release channel.
- **Release repo**: <https://github.com/hu-haibin/wonderful-launcher-comfyui>

For normal users, the release repo is the download page. This repo is mainly for people who specifically need the old Python implementation.

## FAQ

<details>
<summary><b>Should I download Source code.zip from the release repo?</b></summary>

No. If you want the Windows launcher, download `WonderfulLauncher-Setup-v...exe` from the latest GitHub Release.

</details>

<details>
<summary><b>Is this repository abandoned?</b></summary>

It is kept available as an open-source legacy utility. New user-facing ComfyUI startup, repair, model matching, and download work is handled in Wonderful Launcher.

</details>

<details>
<summary><b>Can this still find missing models?</b></summary>

It can still scan workflows and help search for model names, but it is a manual/local tool. For a smoother workflow, use Wonderful Launcher.

</details>

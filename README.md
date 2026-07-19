🌐 **English** | [简体中文](README_CN.md)

<div align="center">

# Looking for the maintained ComfyUI launcher?

### Download Wonderful Launcher first if your goal is to run ComfyUI workflows, fix missing models, or install a Windows desktop app.

[**Download Wonderful Launcher**](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) · [**Release repository**](https://github.com/hu-haibin/wonderful-launcher-comfyui) · [**Website**](https://wonderfullauncher.com/) · [**Docs**](https://wonderfullauncher.com/docs)

</div>

---

> [!IMPORTANT]
> If you are here because a ComfyUI workflow is missing models, the maintained path is **Wonderful Launcher**. This repository is an older standalone Python utility kept for people who specifically want the legacy implementation.

## Which repository should you use?

| Your situation | Recommended path |
|----------------|------------------|
| You want a Windows app that starts ComfyUI, reads startup logs, matches missing models, and downloads available models | Use [Wonderful Launcher](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) |
| You need the packaged installer | Use the [Wonderful Launcher release repository](https://github.com/hu-haibin/wonderful-launcher-comfyui) |
| You want to inspect or modify the older standalone Python model-finder code | Use this repository |
| You are comfortable with Python, Chrome automation, and manual folder setup | This repository can still be useful |

---

## This repository: ComfyUI-ModelFinder

ComfyUI-ModelFinder is a legacy open-source Python/Tkinter tool for finding missing ComfyUI models. It can help you:

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

## Naming

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

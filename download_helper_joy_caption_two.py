import os
import shutil
import sys
from pathlib import Path

# 尝试导入tqdm，如果不存在则自动安装
try:
    from tqdm import tqdm
except ImportError:
    print("正在安装tqdm进度条库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# 尝试导入DrissionPage，如果不存在则自动安装
try:
    from DrissionPage import ChromiumPage
except ImportError:
    print("正在安装 DrissionPage ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "DrissionPage"])
    from DrissionPage import ChromiumPage

# 定义模型及其下载URL
MODELS = [
    {
        "name": "google/siglip-so400m-patch14-384",
        "foreign_url": "https://huggingface.co/google/siglip-so400m-patch14-384",
        "domestic_url": "https://hf-mirror.com/google/siglip-so400m-patch14-384/tree/main",
        "target_path": "models/clip/siglip-so400m-patch14-384",
        "download_folder": "siglip-so400m-patch14-384"
    },
    {
        "name": "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "foreign_url": "https://huggingface.co/unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "domestic_url": "https://hf-mirror.com/unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit/tree/main",
        "target_path": "models/LLM/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "download_folder": "Meta-Llama-3.1-8B-Instruct-bnb-4bit"
    },
    {
        "name": "unsloth/Meta-Llama-3.1-8B-Instruct",
        "foreign_url": "https://huggingface.co/unsloth/Meta-Llama-3.1-8B-Instruct",
        "domestic_url": "https://hf-mirror.com/unsloth/Meta-Llama-3.1-8B-Instruct/tree/main",
        "target_path": "models/LLM/Meta-Llama-3.1-8B-Instruct",
        "download_folder": "Meta-Llama-3.1-8B-Instruct"
    },
    {
        "name": "Joy-Caption-alpha-two",
        "foreign_url": "https://huggingface.co/spaces/fancyfeast/joy-caption-alpha-two/tree/main/cgrkzexw-599808",
        "domestic_url": "https://hf-mirror.com/spaces/fancyfeast/joy-caption-alpha-two/tree/main/cgrkzexw-599808",
        "target_path": "models/Joy_caption_two",
        "download_folder": "joy-caption-alpha-two"
    }
]

def print_download_links():
    """打印所有模型的下载链接"""
    print("=== 模型下载链接 ===")
    print("请使用您喜欢的下载工具(如迅雷)下载以下模型:")
    print()
    
    print("模型名称：")
    for model in MODELS:
        print(f"{model['name']}")
    
    print("\nhuggingface链接:")
    for model in MODELS:
        print(f"{model['foreign_url']}")
    
    print("\nhf-mirror链接：")
    for model in MODELS:
        print(f"{model['domestic_url']}")
    
    print("\nComfyUI目标路径:")
    for model in MODELS:
        print(f"{model['target_path']}")
    
    print("\n下载完成后，使用此脚本将文件移动到正确位置。")
    print()

def get_dir_size(path):
    """计算目录中所有文件的总大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def copy_with_progress(src, dst):
    """带进度条的文件复制"""
    file_size = os.path.getsize(src)
    with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"复制 {os.path.basename(src)}") as pbar:
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                copied = 0
                while True:
                    buf = fsrc.read(1024*1024)  # 1MB块
                    if not buf:
                        break
                    fdst.write(buf)
                    copied += len(buf)
                    pbar.update(len(buf))

def copy_tree_with_progress(src, dst):
    """带进度条的目录树复制"""
    if not os.path.exists(dst):
        os.makedirs(dst)
    
    items = os.listdir(src)
    for item in tqdm(items, desc=f"{os.path.basename(src)}中的文件"):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item)
            print(f"复制目录: {item}")
            shutil.copytree(src_item, dst_item)
        else:
            # 对于大文件，显示单独的进度条
            if os.path.getsize(src_item) > 50 * 1024 * 1024:  # 50MB
                copy_with_progress(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)

def move_model_files(download_path, comfyui_path):
    """将模型文件从下载位置移动到ComfyUI"""
    # 获取可用的模型（存在的目录）
    available_models = []
    for model in MODELS:
        source_dir = os.path.join(download_path, model["download_folder"])
        if os.path.exists(source_dir):
            available_models.append(model)
        else:
            print(f"警告: 源目录 {source_dir} 不存在，跳过...")
    
    if not available_models:
        print("在下载路径中没有找到模型目录。")
        return
    
    # 显示所有模型的进度
    for i, model in enumerate(available_models):
        source_dir = os.path.join(download_path, model["download_folder"])
        target_dir = os.path.join(comfyui_path, model["target_path"])
        
        # 如果目标目录不存在，创建它
        os.makedirs(target_dir, exist_ok=True)
        
        print(f"\n[{i+1}/{len(available_models)}] 移动 {model['name']} 文件")
        print(f"从: {source_dir}")
        print(f"到: {target_dir}")
        
        # 获取目录大小以便更好地报告进度
        dir_size = get_dir_size(source_dir)
        print(f"总大小: {dir_size / (1024*1024*1024):.2f} GB")
        
        # 使用进度条复制文件
        copy_tree_with_progress(source_dir, target_dir)
        
        print(f"成功移动 {model['name']} 到 {target_dir}")

def open_hf_mirror_links():
    print("\n正在自动打开所有 hf-mirror 链接，请在浏览器中批量下载文件 ...")
    page = ChromiumPage()
    for model in MODELS:
        url = model['domestic_url']
        page.new_tab(url)
    print("已在浏览器中打开所有链接，请批量下载所有文件。\n下载完成后回到此窗口继续。")
    input("下载完成后按回车继续 ...")
    page.quit()

def main():
    # 首先显示下载链接
    print_download_links()
    
    proceed = input("是否自动打开下载页面? (y/n): ").strip().lower()
    if proceed == 'y':
        open_hf_mirror_links()
    else:
        print("您选择不自动打开下载页面，请手动下载模型文件。")
    
    proceed_move = input("是否继续移动下载的文件? (y/n): ").strip().lower()
    if proceed_move != 'y':
        print("退出。当您准备好移动文件时，可以再次运行此脚本。")
        return
    
    # 从用户输入获取路径
    download_path = input("输入您下载模型文件的路径: ").strip()
    comfyui_path = input("输入您的ComfyUI安装路径: ").strip()
    
    # 如果用户复制了带引号的路径，去除引号
    download_path = download_path.strip('"\'')
    comfyui_path = comfyui_path.strip('"\'')
    
    # 验证路径是否存在
    if not os.path.exists(download_path):
        print(f"错误: 下载路径 {download_path} 不存在。")
        return
    
    if not os.path.exists(comfyui_path):
        print(f"错误: ComfyUI路径 {comfyui_path} 不存在。")
        return
    
    # 移动文件
    move_model_files(download_path, comfyui_path)
    print("所有文件已成功移动。")
    input("按回车键退出...")

if __name__ == "__main__":
    main() 
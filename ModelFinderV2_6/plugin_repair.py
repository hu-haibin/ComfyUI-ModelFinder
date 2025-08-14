"""
ModelFinder Plugin Repair Module
负责处理ComfyUI插件的修复功能
"""

import os
import sys
import shutil
import threading
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PluginRepairBase:
    """插件修复功能的基类，所有具体的修复实现都应继承此类"""
    def __init__(self, name, description, error_symptoms):
        self.name = name
        self.description = description
        self.error_symptoms = error_symptoms
    
    def check_status(self, comfyui_path):
        """检查是否需要修复
        
        Args:
            comfyui_path: ComfyUI的安装路径
            
        Returns:
            bool: 是否需要修复
        """
        raise NotImplementedError("子类必须实现check_status方法")
    
    def repair(self, comfyui_path, status_callback=None):
        """执行修复
        
        Args:
            comfyui_path: ComfyUI的安装路径
            status_callback: 可选的回调函数，用于更新界面上的状态
                            函数签名应为 callback(message, progress)
                            progress为0-100的整数
                            
        Returns:
            bool: 修复是否成功
        """
        raise NotImplementedError("子类必须实现repair方法")


class JoyCaptionTwoRepair(PluginRepairBase):
    """Joy Caption Two插件修复实现"""
    def __init__(self):
        super().__init__(
            name="Joy Caption Two",
            description="高质量图像描述插件",
            error_symptoms="缺少text_model目录或模型文件不完整"
        )
    
    def check_status(self, comfyui_path):
        joy_caption_path = os.path.join(comfyui_path, "models", "Joy_caption_two")
        text_model_path = os.path.join(joy_caption_path, "text_model")
        
        return not os.path.exists(joy_caption_path) or not os.path.exists(text_model_path)
    
    def repair(self, comfyui_path, status_callback=None):
        # 确保依赖已安装
        self._install_requirements()
        
        try:
            from tqdm import tqdm
            from huggingface_hub import snapshot_download
        except ImportError:
            logger.error("无法导入必要的库：tqdm或huggingface_hub")
            if status_callback:
                status_callback("错误: 无法导入必要的库", 100)
            else:
                print("错误: 无法导入必要的库")
            return False
        
        # 目标路径
        target_dir = os.path.join(comfyui_path, "models", "Joy_caption_two")
        os.makedirs(target_dir, exist_ok=True)
        
        if status_callback:
            status_callback("开始从Hugging Face下载Joy Caption Two模型...", 10)
        else:
            logger.info(f"开始从Hugging Face下载Joy Caption Two模型到 {target_dir}...")
            print(f"开始从Hugging Face下载Joy Caption Two模型到 {target_dir}...")
            print("这可能需要一些时间，请耐心等待...")
        
        try:
            # 使用snapshot_download下载整个仓库，包括text_model
            if status_callback:
                status_callback("下载 Joy-Caption-alpha-two 模型...", 20)
            else:
                logger.info("下载 Joy-Caption-alpha-two 模型...")
                print("下载 Joy-Caption-alpha-two 模型...")
                
            repo_id = "fancyfeast/joy-caption-alpha-two"
            local_dir = snapshot_download(
                repo_id=repo_id,
                repo_type="space",
                local_dir=os.path.join(target_dir, "temp_download"),
                local_dir_use_symlinks=False
            )
            
            if status_callback:
                status_callback("模型下载完成，正在提取必要文件...", 60)
            else:
                logger.info(f"模型下载完成，正在提取必要文件...")
                print(f"模型下载完成，正在提取必要文件...")
            
            # 将cgrkzexw-599808目录下的内容移动到目标目录
            source_model_dir = os.path.join(local_dir, "cgrkzexw-599808")
            if os.path.exists(source_model_dir):
                # 复制所有文件到目标目录
                items = os.listdir(source_model_dir)
                for i, item in enumerate(items):
                    s = os.path.join(source_model_dir, item)
                    d = os.path.join(target_dir, item)
                    
                    # 更新进度
                    if status_callback:
                        progress = 60 + int((i / len(items)) * 30)
                        status_callback(f"提取文件: {item}", progress)
                    
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                
                if status_callback:
                    status_callback("文件提取完成!", 90)
                else:
                    logger.info("文件提取完成!")
                    print("文件提取完成!")
            else:
                error_msg = f"错误: 在下载的模型中未找到 cgrkzexw-599808 目录"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg, 100)
                else:
                    print(error_msg)
                return False
            
            # 清理临时文件
            shutil.rmtree(os.path.join(target_dir, "temp_download"))
            
            # 验证text_model目录是否存在
            if os.path.exists(os.path.join(target_dir, "text_model")):
                success_msg = "模型修复完成! 现在可以使用Joy Caption Two了。"
                logger.info(success_msg)
                if status_callback:
                    status_callback(success_msg, 100)
                else:
                    print("✓ text_model 目录已成功安装")
                    print(f"\n{success_msg}")
                return True
            else:
                error_msg = "错误: 未能正确提取 text_model 目录"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg, 100)
                else:
                    print(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"下载过程中出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if status_callback:
                status_callback(error_msg, 100)
            else:
                print(error_msg)
            return False
    
    def _install_requirements(self):
        """安装必要的依赖库"""
        try:
            from tqdm import tqdm
        except ImportError:
            logger.info("正在安装tqdm进度条库...")
            print("正在安装tqdm进度条库...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        
        try:
            import huggingface_hub
        except ImportError:
            logger.info("正在安装huggingface_hub...")
            print("正在安装huggingface_hub...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])


class PluginRepairModel:
    """插件修复管理模型"""
    def __init__(self):
        self.repair_plugins = []
        # 注册默认修复插件
        self.register_plugin(JoyCaptionTwoRepair())
    
    def register_plugin(self, plugin):
        """注册修复插件"""
        self.repair_plugins.append(plugin)
    
    def get_all_plugins(self):
        """获取所有注册的修复插件"""
        return self.repair_plugins
    
    def get_plugin_by_name(self, name):
        """根据名称获取修复插件"""
        for plugin in self.repair_plugins:
            if plugin.name == name:
                return plugin
        return None
    
    def check_plugin_status(self, comfyui_path):
        """检查所有插件状态，返回需要修复的插件列表"""
        need_repair = []
        
        for plugin in self.repair_plugins:
            if plugin.check_status(comfyui_path):
                need_repair.append(plugin.name)
        
        return need_repair
    
    def repair_plugin(self, plugin_name, comfyui_path, status_callback=None):
        """修复指定插件"""
        plugin = self.get_plugin_by_name(plugin_name)
        if plugin:
            return plugin.repair(comfyui_path, status_callback)
        else:
            error_msg = f"错误: 找不到插件 {plugin_name}"
            logger.error(error_msg)
            if status_callback:
                status_callback(error_msg, 100)
            else:
                print(error_msg)
            return False 
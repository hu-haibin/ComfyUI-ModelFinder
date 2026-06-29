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

class DummyRepair(PluginRepairBase):
    def __init__(self):
        super().__init__("Joy Caption Two", "高质量图像描述插件", "无")
    def check_status(self, comfyui_path):
        return False  # 始终显示为已安装
    def repair(self, comfyui_path, status_callback=None):
        # 实际修复逻辑由助手脚本负责，这里什么都不做
        return True

class PluginRepairModel:
    """插件修复管理模型"""
    def __init__(self):
        self.repair_plugins = []
        self.register_plugin(DummyRepair())
    
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
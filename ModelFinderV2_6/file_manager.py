"""
文件管理模块
包含：创建结构化输出目录、清理旧文件等功能
"""

import os
import time
import shutil
from datetime import datetime
import ctypes
import sys
import logging

logger = logging.getLogger(__name__)

def is_admin():
    """检查程序是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """尝试以管理员权限重启程序"""
    try:
        if not is_admin():
            # 获取当前程序的完整路径
            script = sys.executable
            params = sys.argv
            params.insert(0, script)
            
            # 使用ShellExecute以管理员权限重启程序
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, " ".join(params), None, 1)
            # 退出当前实例
            sys.exit()
        return True
    except Exception as e:
        logger.error(f"请求管理员权限失败: {e}")
        return False

def create_output_directory():
    """创建有组织的输出目录结构
    
    返回:
        创建的输出目录路径
    """
    try:
        # 使用改进后的get_results_folder函数获取基础目录
        base_dir = get_results_folder()
        
        # 使用当前日期创建子文件夹
        today = datetime.now()
        date_dir = os.path.join(base_dir, f"{today.year:04d}-{today.month:02d}-{today.day:02d}")
        
        # 确保目录存在
        os.makedirs(date_dir, exist_ok=True)
        
        return date_dir
    except Exception as e:
        # 如果发生错误，使用临时目录
        import tempfile
        today = datetime.now()
        date_str = f"{today.year:04d}-{today.month:02d}-{today.day:02d}"
        temp_dir = os.path.join(tempfile.gettempdir(), f"ModelFinder_Results/{date_str}")
        logger.error(f"创建输出目录出错: {e}, 使用临时目录: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

def get_output_path(original_file, extension=None):
    """根据原始文件名生成输出文件路径
    
    参数:
        original_file: 原始文件路径
        extension: 可选的文件扩展名(不含点)，如果不提供则保持原始扩展名
    
    返回:
        输出文件的完整路径
    """
    # 创建输出目录
    output_dir = create_output_directory()
    
    # 获取文件名(不含路径)
    base_name = os.path.basename(original_file)
    
    # 如果提供了新扩展名，替换原有扩展名
    if extension:
        base_name = os.path.splitext(base_name)[0] + f".{extension}"
    
    # 返回完整路径
    return os.path.join(output_dir, base_name)

def cleanup_old_results(days_to_keep=30):
    """清理超过指定天数的结果文件
    
    参数:
        days_to_keep: 保留文件的天数，默认30天
    
    返回:
        清理的文件夹数量
    """
    try:
        # 使用改进后的get_results_folder函数获取基础目录
        base_dir = get_results_folder()
        
        if not os.path.exists(base_dir):
            logger.warning(f"结果目录不存在: {base_dir}")
            return 0
        
        current_time = time.time()
        cleaned_count = 0
        
        # 检查每个日期文件夹
        for dir_name in os.listdir(base_dir):
            dir_path = os.path.join(base_dir, dir_name)
            if os.path.isdir(dir_path):
                # 获取目录修改时间
                dir_time = os.path.getmtime(dir_path)
                # 如果超过指定天数
                if (current_time - dir_time) / (24 * 3600) > days_to_keep:
                    try:
                        shutil.rmtree(dir_path)
                        logger.info(f"已清理旧结果目录: {dir_path}")
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"清理目录出错: {e}")
        
        return cleaned_count
    except Exception as e:
        logger.error(f"清理旧结果出错: {e}")
        return 0

def get_results_folder():
    """获取结果文件夹的路径
    
    返回:
        结果文件夹的完整路径
    """
    try:
        # 获取应用程序所在目录
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包环境
            base_path = sys._MEIPASS
            logger.debug(f"使用PyInstaller基础路径: {base_path}")
        else:
            # 开发环境
            # 首先尝试获取当前模块的目录
            base_path = os.path.dirname(os.path.abspath(__file__))
            logger.debug(f"文件管理器模块路径: {base_path}")
            
            # 如果在model_finder子目录中，则上移一级
            if os.path.basename(base_path) == 'model_finder':
                base_path = os.path.dirname(base_path)
                logger.debug(f"上移至父目录: {base_path}")
        
        # 如果以上逻辑失败，尝试使用当前工作目录
        if not os.path.exists(base_path):
            base_path = os.getcwd()
            logger.debug(f"使用当前工作目录: {base_path}")
        
        # 在程序目录下的results文件夹
        results_dir = os.path.join(base_path, "results")
        logger.debug(f"结果目录: {results_dir}")
        
        # 确保目录存在
        os.makedirs(results_dir, exist_ok=True)
        
        # 再次验证目录是否可访问
        if not os.path.exists(results_dir) or not os.access(results_dir, os.W_OK):
            # 如果不可访问，回退到用户文档目录
            import ctypes.wintypes
            CSIDL_PERSONAL = 5  # 我的文档
            SHGFP_TYPE_CURRENT = 0  # 当前值
            
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            
            # 在我的文档下创建一个结果文件夹
            docs_path = buf.value
            results_dir = os.path.join(docs_path, "ModelFinder_Results")
            logger.debug(f"使用备用结果目录: {results_dir}")
            os.makedirs(results_dir, exist_ok=True)
        
        return results_dir
    except Exception as e:
        # 出错时使用临时目录
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "ModelFinder_Results")
        logger.error(f"获取结果目录出错: {e}, 使用临时目录: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
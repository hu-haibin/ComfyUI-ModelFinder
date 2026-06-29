"""
配置日志记录系统 (Logger Configuration System)
设置统一的日志格式、级别和输出方式 (Set unified log format, level, and output method)
"""

import os
import logging
import logging.handlers
from datetime import datetime

def setup_logger(log_level=logging.INFO):
    """
    设置全局日志配置，支持文件和控制台输出
    Set up global logging configuration, supporting file and console output
    
    Args:
        log_level: 日志级别，默认为INFO (Log level, default is INFO)
    """
    # 创建logs目录（如果不存在）
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # 创建日志文件名，包含日期
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"modelfinder_{today}.log")
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除任何现有的处理器（防止重复输出）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建详细的日志格式，匹配示例
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [ModelFinderV2_5.%(module)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S,%f'[:-3]  # 格式化到毫秒
    )
    
    # 设置格式
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到根日志记录器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 设置特定模块的日志级别
    logging.getLogger('ModelFinderV2_5.analysis_model').setLevel(logging.DEBUG)
    logging.getLogger('ModelFinderV2_5.controller').setLevel(logging.INFO)
    
    # 记录一个启动日志消息
    root_logger.info("日志系统初始化完成 (Logging system initialized)")
    return root_logger 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Model Finder Launcher
This script handles the startup of the Model Finder application, including logging setup.
"""

import os
import sys
import logging # Import logging module
import logging.handlers # For file handler
from tkinter import messagebox # Keep for critical startup errors
import tkinter as tk # Keep for critical startup errors

# --- Early Logging Setup ---
# We configure logging here so that even import errors or early issues can be logged.

def setup_logging():
    """Configures logging to console and file."""
    log_level = logging.DEBUG # Set to logging.INFO for less verbose output in production
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    log_filename = "app.log" # Log filename

    # Determine log file path (place it in the 'results' folder if possible)
    log_dir = None
    try:
        # Try to import file_manager to get results path
        # Add project root to sys.path temporarily if needed
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from ModelFinderV2_6.file_manager import get_results_folder
        log_dir = get_results_folder()
        # Ensure the directory exists
        os.makedirs(log_dir, exist_ok=True)
        log_filepath = os.path.join(log_dir, log_filename)
    except Exception as e:
        print(f"Warning: Could not determine results directory for log file: {e}. Logging to current directory.")
        log_filepath = log_filename # Fallback to current directory

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers (important if script is run multiple times in same session)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Console Handler (StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # File Handler
    try:
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logging to {log_filepath}: {e}")

    logging.info("Logging configured successfully.")
    logging.info(f"Log level set to: {logging.getLevelName(log_level)}")
    if log_dir:
        logging.info(f"Log file path: {log_filepath}")

# --- Main Application Execution ---

def main():
    # Configure logging as the first step
    setup_logging()
    logger = logging.getLogger(__name__) # Get logger for the launcher itself
    logger.info(f"Starting Model Finder {__version__ if '__version__' in locals() else 'N/A'}...") # Version might not be available yet

    try:
        # Add project root to Python path (if not already done by setup_logging)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            logger.debug(f"Added {current_dir} to sys.path")

        # Import the main application components AFTER path setup
        # Handle import errors specifically
        start_app = None
        try:
            # We now import the *main* function from the refactored model_finder.py
            from ModelFinderV2_6.model_finder import main as start_app
            from ModelFinderV2_6 import __version__, __author__ # Get version/author after successful import
            logger.info(f"Successfully imported Model Finder v{__version__} by {__author__}")
        except ImportError as e:
             logger.critical(f"ERROR: Could not import Model Finder components: {e}", exc_info=True)
             # Use Tkinter messagebox as fallback UI for critical error
             tk_root = tk.Tk()
             tk_root.withdraw()
             messagebox.showerror("启动错误", f"无法导入程序组件:\n{e}\n\n请确保文件完整并检查日志。")
             tk_root.destroy()
             input("按Enter键退出...") # Keep console pause
             return # Exit script

        # Optional: Automatic cleanup of old results on startup
        try:
             from ModelFinderV2_6.file_manager import cleanup_old_results
             # Use a default value or value from config if available (later)
             cleaned_count = cleanup_old_results(days_to_keep=7)
             if cleaned_count > 0:
                 logger.info(f"自动清理了 {cleaned_count} 个旧结果目录 (超过7天)。")
        except ImportError:
             logger.warning("无法导入 file_manager 或 cleanup_old_results，跳过自动清理。")
        except Exception as e:
             logger.error("自动清理旧结果时出错。", exc_info=True)


        # Start the application (calling the main() function from model_finder.py)
        if start_app:
            logger.info("Launching Model Finder GUI...")
            start_app() # This now sets up ttk.Window, Controller, View and runs mainloop
            logger.info("Model Finder GUI closed.")
        else:
             # This should not happen if import succeeded, but as a safeguard:
             logger.error("start_app function not defined after import.")
             input("按Enter键退出...")


    except Exception as e:
        # Log any other uncaught exception during startup phase
        logger.critical(f"An unexpected error occurred during startup: {e}", exc_info=True)
        try:
            tk_root = tk.Tk()
            tk_root.withdraw()
            messagebox.showerror("严重错误", f"程序启动时遇到意外错误:\n{e}\n\n请查看日志文件 app.log。")
            tk_root.destroy()
        except Exception as me:
            print(f"无法显示最终错误消息框: {me}") # Last resort print
        input("按Enter键退出...") # Keep console pause

if __name__ == "__main__":
    # Set version for logging if available before importing main app
    try:
        from ModelFinderV2_6 import __version__
    except ImportError:
        __version__ = "Unknown" # Default if import fails early
    main()
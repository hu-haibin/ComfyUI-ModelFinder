# model_finder/model_finder.py (Main Application Runner)

import sys
import tkinter as tk
from tkinter import messagebox # Keep for fallback error
import ttkbootstrap as ttk

# Import Controller and View
from .controller import AppController
from .view import AppView
# Import package info (optional here, could be passed from launcher)
from . import __version__, __author__

class ModelFinderApp:
    """
    Main application class responsible for initializing
    the controller and view and starting the application.
    """
    def __init__(self, root):
        self.root = root
        try:
            # 1. Create the View instance
            self.view = AppView(self.root)

            # 2. Create the Controller instance, passing root and view
            self.controller = AppController(self.root, self.view, __version__, __author__)

            # 3. Initialize the controller (loads settings, links view/controller)
            self.controller.initialize()

        except Exception as e:
            import logging
            logging.error("Error during ModelFinderApp Initialization", exc_info=True)
            messagebox.showerror("初始化错误", f"应用程序初始化失败:\n{e}")
            self.root.destroy() # Close window if init fails badly
            sys.exit(1) # Exit the script

def main():
    """Sets up and runs the application."""
    root = None # Initialize root to None
    try:
        # Start with a basic theme, controller will apply loaded/random theme later
        root = ttk.Window(themename="cosmo")
        app = ModelFinderApp(root)
        root.mainloop()
    except Exception as e:
        import logging
        # Fallback error handling if GUI fails catastrophically
        error_msg = f"程序启动失败: {type(e).__name__}: {str(e)}"
        logging.critical(error_msg, exc_info=True)
        
        # Try to show a simple Tkinter error box if possible
        try:
            if root and root.winfo_exists(): # Check if root window was created
                 messagebox.showerror("启动错误", error_msg, parent=root) # Associate with root if possible
            else: # Create temporary root if main one failed early
                 tk_root = tk.Tk()
                 tk_root.withdraw()
                 messagebox.showerror("启动错误", error_msg)
                 tk_root.destroy()
        except Exception as me:
             print(f"无法显示启动错误消息框: {me}")
        finally:
            print("\n如果遇到问题，请检查依赖是否都已安装。")
            input("按Enter键退出...")
            if root and root.winfo_exists():
                root.destroy() # Ensure window is closed on catastrophic failure
            sys.exit(1) # Exit script on failure

# Note: The if __name__ == "__main__": check should be in the launcher (run_model_finder.py)
# This file should ideally only be imported.
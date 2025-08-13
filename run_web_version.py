#!/usr/bin/env python3
"""
ModelFinder Web版本启动脚本
"""

import os
import sys
import webbrowser
import uvicorn
from pathlib import Path

def main():
    print("🚀 启动 ModelFinder Web 版本...")
    
    # 检查frontend目录是否存在
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ frontend 目录不存在")
        return
    
    # 检查Vue界面文件是否存在
    vue_file = frontend_dir / "index.html"
    if not vue_file.exists():
        print("❌ Vue界面文件不存在: frontend/index.html")
        return
    
    print("✅ 检查通过，开始启动服务...")
    print()
    print("📱 Vue界面: http://localhost:8000/vue")
    print("🧪 测试页面: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print()
    print("💡 建议使用Vue界面获得最佳体验！")
    print("🔄 修改代码后会自动重载，无需重启")
    print()
    
    # 3秒后自动打开Vue界面
    import threading
    import time
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open("http://localhost:8000/vue")
            print("🌐 已自动打开Vue界面")
        except:
            print("⚠️  无法自动打开浏览器，请手动访问: http://localhost:8000/vue")
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # 启动服务器
    try:
        uvicorn.run(
            "api_wrapper:app",
            host="127.0.0.1", 
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()

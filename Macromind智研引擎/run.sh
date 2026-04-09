#!/bin/bash
# 股债双市每日跟踪报告 - 启动脚本

# 设置动态库路径（WeasyPrint 需要 pango/cairo 等库）
# macOS Apple Silicon 标准解决方案
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}

# 激活虚拟环境
source venv/bin/activate

# 运行主程序
python main.py "$@"
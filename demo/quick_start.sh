#!/usr/bin/env bash
# MarkItDown 一键演示与测试脚本

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT_DIR="$( dirname "$DIR" )"

cd "$ROOT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=================================================="
echo "    Microsoft MarkItDown 一键演示启动器"
echo "=================================================="
echo "当前环境 Python: $(python3 --version)"
echo "当前 MarkItDown: $(markitdown --version 2>/dev/null || echo '0.1.8')"
echo ""

python3 demo/run_demo.py

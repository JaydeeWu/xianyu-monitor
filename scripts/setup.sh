#!/usr/bin/env bash
# xianyu-monitor 一键安装脚本
# 适配: Hermes / OpenClaw / Claude Code / Codex / 独立使用

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🐟 xianyu-monitor 安装脚本${NC}"
echo "================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. 检查 Python
echo ""
echo -e "${YELLOW}[1/4] 检查 Python...${NC}"
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "${RED}❌ 未找到 Python，请先安装 Python 3.8+${NC}"
    exit 1
fi
echo "✅ Python: $($PY --version)"

# 2. 安装 playwright
echo ""
echo -e "${YELLOW}[2/4] 安装 playwright...${NC}"
$PY -m pip install playwright --quiet 2>/dev/null || pip install playwright --quiet 2>/dev/null
echo "✅ playwright 已安装"

# 3. 安装 Chromium 浏览器
echo ""
echo -e "${YELLOW}[3/4] 安装 Chromium 浏览器...${NC}"
# 国内服务器使用 npmmirror 加速
if curl -s --connect-timeout 3 https://www.google.com >/dev/null 2>&1; then
    echo "  检测到可访问 Google，使用默认下载源"
    $PY -m playwright install chromium
else
    echo "  检测到国内网络，使用 npmmirror 加速"
    PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright $PY -m playwright install chromium
fi
echo "✅ Chromium 已安装"

# 4. 安装系统依赖
echo ""
echo -e "${YELLOW}[4/4] 安装系统依赖...${NC}"
if [ "$(uname)" = "Linux" ]; then
    echo "  Linux 系统，安装 Chromium 系统依赖..."
    $PY -m playwright install-deps chromium 2>/dev/null || echo "  ⚠️  部分依赖可能需要手动安装（sudo 可能需要）"
else
    echo "  非 Linux 系统，跳过"
fi
echo "✅ 系统依赖已安装"

# 完成
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ 安装完成！${NC}"
echo ""
echo "快速开始："
echo ""
echo "  # 添加监控任务"
echo "  $PY $SCRIPT_DIR/xianyu_monitor.py add --keyword \"RTX4090\" --max-price 15000"
echo ""
echo "  # 设置 Cookie（重要！未登录只能看6小时前的商品）"
echo "  $PY $SCRIPT_DIR/xianyu_monitor.py cookie --cookie-string '你的cookie'"
echo ""
echo "  # 执行扫描"
echo "  $PY $SCRIPT_DIR/xianyu_monitor.py scan"
echo ""
echo "  # 查看帮助"
echo "  $PY $SCRIPT_DIR/xianyu_monitor.py --help"

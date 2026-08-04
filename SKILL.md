---
name: xianyu-monitor
description: "闲鱼(Goofish)商品价格监控。自动搜索、去重、价格过滤、推送通知。Use when: user wants to monitor 闲鱼/Xianyu/Goofish for specific items, set up price alerts, track second-hand goods, or find deals on 闲鱼."
---

# 闲鱼商品监控 (xianyu-monitor)

监控闲鱼（Goofish）上的二手商品价格，自动发现新商品并推送通知。

## 一句话安装

### Hermes Agent
```bash
hermes skills install https://github.com/JaydeeWu/xianyu-monitor
```

### OpenClaw
```bash
claw install https://github.com/JaydeeWu/xianyu-monitor
```

### Claude Code / Codex / 其他智能体
```bash
# 克隆到 skills 目录
git clone https://github.com/JaydeeWu/xianyu-monitor.git ~/.skills/xianyu-monitor
# 安装依赖
pip install playwright && python3 -m playwright install chromium
# 国内加速：
# PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright python3 -m playwright install chromium
python3 -m playwright install-deps chromium
```

安装后即可使用，无需手动配置路径。

## 使用方式

### 自然语言（Hermes / OpenClaw / Claude Code / Codex）

直接告诉智能体你想监控什么：

- "帮我监控闲鱼上 RTX4090 的价格，最高 15000"
- "我想看 MacBook M4 二手价格，6000 到 12000 之间"
- "监控 V100 16G 显卡，排除租赁相关的"
- "闲鱼上有没有 iPhone 16 Pro 256G 低于 9000 的？"
- "查看我的闲鱼监控任务列表"
- "闲鱼监控有什么新商品吗？"
- "每 30 分钟帮我扫一次闲鱼，有新商品通知我"
- "设置闲鱼 cookie：[粘贴 cookie]"

智能体会自动调用脚本完成搜索、去重、过滤和推送。

### 命令行

```bash
python3 scripts/xianyu_monitor.py scan                           # 扫描所有任务
python3 scripts/xianyu_monitor.py scan --task-id 1               # 只扫描任务1
python3 scripts/xianyu_monitor.py scan --push feishu             # 推送到飞书
python3 scripts/xianyu_monitor.py add --keyword "RTX4090" --max-price 15000
python3 scripts/xianyu_monitor.py add --keyword "MacBook" --min-price 6000 --max-price 12000 --exclude "翻新,维修"
python3 scripts/xianyu_monitor.py add --keyword "iPhone 16" --only "256G,512G" --max-price 9000
python3 scripts/xianyu_monitor.py remove --task-id 3
python3 scripts/xianyu_monitor.py list
python3 scripts/xianyu_monitor.py history --keyword "2080ti" --limit 50
python3 scripts/xianyu_monitor.py cookie --cookie-string '...'
```

## Cookie 设置

闲鱼需要登录态才能看到实时商品（未登录只能看 6 小时前的）。

1. 浏览器登录 https://goofish.com
2. F12 → Network → 搜索任意关键词 → 点击请求 → 复制 Request Headers 中的 **Cookie** 值
3. 保存到文件：
   ```bash
   echo '你的cookie' > ~/.xianyu-monitor/cookie.txt
   ```
   或：`python3 scripts/xianyu_monitor.py cookie --cookie-string '你的cookie'`

Cookie 有效期约 **7 天**，过期后需重新获取。过期症状：搜索结果为 0 条。

## 定时监控

### Hermes cron
```
hermes cron create --name "闲鱼监控" --schedule "30m" --prompt "运行闲鱼监控扫描，有新商品通知我"
```

### 系统 crontab
```bash
*/30 * * * * cd /path/to/xianyu-monitor && python3 scripts/xianyu_monitor.py scan >> /var/log/xianyu-monitor.log 2>&1
```

### 飞书推送
设置环境变量后使用 `--push feishu`：
```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id"
python3 scripts/xianyu_monitor.py scan --push feishu
```

## 数据目录

| 文件 | 路径 | 说明 |
|------|------|------|
| 数据库 | `~/.xianyu-monitor/monitor.db` | SQLite，自动去重 |
| Cookie | `~/.xianyu-monitor/cookie.txt` | 登录态，约7天有效 |

以上文件在 `.gitignore` 中排除，**不会上传到 GitHub**。

## 依赖

- Python 3.8+
- playwright（自动安装 Chromium）

安装脚本 `scripts/setup.sh` 会自动处理依赖和国内镜像加速。

## 反爬要点

详见 `references/goofish-antiscraping.md`。核心：

- 纯 HTTP 请求 → 返回空壳 SPA，无数据 ❌
- mtop API → 已封禁外部访问 ❌
- Playwright + headless Chromium + Cookie → ✅
- 扫描间隔建议 ≥ 30 分钟

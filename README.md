# 🐟 xianyu-monitor

[![Skill](https://img.shields.io/badge/AI_Skill-Universal-blue)](https://github.com/JaydeeWu/xianyu-monitor)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

闲鱼（Goofish）商品价格监控 — 适配 Hermes / OpenClaw / Claude Code / Codex 等智能体的一键部署技能。

自动搜索闲鱼二手商品，价格过滤，智能去重，新商品推送通知。

## ✨ 功能

- 🔍 **任意关键词搜索** — 监控任何闲鱼商品
- 💰 **价格区间过滤** — 只看预算内的
- 🚫 **排除词 / 必含词** — 灵活过滤无关商品
- 🔄 **自动去重** — SQLite 存储，只推送新商品
- 📱 **飞书推送** — 新商品自动通知
- ⏰ **定时监控** — cron 定时扫描
- 🤖 **智能体原生** — 自然语言操作，无需记命令
- 🖥️ **跨平台** — 支持 Hermes / OpenClaw / Claude Code / Codex

## 📦 一句话安装

### Hermes Agent
```bash
hermes skills install https://github.com/JaydeeWu/xianyu-monitor
```

### OpenClaw
```bash
claw install https://github.com/JaydeeWu/xianyu-monitor
```

### Claude Code / Codex / 通用
```bash
git clone https://github.com/JaydeeWu/xianyu-monitor.git
cd xianyu-monitor
bash scripts/setup.sh
```

`setup.sh` 会自动安装 Python 依赖、Chromium 浏览器和系统依赖（国内自动使用 npmmirror 加速）。

## 🚀 使用

### 自然语言（推荐）

直接告诉你的 AI 智能体：

> "帮我监控闲鱼上 RTX4090 的价格，最高 15000"

> "我想看 MacBook M4 二手，6000 到 12000 之间，排除翻新和维修"

> "每 30 分钟扫一次闲鱼，有新商品通知我"

> "闲鱼监控有什么新商品吗？"

> "设置闲鱼 cookie：[粘贴你的 cookie]"

### 命令行

```bash
# 扫描所有活跃任务
python3 scripts/xianyu_monitor.py scan

# 只扫描指定任务
python3 scripts/xianyu_monitor.py scan --task-id 1

# 扫描并推送到飞书
python3 scripts/xianyu_monitor.py scan --push feishu

# 添加监控任务
python3 scripts/xianyu_monitor.py add --keyword "RTX4090" --max-price 15000
python3 scripts/xianyu_monitor.py add --keyword "MacBook M4" --min-price 6000 --max-price 12000 --exclude "翻新,维修"
python3 scripts/xianyu_monitor.py add --keyword "iPhone 16" --only "256G,512G" --max-price 9000

# 停用 / 查看 / 历史
python3 scripts/xianyu_monitor.py remove --task-id 3
python3 scripts/xianyu_monitor.py list
python3 scripts/xianyu_monitor.py history --keyword "2080ti" --limit 50

# Cookie 管理
python3 scripts/xianyu_monitor.py cookie                          # 查看状态
python3 scripts/xianyu_monitor.py cookie --cookie-string '...'    # 设置
```

## 🍪 Cookie 设置

闲鱼需要登录态才能看到实时发布的商品（未登录只能看 6 小时前的）。

1. 浏览器打开 https://goofish.com 并登录（建议用小号）
2. F12 → Network → 搜索任意关键词 → 点击搜索请求
3. 在 Request Headers 中找到 `Cookie` 字段，**整段复制**
4. 保存：
   ```bash
   python3 scripts/xianyu_monitor.py cookie --cookie-string '粘贴的cookie'
   ```

Cookie 有效期约 **7 天**，过期后搜索结果为 0 条，需重新获取。

## ⏰ 定时监控

### Hermes
```bash
hermes cron create --name "闲鱼监控" --schedule "30m" \
  --prompt "运行闲鱼监控扫描，有新商品通知我"
```

### 系统 crontab
```bash
*/30 * * * * cd /path/to/xianyu-monitor && python3 scripts/xianyu_monitor.py scan >> /var/log/xianyu-monitor.log 2>&1
```

### 飞书推送
```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id"
python3 scripts/xianyu_monitor.py scan --push feishu
```

## 📁 项目结构

```
xianyu-monitor/
├── SKILL.md                    # 智能体技能描述（Hermes/OpenClaw/Claude/Codex 通用）
├── README.md                   # 本文件
├── LICENSE                     # MIT
├── requirements.txt            # Python 依赖
├── .gitignore                  # 排除 cookie、数据库等敏感文件
├── scripts/
│   ├── xianyu_monitor.py       # 核心监控脚本
│   └── setup.sh                # 一键安装脚本
└── references/
    └── goofish-antiscraping.md # 闲鱼反爬技术文档
```

## 🔧 工作原理

1. **Playwright 渲染** — headless Chromium 加载闲鱼搜索页，绕过反爬
2. **Cookie 注入** — 模拟登录态，获取实时商品数据
3. **DOM 提取** — JavaScript 在页面内提取标题、价格、地区、发布时间
4. **SQLite 去重** — 基于 item_id，只记录新商品
5. **关键词过滤** — 排除词/必含词/价格区间灵活筛选

## ⚠️ 注意事项

- 闲鱼反爬严格，**必须使用 Playwright 渲染**（纯 HTTP 请求返回空数据）
- Cookie 包含登录态，**不要泄露或上传到公开仓库**
- 建议使用闲鱼小号登录，降低封号风险
- 扫描间隔建议 ≥ 30 分钟，频繁请求可能触发风控
- 本项目仅供学习交流，请遵守闲鱼平台规则

## 📄 License

[MIT](LICENSE)

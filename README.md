# 🐟 xianyu-monitor

闲鱼（Goofish）商品价格监控工具 — 自动搜索、价格过滤、去重、推送通知。

纯 Python + Playwright 实现，无需浏览器插件，支持 Linux 服务器部署。

## ✨ 功能

- 🔍 **关键词搜索** — 支持任意闲鱼商品搜索
- 💰 **价格过滤** — 设置最低/最高价格区间
- 🚫 **排除词/必含词** — 灵活过滤无关商品
- 🔄 **自动去重** — SQLite 存储已发现商品，只推送新商品
- 📱 **飞书推送** — 新商品自动推送到飞书 Webhook
- ⏰ **定时监控** — 配合 cron 实现定时扫描
- 📊 **历史查询** — 查看所有发现记录，支持关键词搜索

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/xianyu-monitor.git
cd xianyu-monitor

# 安装依赖
pip install playwright
python3 -m playwright install chromium

# Linux 服务器还需要安装系统依赖
python3 -m playwright install-deps chromium
```

> 💡 国内服务器加速安装 Chromium：
> ```bash
> export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
> python3 -m playwright install chromium
> ```

## 🚀 使用

### 1. 设置 Cookie（重要）

未登录只能看到 6 小时前的商品，登录后可看到实时发布的新品。

```bash
# 在浏览器中登录 goofish.com
# F12 → Network → 搜索任意关键词 → 点击请求 → 复制 Request Headers 中的 Cookie

python3 xianyu_monitor.py cookie --cookie-string '你的Cookie'
```

Cookie 有效期约 **7 天**，过期后需重新获取。

### 2. 添加监控任务

```bash
# 监控 RTX 4090
python3 xianyu_monitor.py add --keyword "RTX4090" --max-price 15000

# 监控 MacBook M4，排除翻新和维修
python3 xianyu_monitor.py add --keyword "MacBook M4" --min-price 6000 --max-price 12000 --exclude "翻新,维修"

# 监控 iPhone 16 Pro，只看 256G 和 512G 版本
python3 xianyu_monitor.py add --keyword "iPhone 16 Pro" --only "256G,512G" --max-price 9000

# 监控 V100 显卡
python3 xianyu_monitor.py add --keyword "V100 16G" --min-price 500 --max-price 5000 --exclude "租,租赁"
```

### 3. 执行扫描

```bash
# 扫描所有活跃任务
python3 xianyu_monitor.py scan

# 只扫描指定任务
python3 xianyu_monitor.py scan --task-id 1

# 扫描并推送到飞书
python3 xianyu_monitor.py scan --push feishu
```

### 4. 其他命令

```bash
# 查看所有任务
python3 xianyu_monitor.py list

# 查看历史记录
python3 xianyu_monitor.py history --limit 50

# 按关键词搜索历史
python3 xianyu_monitor.py history --keyword "2080ti"

# 停用任务
python3 xianyu_monitor.py remove --task-id 3

# 查看 Cookie 状态
python3 xianyu_monitor.py cookie
```

## ⏰ 定时监控（Cron）

设置每 30 分钟自动扫描：

```bash
# 编辑 crontab
crontab -e

# 添加以下行
*/30 * * * * cd /path/to/xianyu-monitor && python3 xianyu_monitor.py scan --push feishu >> /var/log/xianyu-monitor.log 2>&1
```

或使用 Hermes Agent 的 cron 功能：

```
hermes cron create --name "闲鱼监控" --schedule "30m" --prompt "运行 python3 /path/to/xianyu-monitor/xianyu_monitor.py scan，如有新商品通知我"
```

## 📱 飞书推送

设置飞书 Webhook 环境变量：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id"
```

然后在扫描时使用 `--push feishu`，新商品会自动推送格式化消息。

## 🔧 工作原理

1. **Playwright 无头浏览器** — 访问闲鱼搜索页，绕过反爬检测
2. **Cookie 注入** — 模拟登录态，获取实时商品数据
3. **DOM 数据提取** — 用 JavaScript 在页面内提取商品标题、价格、地区
4. **SQLite 去重** — 基于 item_id 去重，只记录新商品
5. **关键词过滤** — 排除词/必含词/价格区间灵活过滤

## 📁 数据目录

```
~/.xianyu-monitor/
├── monitor.db      # SQLite 数据库（任务+商品记录）
└── cookie.txt      # 闲鱼登录 Cookie
```

## ⚠️ 注意事项

- 闲鱼反爬严格，必须使用 Playwright 渲染页面（不支持纯 HTTP 请求）
- Cookie 包含登录态，**不要泄露或上传到公开仓库**
- 建议使用闲鱼小号登录，降低封号风险
- 扫描间隔建议 ≥ 30 分钟，过于频繁可能触发风控
- Cookie 约 7 天过期，过期后搜索结果为空，需重新获取
- 本项目仅供学习交流，请遵守闲鱼平台规则

## 📄 License

MIT

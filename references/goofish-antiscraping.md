# 闲鱼 (Goofish) 反爬绕过与 DOM 提取技术文档

闲鱼反爬严格，直接 HTTP 请求只能拿到空壳 SPA，必须用 Playwright 渲染。

## 已验证的方案

### ✅ Playwright + headless Chromium + Cookie 注入

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 800},
        locale='zh-CN',
    )
```

### ✅ 反检测

```python
page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
    Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
""")
```

### ✅ Cookie 注入

从浏览器 F12 → Network → 请求头复制完整 Cookie，注入时过滤无效字段：

```python
cookies = []
for part in cookie_str.split('; '):
    if '=' in part:
        k, v = part.split('=', 1)
        k = k.strip()
        # 过滤 Set-Cookie 响应头字段（只有 name=value 是有效的）
        if k and k not in ('path', 'domain', 'SameSite', 'Secure',
                           'Max-Age', 'Partitioned', 'expires'):
            cookies.append({
                'name': k, 'value': v.strip(),
                'domain': '.goofish.com', 'path': '/',
            })
context.add_cookies(cookies)
```

### ✅ DOM 数据提取（最可靠方式）

用 `page.evaluate()` 在页面 JS 环境内提取，比 Python 端解析 DOM 更稳定：

```javascript
document.querySelectorAll('a[href*="/item?id="]').forEach(a => {
    const idMatch = a.href.match(/id=(\d+)/);
    const container = a.closest('[class*="feeds-item"]')
                   || a.closest('[class*="item"]')
                   || a.parentElement.parentElement.parentElement;
    const text = container ? container.innerText : a.innerText;
    // 价格：/[¥￥]\s*(\d{2,5})/
    // 地区：匹配省份/城市名
    // 发布时间：/前发布|天前|小时前|分钟前|刚刚/
});
```

关键：**价格在 `feeds-item` 容器内而不在 `a` 标签内**，必须向上查找容器。

## ❌ 不可行的方案

| 方案 | 结果 | 原因 |
|------|------|------|
| `requests.get(goofish.com/search)` | 返回 ~10KB 空壳 HTML | SPA 客户端渲染，无数据 |
| mtop API (`mtop.taobao.idlefish.search.item`) | `FAIL_SYS_API_NOT_FOUNDED` | 已封禁外部访问 |
| headless Chrome without Cookie | 只有 6 小时前的商品 | 未登录限制 |
| `page.goto(searchURL)` | 被拦截显示登录墙 | baxia 反爬检测 |
| AppleScript (macOS only) | 不跨平台 | 本项目需支持 Linux |

## 登录态检测

脚本自动检测登录状态：
- 搜索结果中有 "分钟前发布" → 已登录 ✅
- 搜索结果中最新也是 "6小时前发布" → 未登录/Cookie 过期 ⚠️

## Cookie 有效期

约 **7 天**。过期后：
1. 重新登录 goofish.com
2. F12 → Network → 复制新 Cookie
3. `python3 scripts/xianyu_monitor.py cookie --cookie-string '新cookie'`

## 风控规避

- 扫描间隔 ≥ 30 分钟
- 使用小号登录
- 不要同时搜索大量关键词
- 如遇验证码，等待一段时间后重试

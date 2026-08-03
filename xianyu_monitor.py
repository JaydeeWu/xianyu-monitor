#!/usr/bin/env python3
"""
闲鱼(Goofish) 商品价格监控 - Playwright 版
支持任意关键词、价格区间、排除词/必含词过滤

用法：
  python3 xianyu_monitor.py scan                    # 扫描所有活跃任务
  python3 xianyu_monitor.py scan --push feishu       # 扫描并推送到飞书
  python3 xianyu_monitor.py scan --task-id 1         # 只扫描指定任务
  python3 xianyu_monitor.py add --keyword "RTX4090" --max-price 15000
  python3 xianyu_monitor.py add --keyword "MacBook M4" --min-price 6000 --max-price 12000 --exclude "翻新,维修"
  python3 xianyu_monitor.py remove --task-id 3       # 停用任务
  python3 xianyu_monitor.py list                     # 查看所有任务
  python3 xianyu_monitor.py history --limit 50       # 查看历史
  python3 xianyu_monitor.py cookie                   # 查看 Cookie 状态
  python3 xianyu_monitor.py cookie --cookie-string '...'  # 设置 Cookie

依赖：pip install playwright && python3 -m playwright install chromium
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

DB_PATH = os.path.expanduser("~/.xianyu-monitor/monitor.db")
COOKIE_PATH = os.path.expanduser("~/.xianyu-monitor/cookie.txt")
DATA_DIR = os.path.dirname(DB_PATH)


def ensure_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL, min_price INTEGER DEFAULT 0,
        max_price INTEGER DEFAULT 999999, exclude TEXT DEFAULT '',
        only TEXT DEFAULT '', active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS items (
        item_id TEXT PRIMARY KEY, task_id INTEGER, title TEXT,
        price INTEGER, original_price INTEGER, location TEXT,
        seller_nick TEXT, publish_time TEXT, image_url TEXT, url TEXT,
        discovered_at TEXT DEFAULT (datetime('now','localtime')),
        pushed INTEGER DEFAULT 0)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_items_task ON items(task_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_items_discovered ON items(discovered_at)")
    conn.commit()
    return conn


def search_goofish(keyword, cookie_str=None):
    """用 Playwright 渲染闲鱼搜索页并提取商品数据"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright 未安装。运行: pip install playwright && python3 -m playwright install chromium")
        return []

    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                  '--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )

        if cookie_str:
            cookies = []
            for part in cookie_str.split('; '):
                if '=' in part:
                    k, v = part.split('=', 1)
                    k = k.strip()
                    if k and k not in ('path', 'domain', 'SameSite', 'Secure', 'Max-Age', 'Partitioned', 'expires'):
                        cookies.append({'name': k, 'value': v.strip(), 'domain': '.goofish.com', 'path': '/'})
            if cookies:
                context.add_cookies(cookies)

        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
        """)

        try:
            page.goto('https://www.goofish.com/', wait_until='domcontentloaded', timeout=20000)
            time.sleep(2)

            search_url = f'https://www.goofish.com/search?q={keyword}'
            page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(3)

            try:
                page.wait_for_selector('a[href*="/item?id="]', timeout=8000)
            except:
                pass

            for _ in range(2):
                page.evaluate('window.scrollBy(0, 800)')
                time.sleep(1)

            # JS 提取商品数据（最可靠）
            items_raw = page.evaluate(r'''() => {
                const results = [];
                document.querySelectorAll('a[href*="/item?id="]').forEach((a, i) => {
                    if (i >= 30) return;
                    const idMatch = a.href.match(/id=(\d+)/);
                    if (!idMatch) return;
                    const itemId = idMatch[1];
                    const container = a.closest('[class*="feeds-item"]') || a.closest('[class*="item"]') || a.parentElement.parentElement.parentElement;
                    const text = container ? container.innerText : a.innerText;
                    const lines = text.split('\n').map(l => l.trim()).filter(l => l);
                    let price = null;
                    const priceMatch = text.match(/[¥￥]\s*(\d{2,5})/);
                    if (priceMatch) {
                        const p = parseInt(priceMatch[1]);
                        if (p >= 50) price = p;
                    }
                    let title = lines[0] || '';
                    let location = '';
                    const provs = ['北京','上海','广东','浙江','江苏','四川','湖北','湖南','山东','河南','河北','福建','安徽','陕西','甘肃','内蒙古','新疆','西藏','广西','宁夏','青海','海南','吉林','辽宁','黑龙江','云南','贵州','重庆','天津','深圳','广州','杭州','成都','武汉','南京','苏州','西安','长沙','东莞','宁波','佛山','青岛','郑州','厦门','福州','合肥','大连','沈阳','济南','昆明','贵阳','兰州','太原','石家庄','无锡','常州','珠海','中山','惠州','金华','温州','嘉兴','绍兴','烟台','潍坊','保定','廊坊','洛阳','徐州','南通','扬州','镇江'];
                    for (const line of lines) {
                        if (line.length <= 6 && provs.some(p => line.includes(p))) {
                            location = line;
                            break;
                        }
                    }
                    let pubTime = '';
                    for (const line of lines) {
                        if (/前发布|天前|小时前|分钟前|刚刚/.test(line)) {
                            pubTime = line;
                            break;
                        }
                    }
                    results.push({
                        item_id: itemId,
                        title: title.substring(0, 80),
                        price: price,
                        location: location,
                        publish_time: pubTime,
                        url: 'https://www.goofish.com/item?id=' + itemId
                    });
                });
                return results;
            }''')

            for it in items_raw:
                items.append({
                    'item_id': it['item_id'],
                    'title': it.get('title', ''),
                    'price': it.get('price'),
                    'original_price': None,
                    'location': it.get('location', ''),
                    'seller_nick': '',
                    'publish_time': it.get('publish_time', ''),
                    'image_url': '',
                    'url': it.get('url', f"https://www.goofish.com/item?id={it['item_id']}"),
                })

            # 兜底：从 HTML 正则提取
            if not items:
                content = page.content()
                id_set = set()
                for m in re.finditer(r'/item\?id=(\d+)', content):
                    iid = m.group(1)
                    if iid not in id_set:
                        id_set.add(iid)
                        pos = m.start()
                        nearby = content[max(0, pos-300):pos+500]
                        price_match = re.search(r'[¥￥]\s*(\d{2,5})', nearby)
                        price = int(price_match.group(1)) if price_match else None
                        items.append({
                            'item_id': iid, 'title': '', 'price': price,
                            'original_price': None, 'location': '', 'seller_nick': '',
                            'publish_time': '', 'image_url': '',
                            'url': f'https://www.goofish.com/item?id={iid}',
                        })

        except Exception as e:
            print(f"[ERROR] Playwright error: {e}", file=sys.stderr)
        finally:
            browser.close()

    return items


def filter_items(items, task):
    filtered = []
    min_p = task.get("min_price", 0) or 0
    max_p = task.get("max_price", 999999) or 999999
    exclude = [w.strip() for w in (task.get("exclude") or "").split(",") if w.strip()]
    only = [w.strip() for w in (task.get("only") or "").split(",") if w.strip()]

    for item in items:
        if not item or not item.get("item_id"):
            continue
        price = item.get("price")
        if price is not None and (price < min_p or price > max_p):
            continue
        title = item.get("title", "").lower()
        if any(ex.lower() in title for ex in exclude):
            continue
        if only and not any(ow.lower() in title for ow in only):
            continue
        filtered.append(item)
    return filtered


def save_items(conn, items, task_id):
    c = conn.cursor()
    new_count = 0
    for item in items:
        try:
            c.execute("SELECT 1 FROM items WHERE item_id = ?", (item["item_id"],))
            if c.fetchone():
                continue
            c.execute(
                "INSERT OR IGNORE INTO items (item_id,task_id,title,price,original_price,location,seller_nick,publish_time,image_url,url) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (item["item_id"], task_id, item.get("title",""), item.get("price"),
                 item.get("original_price"), item.get("location",""), item.get("seller_nick",""),
                 item.get("publish_time",""), item.get("image_url",""), item.get("url","")))
            new_count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return new_count


def push_to_feishu(items, webhook_url=None):
    """推送到飞书 Webhook"""
    import requests
    webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("[INFO] 未设置 FEISHU_WEBHOOK_URL，跳过推送", file=sys.stderr)
        return
    for item in items[:10]:
        price_str = f"¥{item['price']}" if item.get("price") else "价格未知"
        msg = f"🐟 **{item.get('title','未知')[:50]}**\n💰 {price_str} | 📍 {item.get('location','未知')}\n🔗 {item.get('url','')}"
        try:
            requests.post(webhook_url, json={
                "msg_type": "interactive",
                "card": {"header": {"title": {"tag": "plain_text", "content": "闲鱼监控提醒"}},
                         "elements": [{"tag": "markdown", "content": msg}]}
            }, timeout=10)
        except Exception as e:
            print(f"[WARN] 飞书推送失败: {e}", file=sys.stderr)
    print(f"[OK] 已推送 {min(len(items),10)} 条到飞书")


def cmd_scan(args):
    conn = ensure_db()
    c = conn.cursor()

    if args.task_id:
        c.execute("SELECT * FROM tasks WHERE id=? AND active=1", (args.task_id,))
    else:
        c.execute("SELECT * FROM tasks WHERE active=1")

    tasks = c.fetchall()
    if not tasks:
        print("[INFO] 没有活跃的监控任务。用 add 命令添加: python3 xianyu_monitor.py add --keyword '关键词'")
        return

    cookie = open(COOKIE_PATH).read().strip() if os.path.exists(COOKIE_PATH) else None
    if not cookie:
        print("[WARN] 未设置 Cookie，搜索结果可能不完整。运行: python3 xianyu_monitor.py cookie")

    all_new = []
    for task in tasks:
        tid, keyword, min_p, max_p, exclude, only, active, created = task
        config = {"keyword": keyword, "min_price": min_p, "max_price": max_p, "exclude": exclude or "", "only": only or ""}
        max_str = str(max_p) if max_p < 999999 else "不限"
        print(f'\n🔍 扫描: "{keyword}" (¥{min_p}-¥{max_str})')

        items = search_goofish(keyword, cookie)
        print(f"   原始结果: {len(items)} 条")

        items = filter_items(items, config)
        print(f"   过滤后: {len(items)} 条")

        new_count = save_items(conn, items, tid)
        print(f"   新商品: {new_count} 条")

        for item in items[:5]:
            price_str = f"¥{item['price']}" if item.get("price") else "?"
            print(f"   ✨ {item.get('title','?')[:45]} | {price_str} | {item.get('location','')} | {item.get('publish_time','')}")

        c.execute("SELECT item_id,title,price,location,url,publish_time FROM items WHERE task_id=? AND pushed=0 ORDER BY discovered_at DESC", (tid,))
        new_rows = c.fetchall()
        for r in new_rows:
            all_new.append({"item_id": r[0], "title": r[1], "price": r[2], "location": r[3], "url": r[4], "publish_time": r[5]})
        c.execute("UPDATE items SET pushed=1 WHERE task_id=? AND pushed=0", (tid,))
        conn.commit()

    if all_new:
        print(f"\n--- NEW_ITEMS_JSON ---")
        print(json.dumps(all_new, ensure_ascii=False, indent=2))
        print("--- END_NEW_ITEMS_JSON ---")
        if args.push == "feishu":
            push_to_feishu(all_new)
    else:
        print("\n📭 没有发现新商品")

    conn.close()


def cmd_add(args):
    conn = ensure_db()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (keyword,min_price,max_price,exclude,only) VALUES (?,?,?,?,?)",
              (args.keyword, args.min_price or 0, args.max_price or 999999, args.exclude or "", args.only or ""))
    conn.commit()
    max_str = str(args.max_price) if args.max_price else "不限"
    print(f'[OK] 已添加监控任务 #{c.lastrowid}: "{args.keyword}" (¥{args.min_price or 0}-¥{max_str})')
    conn.close()


def cmd_remove(args):
    conn = ensure_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET active=0 WHERE id=?", (args.task_id,))
    conn.commit()
    print(f'[OK] 已停用任务 #{args.task_id}' if c.rowcount else f'[WARN] 任务 #{args.task_id} 不存在')
    conn.close()


def cmd_list(args):
    conn = ensure_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY id")
    tasks = c.fetchall()
    if not tasks:
        print("没有监控任务。用 add 命令添加。")
    else:
        print(f"{'ID':<5} {'状态':<6} {'关键词':<25} {'价格范围':<15} {'排除词':<20} {'必含词':<15}")
        print("-" * 90)
        for t in tasks:
            tid, keyword, min_p, max_p, exclude, only, active, created = t
            status = "✅" if active else "❌"
            max_str = str(max_p) if max_p < 999999 else "不限"
            print(f"{tid:<5} {status:<6} {keyword:<25} ¥{min_p}-{max_str:<12} {exclude or '-':<20} {only or '-':<15}")
    conn.close()


def cmd_history(args):
    conn = ensure_db()
    c = conn.cursor()
    query = "SELECT item_id,title,price,location,publish_time,url,discovered_at FROM items"
    params = []
    if args.task_id:
        query += " WHERE task_id=?"
        params.append(args.task_id)
    if args.keyword:
        query += (" WHERE " if not args.task_id else " AND ") + "title LIKE ?"
        params.append(f"%{args.keyword}%")
    query += " ORDER BY discovered_at DESC LIMIT ?"
    params.append(args.limit or 20)
    c.execute(query, params)
    rows = c.fetchall()
    if not rows:
        print("没有历史记录")
    else:
        print(f"{'价格':<10} {'地区':<8} {'发布时间':<15} {'标题':<40} {'链接'}")
        print("-" * 120)
        for r in rows:
            iid, title, price, loc, pub, url, disc = r
            price_str = f"¥{price}" if price else "?"
            print(f"{price_str:<10} {loc or '':<8} {(pub or '')[:12]:<15} {(title or '?')[:38]:<40} {url}")
    conn.close()


def cmd_cookie(args):
    if args.cookie_string:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(COOKIE_PATH, 'w') as f:
            f.write(args.cookie_string.strip())
        print("[OK] Cookie 已保存")
    else:
        if os.path.exists(COOKIE_PATH):
            cookie = open(COOKIE_PATH).read().strip()
            print(f"✅ Cookie 已设置 ({len(cookie)} 字符)")
            for field in ['_m_h5_tk', 'cookie2', 'sgcookie', 'unb']:
                if field in cookie:
                    print(f"   ✅ {field}")
                else:
                    print(f"   ⚠️  缺少 {field}")
            exp_match = re.search(r'havana_lgc_exp=(\d+)', cookie)
            if exp_match:
                exp_ts = int(exp_match.group(1)) / 1000
                exp_dt = datetime.fromtimestamp(exp_ts)
                remaining = exp_dt - datetime.now()
                if remaining.days > 0:
                    print(f"   📅 Cookie 预计有效期还剩 {remaining.days} 天")
                else:
                    print(f"   ⚠️  Cookie 可能已过期！（过期于 {exp_dt.strftime('%Y-%m-%d')}）")
        else:
            print("❌ 未设置 Cookie")
            print("\n设置方法：")
            print("1. 浏览器登录 goofish.com")
            print("2. F12 → Network → 搜索任意关键词 → 点击请求 → 复制 Request Headers 中的 Cookie")
            print(f"3. python3 xianyu_monitor.py cookie --cookie-string '你的cookie'")


def main():
    parser = argparse.ArgumentParser(
        description="🐟 闲鱼监控 - 通用商品价格追踪",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s scan                              # 扫描所有活跃任务
  %(prog)s scan --task-id 1                  # 只扫描任务1
  %(prog)s scan --push feishu                # 扫描并推送到飞书
  %(prog)s add --keyword "RTX4090" --max-price 15000
  %(prog)s add --keyword "MacBook M4" --min-price 6000 --max-price 12000 --exclude "翻新,维修"
  %(prog)s add --keyword "iPhone 16 Pro" --only "256G,512G" --max-price 9000
  %(prog)s remove --task-id 3
  %(prog)s list
  %(prog)s history --keyword "2080ti" --limit 50
  %(prog)s cookie --cookie-string '...'
        """,
    )
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="执行扫描")
    scan_p.add_argument("--task-id", type=int, help="指定任务ID")
    scan_p.add_argument("--push", choices=["feishu"], help="推送方式")

    add_p = sub.add_parser("add", help="添加监控任务")
    add_p.add_argument("--keyword", required=True, help="搜索关键词")
    add_p.add_argument("--min-price", type=int, help="最低价格")
    add_p.add_argument("--max-price", type=int, help="最高价格")
    add_p.add_argument("--exclude", help="排除词（逗号分隔）")
    add_p.add_argument("--only", help="必含词（逗号分隔）")

    rm_p = sub.add_parser("remove", help="停用监控任务")
    rm_p.add_argument("--task-id", type=int, required=True)

    sub.add_parser("list", help="列出所有任务")

    hist_p = sub.add_parser("history", help="查看历史记录")
    hist_p.add_argument("--task-id", type=int)
    hist_p.add_argument("--keyword", help="按关键词筛选")
    hist_p.add_argument("--limit", type=int, default=20)

    cookie_p = sub.add_parser("cookie", help="管理 Cookie")
    cookie_p.add_argument("--cookie-string", help="设置 Cookie 字符串")

    args = parser.parse_args()
    cmds = {"scan": cmd_scan, "add": cmd_add, "remove": cmd_remove,
            "list": cmd_list, "history": cmd_history, "cookie": cmd_cookie}
    if args.command in cmds:
        cmds[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

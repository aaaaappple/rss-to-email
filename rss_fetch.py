import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import html
import re

# ---------------------- 小白必改！只改这3行！其他不动！----------------------
QQ_EMAIL = "1047372945@qq.com"
QQ_AUTH_CODE = "excnvmaryozwbech"
RECEIVER_EMAIL = "1047372945@qq.com"
# ---------------------------------------------------------------------------

# 数据源配置（路透社优先展示，分源独立标序核心依赖此顺序）
RSS_SOURCES = [
    ("https://reutersnew.buzzing.cc/feed.xml", "路透社", 1),  # 先展示+独立标序1、2、3...
    ("https://bloombergnew.buzzing.cc/feed.xml", "彭博社", 2)   # 后展示+独立标序1、2、3...
]

# 样式配置（标序颜色和来源颜色绑定，区分更清晰）
STYLE_CONFIG = {
    "email_bg": "#f5f5f5",        # 邮件背景（柔和不刺眼）
    "container_bg": "#ffffff",    # 内容卡片背景（纯白整洁）
    "title_color": "#2E4057",     # 邮件主标题颜色（深蓝色醒目）
    "time_color": "#F97316",      # 时间颜色（橙色，一眼找时间）
    "reuters_color": "#E63946",   # 路透社序号+来源颜色（红色，专属标识）
    "bloomberg_color": "#1D4ED8", # 彭博社序号+来源颜色（蓝色，专属标识）
    "title_font_size": "18px",    # 主标题字号（适中不突兀）
    "news_font_size": "15px",     # 资讯内容字号（易读不费力）
    "line_height": "2.2",         # 行间距（宽松不拥挤）
    "link_color": "#16A34A",      # 原文链接颜色（绿色，醒目易点击）
    "container_padding": "25px",  # 内容卡片内边距（不贴边更美观）
    "list_padding": "0 0 0 22px"  # 列表左内边距（排版整齐不跑偏）
}

# 防重复推送（自动记录已发资讯ID，逻辑不变）
def get_pushed_ids():
    if not os.path.exists("pushed_ids.txt"):
        return set()
    with open("pushed_ids.txt", "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

def save_pushed_id(id):
    with open("pushed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{id}\n")

# 邮件发送核心（样式渲染+SMTP推送，仅适配标序样式，逻辑不变）
def send_email(subject, content):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ background: {STYLE_CONFIG['email_bg']}; font-family: 微软雅黑, Arial, sans-serif; margin: 0; padding: 20px; }}
            .container {{ background: {STYLE_CONFIG['container_bg']}; border-radius: 10px; padding: {STYLE_CONFIG['container_padding']}; max-width: 800px; margin: 0 auto; }}
            .main-title {{ color: {STYLE_CONFIG['title_color']}; margin: 0 0 22px 0; font-size: {STYLE_CONFIG['title_font_size']}; }}
            ul {{ list-style: none; padding: {STYLE_CONFIG['list_padding']}; margin: 0; line-height: {STYLE_CONFIG['line_height']}; font-size: {STYLE_CONFIG['news_font_size']}; }}
            li {{ margin-bottom: 10px; }}
            .news-num {{ font-weight: bold; margin-right: 9px; }}  /* 序号加粗，间距适中 */
            .time {{ color: {STYLE_CONFIG['time_color']}; font-weight: bold; }}
            .source-reuters {{ color: {STYLE_CONFIG['reuters_color']}; font-weight: bold; }}
            .source-bloomberg {{ color: {STYLE_CONFIG['bloomberg_color']}; font-weight: bold; }}
            a {{ color: {STYLE_CONFIG['link_color']}; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">{content}</div>
    </body>
    </html>
    """
    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = QQ_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(QQ_EMAIL, QQ_AUTH_CODE)
        smtp.sendmail(QQ_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        print("✅ 邮件推送成功！标序：路透社、彭博社各自独立从1开始")
    except smtplib.SMTPAuthenticationError:
        print("❌ 登录失败！请替换为自己的QQ邮箱16位SMTP授权码（不是登录密码）")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# 智能提取资讯分时（XX:XX），无则后续显月日（逻辑不变）
def get_source_exact_hm(content):
    try:
        content = html.unescape(content).replace("\n", "").replace("\r", "").replace("\t", "").strip()
        patterns = [r'>\s*(\d{2}:\d{2})\s*<', r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>', r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"']
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    except:
        return None

# 提取资讯月日（MM-DD），无时间字段则显当前月日（逻辑不变）
def get_news_md_date(entry):
    try:
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            return datetime.now().strftime("%m-%d")
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return time_obj.strftime("%m-%d")
    except:
        return datetime.now().strftime("%m-%d")

# 提取更新时间戳（用于数据源内部按“最新在前”排序，逻辑不变）
def get_source_update_timestamp(entry):
    try:
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            return datetime.now().timestamp()
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return time_obj.timestamp()
    except:
        return datetime.now().timestamp()

# 核心逻辑：分源抓取+各自独立标序+按时间倒序排列（重点保障标序独立）
def fetch_rss():
    pushed_ids = get_pushed_ids()
    # 分数据源存储资讯，确保后续各自独立标序
    source_news = {"路透社": [], "彭博社": []}

    # 循环抓取两个数据源，各自筛选、排序
    for rss_url, source, weight in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            temp_list = []
            for entry in feed.entries:
                entry_id = entry.get("id", "").strip()
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 筛选有效资讯（未推送+有ID+有标题+有有效链接，过滤垃圾内容）
                if entry_id not in pushed_ids and entry_id and title and link.startswith(("http", "https")):
                    # 智能显时间：有分时显分时，无则显月日
                    show_time = get_source_exact_hm(content) or get_news_md_date(entry)
                    # 提取时间戳（用于内部排序）
                    timestamp = get_source_update_timestamp(entry)
                    temp_list.append((timestamp, show_time, title, link))
                    # 记录已推送ID，防重复
                    save_pushed_id(entry_id)
            
            # 单个数据源内部：按更新时间倒序（最新的在前）
            temp_list.sort(key=lambda x: -x[0])
            source_news[source] = [(t, tit, lk) for _, t, tit, lk in temp_list]
        except Exception as e:
            print(f"⚠️ {source}抓取出错：{e}（不影响另一个数据源推送）")

    # 整理邮件内容：仅保留主标题，路透社、彭博社各自独立标序合并为一个列表
    email_content = [f"<h2 class='main-title'>📩 最新资讯推送（{datetime.now().strftime('%m-%d')}）</h2>", "<ul>"]
    
    # 路透社：独立标序1、2、3...（红色序号+红色来源）
    for num, (show_time, title, link) in enumerate(source_news["路透社"], 1):
        email_content.append(f"""
        <li>
            <span class="news-num source-reuters">{num}.</span>
            ［<span class="time">{show_time}</span> <span class="source-reuters">路透社</span>］
            {title} 👉 <a href='{link}' target='_blank'>原文链接</a>
        </li>
        """)
    
    # 彭博社：独立标序1、2、3...（蓝色序号+蓝色来源，重新从1开始）
    for num, (show_time, title, link) in enumerate(source_news["彭博社"], 1):
        email_content.append(f"""
        <li>
            <span class="news-num source-bloomberg">{num}.</span>
            ［<span class="time">{show_time}</span> <span class="source-bloomberg">彭博社</span>］
            {title} 👉 <a href='{link}' target='_blank'>原文链接</a>
        </li>
        """)
    
    email_content.append("</ul>")
    final_content = "\n".join(email_content)

    # 有新资讯才推送（避免空邮件）
    if source_news["路透社"] or source_news["彭博社"]:
        send_email(f"资讯推送 | {datetime.now().strftime('%m-%d')}", final_content)
    else:
        print("ℹ️  暂无新资讯，本次不推送")

# 执行脚本（直接运行，无需额外操作）
if __name__ == "__main__":
    fetch_rss()


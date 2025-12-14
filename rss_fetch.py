import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os
import html
import re

# ---------------------- 小白必改！只改这3行！----------------------
QQ_EMAIL = "1047372945@qq.com"
QQ_AUTH_CODE = "excnvmaryozwbech"
RECEIVER_EMAIL = "1047372945@qq.com"
# ------------------------------------------------------------------

# 数据源配置
RSS_SOURCES = [
    ("https://reutersnew.buzzing.cc/feed.xml", "路透社"),
    ("https://bloombergnew.buzzing.cc/feed.xml", "彭博社")
]

# 颜色配置（内联样式用，确保邮箱兼容）
COLORS = {
    "time": "#F97316",       # 时间：橙色
    "reuters": "#E63946",    # 路透社：红色
    "bloomberg": "#1D4ED8",  # 彭博社：蓝色
    "link": "#16A34A"        # 链接：绿色
}

# 防重复推送：读取已推送ID
def get_pushed_ids():
    if not os.path.exists("pushed_ids.txt"):
        return set()
    with open("pushed_ids.txt", "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

# 防重复推送：保存已推送ID
def save_pushed_id(id):
    with open("pushed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{id}\n")

# 发送邮件（改用内联样式，确保颜色生效）
def send_email(subject, content):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 微软雅黑, Arial, sans-serif; line-height: 2.2; font-size: 15px; }}
            li {{ margin-bottom: 12px; list-style: none; padding-left: 8px; }}
        </style>
    </head>
    <body>
        <h2 style="color:#2E4057; font-size:18px; margin-bottom:25px;">📩 最新资讯推送（{datetime.now().strftime('%m-%d')}）</h2>
        <ul style="padding-left:22px; margin:0;">
            {content}
        </ul>
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
        print("✅ 邮件推送成功！颜色生效+时间混合排序")
    except smtplib.SMTPAuthenticationError:
        print("❌ 登录失败！请替换为自己的QQ邮箱16位SMTP授权码")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# 提取资讯分时（XX:XX），无则返回月日（MM-DD）
def get_show_time(entry, content):
    try:
        # 提取分时
        content = html.unescape(content).replace("\n", "").replace("\r", "").replace("\t", "").strip()
        patterns = [r'>\s*(\d{2}:\d{2})\s*<', r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>', r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"']
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        # 提取月日
        time_str = entry.get("updated", entry.get("published", ""))
        if time_str:
            time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return time_obj.strftime("%m-%d")
        return datetime.now().strftime("%m-%d")
    except:
        return datetime.now().strftime("%m-%d")

# 提取资讯时间戳（用于混合排序）
def get_timestamp(entry):
    try:
        time_str = entry.get("updated", entry.get("published", ""))
        if time_str:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp()
        return datetime.now().timestamp()
    except:
        return datetime.now().timestamp()

# 核心逻辑：混合排序+分源独立标序+颜色生效
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 存储所有资讯：(时间戳, 来源, 展示时间, 标题, 链接, 资讯ID)
    source_counter = {"路透社": 0, "彭博社": 0}  # 分源计数

    # 抓取所有数据源资讯
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                entry_id = entry.get("id", "").strip()
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 筛选有效资讯
                if entry_id not in pushed_ids and entry_id and title and link.startswith(("http", "https")):
                    show_time = get_show_time(entry, content)
                    timestamp = get_timestamp(entry)
                    all_news.append((timestamp, source, show_time, title, link, entry_id))
                    save_pushed_id(entry_id)  # 标记已推送
        except Exception as e:
            print(f"⚠️ {source}抓取出错：{e}")

    # 按时间戳倒序混合排序（最新的在前）
    all_news.sort(key=lambda x: -x[0])
    news_html = []

    # 生成混合排序后的资讯列表，分源独立标序
    for news in all_news:
        _, source, show_time, title, link, _ = news
        source_counter[source] += 1  # 对应来源计数+1
        counter = source_counter[source]

        # 内联样式设置颜色，确保邮箱生效
        time_style = f"color:{COLORS['time']};font-weight:bold;"
        source_color = COLORS["reuters"] if source == "路透社" else COLORS["bloomberg"]
        source_style = f"color:{source_color};font-weight:bold;"
        link_style = f"color:{COLORS['link']};text-decoration:none;font-weight:500;"
        link_hover = f"color:{COLORS['link']};text-decoration:underline;"

        # 生成单条资讯HTML
        news_item = f"""
        <li>
            {counter}. ［<span style="{time_style}">{show_time}</span> <span style="{source_style}">{source}({counter})</span>］
            {title} 👉 <a href="{link}" target="_blank" style="{link_style}" onmouseover="this.style='{link_hover}'">原文链接</a>
        </li>
        """
        news_html.append(news_item)

    # 推送邮件
    if news_html:
        final_content = "\n".join(news_html)
        send_email(f"资讯推送 | {datetime.now().strftime('%m-%d')}", final_content)
    else:
        print("ℹ️  暂无新资讯，本次不推送")

if __name__ == "__main__":
    fetch_rss()


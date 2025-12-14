import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
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

# 颜色配置（内联样式用，确保QQ邮箱兼容）
COLORS = {
    "time": "#F97316",       # 时间：橙色
    "reuters": "#E63946",    # 路透社：红色
    "bloomberg": "#1D4ED8",  # 彭博社：蓝色
    "link": "#E63946",       # 链接符号：红色
    "title": "#2E4057"       # 主标题：深蓝色
}

# 防重复推送：读取已推送的资讯ID
def get_pushed_ids():
    if not os.path.exists("pushed_ids.txt"):
        return set()
    with open("pushed_ids.txt", "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

# 防重复推送：保存已推送的资讯ID
def save_pushed_id(id):
    with open("pushed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{id}\n")

# 发送邮件（两处日期显示完整北京时间：年-月-日）
def send_email(subject, content, news_bj_date):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 微软雅黑, Arial, sans-serif; line-height: 2.2; font-size: 15px; }}
            li {{ margin-bottom: 12px; list-style: none; padding-left: 1px; }}
            a {{ text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <!-- 邮件内主标题：完整北京时间（年-月-日） -->
        <h2 style="color:{COLORS['title']}; font-size:18px; margin-bottom:25px;">路博速递（{news_bj_date}）</h2>
        <ul style="padding-left:2px; margin:0;">
            {content}
        </ul>
    </body>
    </html>
    """
    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = QQ_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject  # 邮件主题：完整北京时间（年-月-日）

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(QQ_EMAIL, QQ_AUTH_CODE)
        smtp.sendmail(QQ_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        print("✅ 邮件推送成功！两处日期显示完整北京时间（年-月-日）")
    except smtplib.SMTPAuthenticationError:
        print("❌ 登录失败！请替换为自己的QQ邮箱16位SMTP授权码（非登录密码）")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# 提取资讯展示时间（分时保持原始，不转换）
def get_show_time(entry, content):
    try:
        content = html.unescape(content).replace("\n", "").replace("\r", "").replace("\t", "").strip()
        time_patterns = [
            r'>\s*(\d{2}:\d{2})\s*<',
            r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>',
            r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        entry_time = entry.get("updated", entry.get("published", ""))
        if entry_time:
            time_obj = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            return time_obj.strftime("%m-%d")
        return datetime.now().strftime("%m-%d")
    except:
        return datetime.now().strftime("%m-%d")

# 提取资讯UTC时间并转换为【完整北京时间】（戳+年-月-日）
def get_news_bj_info(entry):
    try:
        entry_time = entry.get("updated", entry.get("published", ""))
        if entry_time:
            # 解析UTC时间
            utc_time = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            # 转换为北京时间
            bj_time = utc_time + timedelta(hours=8)
            # 返回：北京时间戳（排序用）、完整北京时间（年-月-日，显示用）
            return bj_time.timestamp(), bj_time.strftime("%Y-%m-%d")
        # 无时间字段时，返回当前完整北京时间
        current_bj = datetime.now()
        return current_bj.timestamp(), current_bj.strftime("%Y-%m-%d")
    except:
        # 异常时，返回当前完整北京时间
        current_bj = datetime.now()
        return current_bj.timestamp(), current_bj.strftime("%Y-%m-%d")

# 核心逻辑：两处日期显示完整北京时间（年-月-日），其余功能不变
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 存储：(北京时间戳, 来源, 展示时间, 标题, 链接, 资讯ID, 完整北京时间)
    source_counter = {"路透社": 0, "彭博社": 0}  # 分源计数（括号内用）
    global_counter = 0  # 全局计数（最前面的连续序号）

    # 抓取并筛选所有数据源的资讯
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                entry_id = entry.get("id", "").strip()
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 筛选条件：未推送+有有效ID+有标题+有合法链接
                if entry_id not in pushed_ids and entry_id and title and link.startswith(("http", "https")):
                    show_time = get_show_time(entry, content)
                    # 获取资讯的北京时间戳+完整北京时间（年-月-日）
                    bj_timestamp, news_bj_date = get_news_bj_info(entry)
                    all_news.append((bj_timestamp, source, show_time, title, link, entry_id, news_bj_date))
                    save_pushed_id(entry_id)  # 标记为已推送，避免重复
        except Exception as e:
            print(f"⚠️ {source}资讯抓取出错：{e}（不影响其他数据源）")

    # 按北京时间戳倒序排序（最新资讯在前）
    all_news.sort(key=lambda x: -x[0])
    news_html_list = []  # 存储每条资讯的HTML代码

    # 确定两处标题的显示日期：优先最新资讯的完整北京时间，无新资讯则用当前
    if all_news:
        display_bj_date = all_news[0][6]  # 最新资讯的完整北京时间（年-月-日）
    else:
        display_bj_date = datetime.now().strftime("%Y-%m-%d")  # 兜底：当前完整北京时间

    # 生成带双序号+🔗符号的资讯列表
    for news in all_news:
        bj_timestamp, source, show_time, title, link, _, _ = news
        global_counter += 1
        source_counter[source] += 1
        source_seq = source_counter[source]

        # 内联样式：颜色逻辑不变
        time_style = f"color:{COLORS['time']};font-weight:bold;"
        source_color = COLORS["reuters"] if source == "路透社" else COLORS["bloomberg"]
        source_style = f"color:{source_color};font-weight:bold;"
        link_style = f"color:{COLORS['link']};"

        # 🔗符号替换原文链接（逻辑不变）
        news_html = f"""
        <li>
            {global_counter}. ［<span style="{time_style}">{show_time}</span> <span style="{source_style}">{source}({source_seq})</span>］
            {title} 👉 <a href="{link}" target="_blank" style="{link_style}">🔗</a>
        </li>
        """
        news_html_list.append(news_html)

    # 有新资讯才发送邮件
    if news_html_list:
        final_content = "\n".join(news_html_list)
        # 邮件主题：完整北京时间（年-月-日），对应第一个圈
        email_title = f"快讯 | {display_bj_date}"
        # 发送邮件，传入完整北京时间（用于邮件内主标题，对应第二个圈）
        send_email(email_title, final_content, display_bj_date)
    else:
        print("ℹ️  暂无新资讯，本次不推送邮件")

# 执行脚本
if __name__ == "__main__":
    fetch_rss()


import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime  # 移除时区转换，仅保留当前北京时间获取
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
    "link": "#16A34A",       # 链接符号：绿色
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

# 发送邮件（仅两处月日改为北京时间，其余不变）
def send_email(subject, content):
    # 获取北京时间的月日（仅用于邮件内主标题，对应第二个圈）
    bj_date = datetime.now().strftime("%m-%d")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 微软雅黑, Arial, sans-serif; line-height: 2.2; font-size: 15px; }}
            li {{ margin-bottom: 12px; list-style: none; padding-left: 8px; }}
            a {{ text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <!-- 邮件内主标题：第二个圈的月日，用北京时间 -->
        <h2 style="color:{COLORS['title']}; font-size:18px; margin-bottom:25px;">📩 最新资讯推送（{bj_date}）</h2>
        <ul style="padding-left:22px; margin:0;">
            {content}
        </ul>
    </body>
    </html>
    """
    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = QQ_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject  # 邮件主题：第一个圈的月日，外部传入（已为北京时间）

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(QQ_EMAIL, QQ_AUTH_CODE)
        smtp.sendmail(QQ_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        print("✅ 邮件推送成功！仅两处月日改为北京时间，其余不变")
    except smtplib.SMTPAuthenticationError:
        print("❌ 登录失败！请替换为自己的QQ邮箱16位SMTP授权码（非登录密码）")
    except Exception as e:
        print(f"❌ 推送失败：{e}")

# 提取资讯展示时间（恢复原始逻辑，分时不做时区转换，对应你的要求）
def get_show_time(entry, content):
    try:
        # 提取原始分时（XX:XX），不做任何时区转换，保持原样
        content = html.unescape(content).replace("\n", "").replace("\r", "").replace("\t", "").strip()
        time_patterns = [
            r'>\s*(\d{2}:\d{2})\s*<',
            r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>',
            r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()  # 直接返回原始分时，不转换
        # 提取原始月日（无分时时用），此处仍保持原始逻辑，不改动
        entry_time = entry.get("updated", entry.get("published", ""))
        if entry_time:
            time_obj = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            return time_obj.strftime("%m-%d")
        return datetime.now().strftime("%m-%d")
    except:
        return datetime.now().strftime("%m-%d")

# 提取资讯时间戳（恢复原始逻辑，不做时区转换，排序不变）
def get_news_timestamp(entry):
    try:
        entry_time = entry.get("updated", entry.get("published", ""))
        if entry_time:
            return datetime.fromisoformat(entry_time.replace("Z", "+00:00")).timestamp()
        return datetime.now().timestamp()
    except:
        return datetime.now().timestamp()

# 核心逻辑：仅两处月日改北京时间，其余功能（标序/符号/颜色/排序）全不变
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 存储所有有效资讯：(时间戳, 来源, 展示时间, 标题, 链接, 资讯ID)
    source_counter = {"路透社": 0, "彭博社": 0}  # 分源计数（括号内用）
    global_counter = 0  # 全局计数（最前面的连续序号）

    # 抓取并筛选所有数据源的资讯（逻辑不变）
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
                    timestamp = get_news_timestamp(entry)
                    all_news.append((timestamp, source, show_time, title, link, entry_id))
                    save_pushed_id(entry_id)  # 标记为已推送，避免重复
        except Exception as e:
            print(f"⚠️ {source}资讯抓取出错：{e}（不影响其他数据源）")

    # 按原始时间戳倒序排序（逻辑不变）
    all_news.sort(key=lambda x: -x[0])
    news_html_list = []  # 存储每条资讯的HTML代码

    # 生成带双序号+🔗符号的资讯列表（逻辑不变）
    for news in all_news:
        timestamp, source, show_time, title, link, _ = news
        # 全局序号+1（连续标序）
        global_counter += 1
        # 分源序号+1（各自独立）
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
        # 邮件主题：第一个圈的月日，用北京时间（核心修改点）
        bj_date = datetime.now().strftime("%m-%d")
        email_title = f"快讯 | {bj_date}"  # 对应截图中“快讯 12-14”的格式
        send_email(email_title, final_content)
    else:
        print("ℹ️  暂无新资讯，本次不推送邮件")

# 执行脚本
if __name__ == "__main__":
    fetch_rss()


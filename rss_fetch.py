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

# 数据源配置（不用改）
RSS_SOURCES = [
    ("https://reutersnew.buzzing.cc/feed.xml", "路透社"),
    ("https://bloombergnew.buzzing.cc/feed.xml", "彭博社")
]

# 自动记录已推送内容（防重复）
def get_pushed_ids():
    if not os.path.exists("pushed_ids.txt"):
        return set()
    with open("pushed_ids.txt", "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

# 自动保存已推送内容（防重复）
def save_pushed_id(id):
    with open("pushed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{id}\n")

# 自动发送邮件（固定配置）
def send_email(subject, content):
    msg = MIMEText(content, "html", "utf-8")
    msg["From"] = QQ_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)
        smtp.login(QQ_EMAIL, QQ_AUTH_CODE)
        smtp.sendmail(QQ_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        print("邮件推送成功！")
    except Exception as e:
        print(f"推送失败：{e}")

# 提取信息源原始精确时分（仅XX:XX格式）
def get_source_hour_min(content):
    try:
        content = html.unescape(content)
        content = content.replace("\n", "").replace("\r", "").replace("\t", "").strip()
        # 匹配核心时分格式
        patterns = [r'>\s*(\d{2}:\d{2})\s*<', r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>', r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"']
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    except:
        return None

# 提取资讯的完整时间（年-月-日 HH:MM，用于排序）+ 展示时间（月-日 HH:MM）
def get_news_full_time(entry):
    try:
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            # 无时间字段则返回当前时间
            now = datetime.now()
            return now.timestamp(), now.strftime("%m-%d %H:%M")
        # 解析ISO格式时间
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        # 排序用时间戳，展示用月-日 时分
        return time_obj.timestamp(), time_obj.strftime("%m-%d %H:%M")
    except:
        # 解析失败返回当前时间
        now = datetime.now()
        return now.timestamp(), now.strftime("%m-%d %H:%M")

# 核心功能：全显月日时分+去分类+按最新时间排序
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 存储格式：(排序时间戳, 展示时间, 资讯内容)

    # 循环抓取两个数据源
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                entry_id = entry.get("id", "").strip()
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 基础筛选：未推送+有ID+有标题+有有效链接
                if (entry_id not in pushed_ids and entry_id and title and link.startswith(("http", "https"))):
                    # 步骤1：提取信息源精确时分
                    source_hm = get_source_hour_min(content)
                    # 步骤2：提取资讯完整时间（排序戳+默认展示时间）
                    sort_timestamp, default_show_time = get_news_full_time(entry)
                    
                    # 最终展示时间：有信息源时分则替换默认时分，日期保留
                    if source_hm:
                        # 拆分默认展示时间的月-日，拼接信息源时分
                        md_part = default_show_time.split(" ")[0]
                        final_show_time = f"{md_part} {source_hm}"
                        # 重新生成排序戳（确保信息源时分的时间精准）
                        final_sort_time = datetime.strptime(f"{datetime.now().year}-{final_show_time}", "%Y-%m-%d %H:%M").timestamp()
                    else:
                        final_show_time = default_show_time
                        final_sort_time = sort_timestamp

                    # 生成资讯内容
                    news_content = f"<li>［{final_show_time} {source}］{title} 👉 <a href='{link}'>原文链接</a></li>"
                    all_news.append((final_sort_time, final_show_time, news_content))
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 按时间戳倒序排序（最新的资讯置顶，绝对精准）
    all_news.sort(key=lambda x: x[0], reverse=True)

    # 整理邮件正文
    email_content = []
    # 抬头：最新资讯的展示时间
    latest_show_time = all_news[0][1] if all_news else datetime.now().strftime("%m-%d %H:%M")
    email_content.append(f"📩 最新资讯推送（{latest_show_time}）")
    email_content.append("<ul style='line-height: 1.8; padding-left: 20px;'>")

    # 加入排序后的资讯
    for _, _, content in all_news:
        email_content.append(content)
    email_content.append("</ul>")

    # 发送邮件
    if all_news:
        final_content = "\n".join(email_content)
        email_title = f"资讯推送 | {datetime.now().strftime('%m-%d %H:%M')}"
        send_email(email_title, final_content)
    else:
        print("ℹ️  暂无新资讯，不推送")

# 执行脚本
if __name__ == "__main__":
    fetch_rss()


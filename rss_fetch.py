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

# 自动记录已推送内容（防重复，不用管）
def get_pushed_ids():
    if not os.path.exists("pushed_ids.txt"):
        return set()
    with open("pushed_ids.txt", "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

# 自动保存已推送内容（防重复，不用管）
def save_pushed_id(id):
    with open("pushed_ids.txt", "a", encoding="utf-8") as f:
        f.write(f"{id}\n")

# 自动发送邮件（固定配置，不用改）
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

# 核心1：提取信息源原始确切分时（仅XX:XX，和信息源完全一致）
def get_source_exact_hm(content):
    try:
        content = html.unescape(content)
        content = content.replace("\n", "").replace("\r", "").replace("\t", "").strip()
        # 匹配信息源所有可能的分时格式，优先提取
        patterns = [
            r'>\s*(\d{2}:\d{2})\s*<',  # 核心格式：>17:35<
            r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>',  # 标签格式：<time>17:35</time>
            r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"'  # 属性格式：datetime="xxxT17:35:00Z"
        ]
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None  # 提取不到返回空，后续显月日
    except:
        return None

# 核心2：提取资讯月日（仅MM-DD，无年份/时分）
def get_news_md_date(entry):
    try:
        # 从资讯自带的时间字段提取日期
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            return datetime.now().strftime("%m-%d")  # 无字段则显当前月日
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return time_obj.strftime("%m-%d")
    except:
        return datetime.now().strftime("%m-%d")  # 解析失败显当前月日

# 核心3：抓资讯+智能显时间+按信息源更新顺序排序
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 直接按信息源更新顺序存储，不额外排序

    # 循环抓取两个数据源（顺序不影响，均按各自源更新顺序提取）
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            # feed.entries本身就是信息源的更新顺序（最新资讯排在最前面），直接循环即可
            for entry in feed.entries:
                entry_id = entry.get("id", "").strip()
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 严格筛选：未推送+有有效ID+有标题+有可访问链接（过滤无效内容）
                if (entry_id not in pushed_ids 
                    and entry_id 
                    and title != "" 
                    and link.startswith(("http", "https"))):
                    
                    # 智能判断显示时间：有分时显分时，无则显月日
                    exact_hm = get_source_exact_hm(content)
                    if exact_hm:
                        show_time = exact_hm  # 有信息源分时：显XX:XX
                    else:
                        show_time = get_news_md_date(entry)  # 无分时：显MM-DD
                    
                    # 生成统一格式的资讯内容
                    news_content = f"<li>［{show_time} {source}］{title} 👉 <a href='{link}' target='_blank'>原文链接</a></li>"
                    # 按信息源更新顺序添加（feed.entries默认最新在前，直接append就是正确顺序）
                    all_news.append(news_content)
                    # 记录已推送，避免重复
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 按信息源更新顺序整理邮件（不额外排序，保持原始更新顺序）
    email_content = []
    # 邮件抬头：用第一条资讯的时间（最新资讯的时间）
    if all_news:
        # 提取第一条资讯的时间（从内容中截取，确保抬头和最新资讯一致）
        first_news = all_news[0]
        time_match = re.search(r'［(\S+) ', first_news)
        latest_time = time_match.group(1) if time_match else datetime.now().strftime("%m-%d")
        email_content.append(f"📩 最新资讯推送（{latest_time}）")
        email_content.append("<ul style='line-height: 1.9; padding-left: 22px; margin: 8px 0;'>")
        email_content.extend(all_news)  # 直接添加按信息源顺序排列的资讯
        email_content.append("</ul>")

    # 有新资讯才推送，不发空邮件
    if all_news:
        final_content = "\n".join(email_content)
        email_title = f"资讯推送 | {datetime.now().strftime('%m-%d')}"
        send_email(email_title, final_content)
    else:
        print("ℹ️  暂无新资讯，本次不推送")

# 执行脚本（不用改）
if __name__ == "__main__":
    fetch_rss()


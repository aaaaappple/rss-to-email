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

# 数据源配置（新增权重：数字越小，时间相同时优先级越高）
RSS_SOURCES = [
    ("https://reutersnew.buzzing.cc/feed.xml", "路透社", 1),  # 权重1：优先
    ("https://bloombergnew.buzzing.cc/feed.xml", "彭博社", 2)   # 权重2：次优先
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

# 核心3：提取资讯原始更新时间戳（用于跨源混合排序）
def get_source_update_timestamp(entry):
    try:
        # 优先用entry的updated/published字段（信息源原始更新时间）
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            return datetime.now().timestamp()  # 无时间则用当前时间戳
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return time_obj.timestamp()  # 返回时间戳（数字越大，更新越新）
    except:
        return datetime.now().timestamp()  # 解析失败用当前时间戳

# 核心4：抓资讯+智能显时间+跨源按原始更新时间混合排序（含时间相同规则）
def fetch_rss():
    pushed_ids = get_pushed_ids()
    # 存储：(信息源原始更新时间戳, 数据源权重, 资讯内容) → 权重用于时间相同时排序
    all_news_with_info = []

    # 循环抓取两个数据源（新增权重参数weight）
    for rss_url, source, weight in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
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
                    
                    # 生成资讯内容
                    news_content = f"<li>［{show_time} {source}］{title} 👉 <a href='{link}' target='_blank'>原文链接</a></li>"
                    # 提取信息源原始更新时间戳
                    update_timestamp = get_source_update_timestamp(entry)
                    # 存入列表（时间戳+权重+内容）→ 权重用于时间相同时排序
                    all_news_with_info.append((update_timestamp, weight, news_content))
                    # 记录已推送，避免重复
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 关键排序逻辑：1. 时间戳倒序（优先，更新晚的在前）；2. 权重正序（时间相同时，权重小的优先）
    all_news_with_info.sort(key=lambda x: (-x[0], x[1]))
    # 提取排序后的纯资讯内容
    sorted_news = [content for _, _, content in all_news_with_info]

    # 按混合排序后的顺序整理邮件
    email_content = []
    # 邮件抬头：用第一条资讯的时间（最新资讯的时间）
    if sorted_news:
        first_news = sorted_news[0]
        time_match = re.search(r'［(\S+) ', first_news)
        latest_time = time_match.group(1) if time_match else datetime.now().strftime("%m-%d")
        email_content.append(f"📩 最新资讯推送（{latest_time}）")
        email_content.append("<ul style='line-height: 1.9; padding-left: 22px; margin: 8px 0;'>")
        email_content.extend(sorted_news)  # 添加混合排序后的资讯
        email_content.append("</ul>")

    # 有新资讯才推送，不发空邮件
    if sorted_news:
        final_content = "\n".join(email_content)
        email_title = f"资讯推送 | {datetime.now().strftime('%m-%d')}"
        send_email(email_title, final_content)
    else:
        print("ℹ️  暂无新资讯，本次不推送")

# 执行脚本（不用改）
if __name__ == "__main__":
    fetch_rss()


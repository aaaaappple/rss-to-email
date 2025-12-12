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

# 提取资讯的发布日期（仅MM-DD格式，无年份）
def get_news_date_md(entry):
    try:
        time_str = entry.get("updated", entry.get("published", ""))
        if not time_str:
            return None
        # 解析为日期对象，仅提取月-日
        time_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return time_obj.strftime("%m-%d")  # 关键修改：仅保留月和日
    except:
        # 解析失败返回当前月-日
        return datetime.now().strftime("%m-%d")

# 核心功能：按规则展示时间+去分类+排序
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 存储格式：(排序用时间戳, 展示用时间, 资讯内容)

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
                    # 步骤2：提取资讯发布月-日
                    news_md = get_news_date_md(entry)
                    if not news_md:
                        print(f"⚠️  {source}《{title}》无法提取日期，跳过")
                        continue

                    # 补充完整年份用于排序（仅排序用，不展示）
                    current_year = datetime.now().year
                    news_date_full = f"{current_year}-{news_md}"

                    # 确定展示用时间和排序用时间戳
                    if source_hm:
                        show_time = source_hm  # 有时分，仅展示时分
                        # 排序戳：完整日期+时分（精准排序）
                        sort_time = datetime.strptime(f"{news_date_full} {source_hm}", "%Y-%m-%d %H:%M").timestamp()
                    else:
                        show_time = news_md  # 无时分，仅展示月-日
                        # 排序戳：完整日期+23:59（同日期无时分的排最后）
                        sort_time = datetime.strptime(f"{news_date_full} 23:59", "%Y-%m-%d %H:%M").timestamp()

                    # 生成资讯内容
                    news_content = f"<li>［{show_time} {source}］{title} 👉 <a href='{link}'>原文链接</a></li>"
                    all_news.append((sort_time, show_time, news_content))
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 按时间戳倒序排序（最新的在前，同日期时分优先于无时分）
    all_news.sort(key=lambda x: x[0], reverse=True)

    # 整理邮件正文
    email_content = []
    # 抬头：最新资讯的展示时间（时分/月-日）
    latest_show_time = all_news[0][1] if all_news else "无新资讯"
    email_content.append(f"📩 最新资讯推送（{latest_show_time}）")
    email_content.append("<ul style='line-height: 1.8; padding-left: 20px;'>")

    # 加入排序后的资讯
    for _, _, content in all_news:
        email_content.append(content)
    email_content.append("</ul>")

    # 发送邮件
    if all_news:
        final_content = "\n".join(email_content)
        email_title = f"资讯推送 | {datetime.now().strftime('%m-%d')}"  # 标题也显月-日
        send_email(email_title, final_content)
    else:
        print("ℹ️  暂无新资讯，不推送")

# 执行脚本
if __name__ == "__main__":
    fetch_rss()


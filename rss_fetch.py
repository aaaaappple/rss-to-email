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

# 提取信息源原始精准时间
def get_source_exact_time(entry_content):
    try:
        content = html.unescape(entry_content)
        content = content.replace("\n", "").replace("\r", "").strip()
        
        time_match1 = re.search(r'>\s*(\d{2}:\d{2})\s*<', content)
        if time_match1:
            return time_match1.group(1).strip()
        
        time_match2 = re.search(r'<time[^>]*>\s*(\d{2}:\d{2})\s*</time>', content, re.IGNORECASE)
        if time_match2:
            return time_match2.group(1).strip()
        
        time_match3 = re.search(r'datetime="[^"]*T(\d{2}:\d{2}):\d{2}[^"]*"', content)
        if time_match3:
            return time_match3.group(1).strip()
        
        return ""
    except:
        return ""

# 核心功能：抓新资讯+合并去分类+按时间排序
def fetch_rss():
    pushed_ids = get_pushed_ids()
    all_news = []  # 合并所有资讯，不再分来源

    # 循环抓取两个数据源
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                entry_id = entry.get("id", "")
                title = entry.get("title", "无标题")
                updated_time = entry.get("updated", "")
                原文链接 = entry.get("link", "无原文链接")
                entry_content = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

                # 只推没发过的新内容
                if entry_id not in pushed_ids and title and updated_time:
                    # 提取信息源精准时间
                    显示时间 = get_source_exact_time(entry_content)
                    if not 显示时间:
                        try:
                            time_obj = datetime.fromisoformat(updated_time.replace("Z", "+00:00"))
                            显示时间 = time_obj.strftime("%H:%M")
                        except:
                            显示时间 = "未知时间"
                    
                    # 存储（时间+内容）元组，用于后续排序
                    单条内容 = f"<li>［{显示时间} {source}］{title} 👉 <a href='{原文链接}'>原文链接</a></li><br>"
                    all_news.append((显示时间, 单条内容))  # 元组格式：(时间, 内容)
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 按时间倒序排序（最新的在前）
    # 处理"未知时间"，放到最后；有效时间按HH:MM降序排列
    def sort_key(item):
        time_str = item[0]
        if time_str == "未知时间":
            return ("00:00",)  # 未知时间排最后
        return (time_str,)
    all_news.sort(key=sort_key, reverse=True)

    # 整理邮件正文（无分类，统一展示）
    邮件内容 = []
    当前推送时间 = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 抬头按你之前要求：年月日+最新资讯时分（无重复第二行）
    最新时间 = all_news[0][0] if all_news else 当前推送时间.split(" ")[1]
    邮件内容.append(f"📩 最新资讯推送（{datetime.now().strftime('%Y-%m-%d')} {最新时间}）\n")

    # 加入排序后的所有资讯
    if all_news:
        邮件内容.append("<ul>")
        for _, content in all_news:  # 只取内容，时间已在内容里展示
            邮件内容.append(content)
        邮件内容.append("</ul>")

    # 发送邮件
    if all_news:
        最终邮件内容 = "\n".join(邮件内容)
        邮件标题 = f"资讯推送 | {当前推送时间}"
        send_email(邮件标题, 最终邮件内容)
    else:
        print("暂无新资讯，不推送")

# 执行脚本
if __name__ == "__main__":
    fetch_rss()


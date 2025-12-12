import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

# ---------------------- 小白必改！只改这3行！其他不动！----------------------
QQ_EMAIL = "1047372945@qq.com"  # 例：123456@qq.com（发邮件的邮箱）
QQ_AUTH_CODE = "excnvmaryozwbech"  # 前面存备忘录的授权码，比如abcdefghijklmno
RECEIVER_EMAIL = "1047372945@qq.com"  # 直接填上面的QQ邮箱（自己收最省事）
# ---------------------------------------------------------------------------

# 数据源配置（不用改，自动抓路透社+彭博社）
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

# 自动发送邮件（不用改，固定配置）
def send_email(subject, content):
    msg = MIMEText(content, "html", "utf-8")
    msg["From"] = QQ_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject

    try:
        smtp = smtplib.SMTP_SSL("smtp.qq.com", 465)  # QQ邮箱固定地址
        smtp.login(QQ_EMAIL, QQ_AUTH_CODE)
        smtp.sendmail(QQ_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        print("邮件推送成功！")
    except Exception as e:
        print(f"推送失败：{e}")

# 核心功能：抓新资讯+整理格式（分来源+带链接，简洁不杂乱）
def fetch_rss():
    pushed_ids = get_pushed_ids()
    路透社资讯 = []
    彭博社资讯 = []

    # 循环抓取两个数据源
    for rss_url, source in RSS_SOURCES:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                entry_id = entry.get("id", "")
                title = entry.get("title", "无标题")
                updated_time = entry.get("updated", "")
                原文链接 = entry.get("link", "无原文链接")  # 自动抓链接

                # 只推没发过的新内容（去重）
                if entry_id not in pushed_ids and title and updated_time:
                    # 格式化时间（只显示 小时:分钟，简洁）
                    try:
                        time_obj = datetime.fromisoformat(updated_time.replace("Z", "+00:00"))
                        显示时间 = time_obj.strftime("%H:%M")
                    except:
                        显示时间 = "未知时间"
                    # 单条资讯格式：［时间 来源］标题 | 原文链接（清晰不乱）
                    单条内容 = f"<li>［{显示时间} {source}］{title} 👉 <a href='{原文链接}'>原文链接</a></li><br>"

                    # 按来源分类存放
                    if source == "路透社":
                        路透社资讯.append(单条内容)
                    else:
                        彭博社资讯.append(单条内容)
                    # 记录已推送，下次不重复
                    save_pushed_id(entry_id)
        except Exception as e:
            print(f"{source}抓取出错：{e}")

    # 整理邮件正文（有新内容才发，不发空邮件）
    邮件内容 = []
    当前推送时间 = datetime.now().strftime("%Y-%m-%d %H:%M")
    邮件内容.append(f"📩 最新资讯推送（{当前推送时间}）\n")

    # 加路透社内容（有更新才显示）
    if 路透社资讯:
        邮件内容.append("<h3>🔸 路透社更新</h3>")
        邮件内容.append("<ul>")  # 开启无序列表
        邮件内容.extend(路透社资讯)  # 加入所有路透社资讯
        邮件内容.append("</ul><br>")  # 关闭列表+空行


  
    # 加彭博社内容（有更新才显示）
    if 彭博社资讯:
        邮件内容.append("<h3>🔸 彭博社更新</h3>")
        邮件内容.append("<ul>")  # 开启无序列表
        邮件内容.extend(彭博社资讯)  # 加入所有彭博社资讯
        邮件内容.append("</ul>")  # 关闭列表


    # 发送邮件
    if 路透社资讯 or 彭博社资讯:
        最终邮件内容 = "\n".join(邮件内容)
        邮件标题 = f"资讯推送 | {当前推送时间}（路透社+彭博社）"
        send_email(邮件标题, 最终邮件内容)

# 执行脚本
if __name__ == "__main__":
    fetch_rss()

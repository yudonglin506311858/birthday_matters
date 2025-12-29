# -*- coding: utf-8 -*-

import json
import datetime
import threading
import time
import schedule
import tkinter as tk
from tkinter import messagebox
from plyer import notification
from lunardate import LunarDate

# =========================
# 文件路径
# =========================

DATA_FILE = "birthdays.json"
CONFIG_FILE = "config.json"
APP_NAME = "🎂 Birthday Matters"

# =========================
# 读取配置
# =========================

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

config = load_json(CONFIG_FILE, {})
birthdays = load_json(DATA_FILE, {})

LANG = config.get("language", "zh")
NOTIFY_TIME = config.get("notify_time", "09:00")
REMIND_RULES = {
    int(k): v for k, v in config.get("remind_rules", {}).items()
}

# =========================
# 文案
# =========================

TEXT = {
    "zh": {
        "name": "姓名",
        "date": "生日 (YYYY-MM-DD)",
        "lunar": "农历生日",
        "priority": "重要性（1–5 星）",
        "add": "添加生日",
        "delete": "删除选中",
        "empty_name": "姓名不能为空",
        "date_error": "日期格式应为 YYYY-MM-DD"
    }
}

T = TEXT[LANG]

# =========================
# 数据保存
# =========================

def save_birthdays():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(birthdays, f, ensure_ascii=False, indent=2)

# =========================
# 日期计算
# =========================

def get_next_birthday(date_str, lunar):
    today = datetime.date.today()

    if lunar:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        lunar_date = LunarDate.fromSolarDate(d.year, d.month, d.day)
        solar = lunar_date.toSolarDate(today.year)
        if solar < today:
            solar = lunar_date.toSolarDate(today.year + 1)
        return solar
    else:
        d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        this_year = d.replace(year=today.year)
        return this_year if this_year >= today else d.replace(year=today.year + 1)

# =========================
# 通知逻辑
# =========================

def should_notify(days_left, priority):
    return days_left in REMIND_RULES.get(priority, [0])

import sys
if sys.platform.startswith("win"):
    import winsound

def notify(name, days_left, priority):
    stars = "⭐" * priority  # 用星星显示重要性
    if days_left == 0:
        msg = f"🎉 今天是 {name} 的生日！ {stars}"
    else:
        msg = f"🎈 {name} 的生日还有 {days_left} 天 {stars}"

    # ---------------------
    # 1️⃣ 桌面通知
    # ---------------------
    notification.notify(
        title=APP_NAME,
        message=msg,
        timeout=10
    )

    # ---------------------
    # 2️⃣ 弹窗提醒
    # ---------------------
    try:
        root_temp = tk.Tk()
        root_temp.withdraw()  # 隐藏主窗口
        messagebox.showinfo(APP_NAME, msg)
        root_temp.destroy()
    except:
        pass  # 防止线程里报错

    # ---------------------
    # 3️⃣ 声音提醒（仅 Windows）
    # ---------------------
    if sys.platform.startswith("win"):
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

def check_birthdays():
    today = datetime.date.today()
    for name, info in birthdays.items():
        next_bd = get_next_birthday(info["date"], info["lunar"])
        days_left = (next_bd - today).days
        if should_notify(days_left, info["priority"]):
            notify(name, days_left, info["priority"])

# =========================
# 定时线程
# =========================

def scheduler_loop():
    schedule.every().day.at(NOTIFY_TIME).do(check_birthdays)
    while True:
        schedule.run_pending()
        time.sleep(60)

# =========================
# GUI
# =========================

def add_birthday():
    name = name_entry.get().strip()
    date = date_entry.get().strip()
    lunar = lunar_var.get()
    priority = priority_var.get()

    if not name:
        messagebox.showerror(APP_NAME, T["empty_name"])
        return

    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except:
        messagebox.showerror(APP_NAME, T["date_error"])
        return

    birthdays[name] = {
        "date": date,
        "lunar": lunar,
        "priority": priority
    }
    save_birthdays()
    refresh_list()

def delete_birthday():
    sel = listbox.curselection()
    if not sel:
        return
    name = listbox.get(sel[0]).split(" | ")[0]
    birthdays.pop(name, None)
    save_birthdays()
    refresh_list()

def refresh_list():
    listbox.delete(0, tk.END)
    for name, info in sorted(
        birthdays.items(),
        key=lambda x: -x[1]["priority"]
    ):
        tag = "🌙 农历" if info["lunar"] else "📅 公历"
        stars = "⭐" * info["priority"]
        listbox.insert(
            tk.END,
            f"{name} | {info['date']} | {tag} | {stars}"
        )

# =========================
# 启动 GUI
# =========================

root = tk.Tk()
root.title(APP_NAME)
root.geometry("500x540")

tk.Label(root, text=T["name"]).pack()
name_entry = tk.Entry(root)
name_entry.pack(fill=tk.X, padx=20)

tk.Label(root, text=T["date"]).pack()
date_entry = tk.Entry(root)
date_entry.pack(fill=tk.X, padx=20)

lunar_var = tk.BooleanVar()
tk.Checkbutton(root, text=T["lunar"], variable=lunar_var).pack()

tk.Label(root, text=T["priority"]).pack()
priority_var = tk.IntVar(value=3)
pf = tk.Frame(root)
pf.pack()

for i in range(1, 6):
    tk.Radiobutton(
        pf,
        text="⭐" * i,
        variable=priority_var,
        value=i
    ).pack(side=tk.LEFT)

tk.Button(root, text=T["add"], command=add_birthday).pack(pady=5)
tk.Button(root, text=T["delete"], command=delete_birthday).pack(pady=5)

# 使用 Emoji 字体（防止 Windows 方框）
listbox = tk.Listbox(
    root,
    width=65,
    font=("Segoe UI Emoji", 10)
)
listbox.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

refresh_list()

threading.Thread(target=scheduler_loop, daemon=True).start()
root.mainloop()

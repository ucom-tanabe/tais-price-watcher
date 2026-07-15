import json
import os
import re
import sys

import requests

URL = "https://www.techno-aids.or.jp/tekisei/index.shtml"
STATE_FILE = "state.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# お知らせは「2026.07.01」のような日付＋タイトルの形式で並んでいるので、
# その中から「全国平均貸与価格」というキーワードを含む行だけを拾う。
PATTERN = re.compile(
    r"(\d{4}\.\d{2}\.\d{2})[^\d\w]{0,5}([^\n<]{5,150}?全国平均貸与価格[^\n<]{0,100})"
)


def fetch_announcements():
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    # このサイトはShift_JIS系のエンコーディングのことがあるため自動判定させる
    resp.encoding = resp.apparent_encoding or "cp932"
    html = resp.text

    seen = set()
    announcements = []
    for date, title in PATTERN.findall(html):
        title = re.sub(r"\s+", " ", title).strip()
        key = f"{date} {title}"
        if key not in seen:
            seen.add(key)
            announcements.append(key)
    return announcements


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notify_discord(new_items):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    lines = "\n".join(f"・{item}" for item in new_items)
    content = (
        "📢 福祉用具の全国平均貸与価格に関する新しいお知らせがありました！\n"
        f"{lines}\n{URL}"
    )
    r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=15)
    r.raise_for_status()


def main():
    current = fetch_announcements()
    if not current:
        print(
            "お知らせを1件も取得できませんでした。"
            "サイトのHTML構造が変わった可能性があるため、check.pyの抽出条件を見直してください。"
        )
        # 誤検知で全件を「新着」扱いしないよう、ここで終了する
        sys.exit(0)

    previous = set(load_state())
    new_items = [item for item in current if item not in previous]

    if new_items:
        print(f"{len(new_items)}件の新着を検知しました。Discordに通知します。")
        notify_discord(new_items)
    else:
        print("更新はありませんでした。")

    save_state(current)


if __name__ == "__main__":
    main()

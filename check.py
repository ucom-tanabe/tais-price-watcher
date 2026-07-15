import json
import os
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.techno-aids.or.jp/tekisei/index.shtml"
STATE_FILE = "state.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def fetch_announcements():
    """
    全国平均貸与価格・貸与価格の上限の表を解析する。
    各行には「pricelistXXXXXX.xlsx」という一覧ファイルへのリンクがあるので、
    これをキーにして各回の発表を識別する。
    """
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = resp.apparent_encoding or "cp932"
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = set()
    announcements = []
    for tr in soup.find_all("tr"):
        links = [a.get("href", "") for a in tr.find_all("a", href=True)]
        pricelist_links = [l for l in links if "pricelist" in l]
        if not pricelist_links:
            continue
        key = pricelist_links[0].rsplit("/", 1)[-1]
        if key in seen:
            continue
        seen.add(key)
        text = tr.get_text(" ", strip=True)
        announcements.append(f"{key} | {text}")
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

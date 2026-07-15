import json
import os
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.techno-aids.or.jp/tekisei/index.shtml"
STATE_FILE = "state.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def fetch_keys():
    """
    ページ内の「pricelistXXXXXX.xlsx」へのリンクを、各回の発表を識別するキーとして使う。
    """
    resp = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = resp.apparent_encoding or "cp932"
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = set()
    keys = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "pricelist" not in href:
            continue
        key = href.rsplit("/", 1)[-1]  # 例: pricelist202610.xlsx
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def load_state_keys():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return None  # ファイルが無い = 初回実行


def save_state_keys(keys):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, ensure_ascii=False, indent=2)


def notify_discord():
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    content = f"📢 福祉用具の全国平均貸与価格が更新されました。\n{URL}"
    r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=15)
    r.raise_for_status()


def main():
    current_keys = fetch_keys()
    if not current_keys:
        print(
            "お知らせを1件も取得できませんでした。"
            "サイトのHTML構造が変わった可能性があるため、check.pyの抽出条件を見直してください。"
        )
        sys.exit(0)

    previous_keys = load_state_keys()

    if previous_keys is None:
        # 初回実行：通知はせず、現状を基準として保存するだけ
        print("初回実行のため、現状を基準として保存しました（通知は行いません）。")
        save_state_keys(current_keys)
        return

    new_keys = [k for k in current_keys if k not in previous_keys]

    if new_keys:
        print(f"{len(new_keys)}件の新着を検知しました。Discordに通知します。")
        notify_discord()
    else:
        print("更新はありませんでした。")

    save_state_keys(current_keys)


if __name__ == "__main__":
    main()

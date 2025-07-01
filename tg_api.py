import requests

with open(".env/tg.key", "r") as f:
    BOT_TOKEN = f.read().strip()

with open(".env/tg_chat_id.key", "r") as f:
    CHAT_ID= int(f.read().strip())

def tg_notify(text):
    if not text:
        print("Empty text submitted")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, json=payload)
    # print(r.status_code, r.text)



def main():
    from main import load_json_today, JSON_DIR, parse_report

    report = load_json_today(f"{JSON_DIR}/daily_report")
    text = parse_report(report)
    tg_notify(text)

if __name__ == "__main__":
    exit(main())

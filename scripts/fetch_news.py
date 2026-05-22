"""
국가인권위원회 인권뉴스·보도자료 자동 수집
NHRC 게시판 API 활용
"""
import requests
import json
import datetime
import os
import re

BASE = "https://www.humanrights.go.kr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": BASE,
}
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")


def fetch_board(url: str, cat: str, max_items: int = 8) -> list[dict]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"[오류] {cat} 수집 실패: {e}")
        return []

    items = []
    # 제목과 날짜를 HTML에서 추출 (NHRC 게시판 공통 패턴)
    titles = re.findall(r'class="title"[^>]*>\s*<a[^>]*>([^<]+)</a>', html)
    dates = re.findall(r'class="date"[^>]*>([^<]+)</a>|class="date">([^<]+)<', html)
    links = re.findall(r'class="title"[^>]*>\s*<a[^>]+href="([^"]+)"', html)

    for i, title in enumerate(titles[:max_items]):
        title = title.strip()
        if not title:
            continue
        date = ""
        if i < len(dates):
            date = (dates[i][0] or dates[i][1]).strip()
        link = ""
        if i < len(links):
            raw = links[i].strip()
            link = BASE + raw if raw.startswith("/") else raw
        if not link:
            link = url

        items.append({"title": title, "date": date, "url": link, "category": cat})

    return items


def main():
    news_url = f"{BASE}/site/program/board/basicboard/list?boardtypeid=24&menuid=002004002&pagesize=10"
    press_url = f"{BASE}/site/program/board/basicboard/list?boardtypeid=39&menuid=002004001&pagesize=10"

    news = fetch_board(news_url, "인권뉴스")
    press = fetch_board(press_url, "보도자료")

    result = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "news": news,
        "press": press,
    }

    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[완료] 뉴스 {len(news)}건, 보도자료 {len(press)}건 저장")


if __name__ == "__main__":
    main()

"""
국가인권위원회 유튜브 채널 최신 영상 자동 수집
YouTube RSS 피드 사용 (API 키 불필요)
"""
import requests
import json
import datetime
import os
import re

CHANNEL_ID = "UCoeG4QtnNXXeMEU94cUBihA"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "videos.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def parse_rss(xml_text: str) -> list[dict]:
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)
    items = []
    for entry in entries:
        vid_match = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", entry)
        title_match = re.search(r"<title>([^<]+)</title>", entry)
        pub_match = re.search(r"<published>([^<]+)</published>", entry)

        if not vid_match or not title_match:
            continue

        vid_id = vid_match.group(1).strip()
        title = title_match.group(1).strip()
        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        pub = pub_match.group(1).strip()[:10] if pub_match else ""

        items.append({
            "id": vid_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "thumbnail": f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg",
            "date": pub,
        })

    return items


def main():
    try:
        resp = requests.get(RSS_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[오류] RSS 요청 실패: {e}")
        return

    items = parse_rss(resp.text)
    if not items:
        print("[경고] 영상 데이터 없음. 기존 파일 유지.")
        return

    # 최신 12개만
    items = items[:12]

    output = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "channel": "https://www.youtube.com/@NHRCkr",
        "count": len(items),
        "items": items,
    }

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[완료] 영상 {len(items)}개를 data/videos.json에 저장했습니다.")


if __name__ == "__main__":
    main()

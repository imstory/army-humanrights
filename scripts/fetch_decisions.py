"""
국가인권위원회 결정례 자동 수집 스크립트
매일 GitHub Actions에서 실행되어 data/decisions.json을 업데이트합니다.
"""
import requests
from bs4 import BeautifulSoup
import json
import datetime
import os
import sys

BASE_URL = "https://case.humanrights.go.kr"
LIST_URL = f"{BASE_URL}/dici/diciList.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": BASE_URL,
}

# 카테고리 키워드 매핑
CATEGORY_MAP = {
    "가혹": "가혹행위",
    "폭행": "가혹행위",
    "구타": "가혹행위",
    "얼차려": "가혹행위",
    "욕설": "가혹행위",
    "성희롱": "성희롱·성폭력",
    "성폭력": "성희롱·성폭력",
    "성추행": "성희롱·성폭력",
    "표현": "표현·종교의 자유",
    "종교": "표현·종교의 자유",
    "집회": "표현·종교의 자유",
    "차별": "평등권·차별",
    "평등": "평등권·차별",
    "여성": "평등권·차별",
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'decisions.json')


def guess_category(title: str) -> str:
    for kw, cat in CATEGORY_MAP.items():
        if kw in title:
            return cat
    return "기타"


def fetch_decisions(page: int = 1) -> list[dict]:
    params = {"pageIndex": page, "searchCondition": "", "searchKeyword": ""}
    try:
        resp = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[오류] 페이지 {page} 요청 실패: {e}", file=sys.stderr)
        return []

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    items = []
    # 결정례 목록 테이블 파싱 (사이트 구조에 따라 선택자 조정 필요)
    rows = soup.select("table tbody tr")
    if not rows:
        # 대안 선택자 시도
        rows = soup.select(".board_list tbody tr, .list_table tbody tr, #listTbody tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # 번호
        num = cols[0].get_text(strip=True)

        # 제목 및 링크
        title_td = cols[1] if len(cols) > 1 else cols[-1]
        a_tag = title_td.find("a")
        title = a_tag.get_text(strip=True) if a_tag else title_td.get_text(strip=True)
        if not title or title == "제목":
            continue

        href = ""
        if a_tag:
            raw_href = a_tag.get("href", "")
            if raw_href.startswith("http"):
                href = raw_href
            elif raw_href.startswith("/"):
                href = BASE_URL + raw_href
            elif raw_href:
                href = f"{BASE_URL}/dici/{raw_href}"

        if not href:
            href = LIST_URL

        # 날짜 (마지막 td)
        date_txt = cols[-1].get_text(strip=True)

        # 결과 (있으면)
        result = ""
        if len(cols) >= 4:
            result = cols[-2].get_text(strip=True)

        category = guess_category(title)

        items.append({
            "id": num,
            "title": title,
            "url": href,
            "category": category,
            "date": date_txt,
            "result": result,
        })

    return items


def main():
    all_items = []
    # 최신 2페이지(40건 내외) 수집
    for page in [1, 2]:
        batch = fetch_decisions(page)
        all_items.extend(batch)
        if not batch:
            break

    # 최신 30건으로 제한
    all_items = all_items[:30]

    # 기존 파일이 있으면 읽어서 items가 0개일 때 덮어쓰지 않음
    if not all_items:
        print("[경고] 수집된 데이터가 없습니다. 기존 파일을 유지합니다.", file=sys.stderr)
        sys.exit(0)

    output = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": LIST_URL,
        "count": len(all_items),
        "items": all_items,
    }

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[완료] 결정례 {len(all_items)}건을 data/decisions.json에 저장했습니다.")


if __name__ == "__main__":
    main()

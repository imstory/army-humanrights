"""
국가인권위원회 결정례 자동 수집 스크립트
매일 GitHub Actions에서 실행되어 data/decisions.json을 업데이트합니다.
AJAX 엔드포인트 사용: https://case.humanrights.go.kr/dici/selectDiciList.do
"""
import requests
import json
import datetime
import os
import sys

BASE_URL = "https://case.humanrights.go.kr"
AJAX_URL = f"{BASE_URL}/dici/selectDiciList.do"
DETAIL_URL = f"{BASE_URL}/dici/diciView.do"
LIST_URL = f"{BASE_URL}/dici/diciList.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": LIST_URL,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 제목 키워드 → 카테고리 매핑
CATEGORY_MAP = [
    (["가혹", "폭행", "구타", "얼차려", "욕설", "기합", "인격비하", "폭언"], "가혹행위"),
    (["성희롱", "성폭력", "성추행", "성적 수치", "성적수치"], "성희롱·성폭력"),
    (["표현", "SNS", "종교", "집회", "결사", "신앙"], "표현·종교의 자유"),
    (["차별", "평등", "여성", "다문화", "장애"], "평등권·차별"),
    (["진급", "보직", "전역", "복귀", "포상", "승진"], "인사·처우"),
    (["휴가", "외출", "외박", "면회"], "휴가·이동의 자유"),
]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "decisions.json")


def guess_category(title: str) -> str:
    for keywords, cat in CATEGORY_MAP:
        for kw in keywords:
            if kw in title:
                return cat
    return "기타"


def fetch_page(page: int) -> list[dict]:
    payload = {
        "pageIndex": str(page),
        "searchCondition": "",
        "searchKeyword": "",
        "dcsnSttCd": "",
        "rghtKindCd": "",
    }
    try:
        resp = requests.post(AJAX_URL, data=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[오류] 페이지 {page} 요청 실패: {e}", file=sys.stderr)
        return []

    result_list = data.get("resultList", [])
    items = []
    for r in result_list:
        doc_id = r.get("DOCID", "")
        title = r.get("SJ", "").strip()
        date = r.get("MTG_DE", "").strip()
        committee = r.get("CMIT_NM", "").strip()
        team = r.get("EXMNR_TEAM_NM", "").strip()

        if not title:
            continue

        # 결정례 상세 URL 생성
        url = f"{DETAIL_URL}?docId={doc_id}" if doc_id else LIST_URL

        category = guess_category(title)

        items.append({
            "id": doc_id,
            "title": title,
            "url": url,
            "category": category,
            "date": date,
            "committee": committee,
            "team": team,
            "result": "",  # API에 결과(인용/각하) 필드 없음
        })
    return items


def main():
    all_items = []
    seen_ids = set()

    # 최신 3페이지 수집 (중복 제거)
    for page in range(1, 4):
        batch = fetch_page(page)
        new_items = []
        for item in batch:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                new_items.append(item)
        all_items.extend(new_items)
        print(f"[페이지 {page}] {len(batch)}건 수집, {len(new_items)}건 신규")
        if not batch:
            break

    if not all_items:
        print("[경고] 수집된 데이터가 없습니다. 기존 파일을 유지합니다.", file=sys.stderr)
        sys.exit(0)

    # 최신 30건으로 제한
    all_items = all_items[:30]

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

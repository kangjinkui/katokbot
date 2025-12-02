"""
검색 기능 테스트 스크립트
------------------------
동의어 사전 기반 검색 기능을 테스트합니다.
"""

import sys
import os

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

from search_utils import load_synonyms, expand_query, search_in_text, calculate_relevance_score


def test_load_synonyms():
    """동의어 사전 로드 테스트"""
    print("=" * 50)
    print("1. 동의어 사전 로드 테스트")
    print("=" * 50)

    synonyms = load_synonyms("data/synonyms.json")
    print(f"로드된 동의어 수: {len(synonyms)}개")
    print(f"예시: QR코드 -> {synonyms.get('QR코드', [])}")
    print(f"예시: 정산 -> {synonyms.get('정산', [])}")
    print()


def test_expand_query():
    """쿼리 확장 테스트"""
    print("=" * 50)
    print("2. 쿼리 확장 테스트")
    print("=" * 50)

    synonyms = load_synonyms("data/synonyms.json")

    test_queries = [
        "QR코드",
        "큐알코드",
        "정산업무",
        "정산 업무",
        "식권",
        "회원가입",
        "제로페이",
    ]

    for query in test_queries:
        expanded = expand_query(query, synonyms)
        print(f"쿼리: '{query}'")
        print(f"확장: {expanded}")
        print()


def test_search_in_text():
    """텍스트 검색 테스트"""
    print("=" * 50)
    print("3. 텍스트 검색 테스트")
    print("=" * 50)

    synonyms = load_synonyms("data/synonyms.json")

    test_cases = [
        ("QR코드", "시스템 도입으로 정산 업무가 얼마나 줄어드나요?"),
        ("정산업무", "시스템 도입으로 정산 업무가 얼마나 줄어드나요?"),
        ("큐알코드", "식권은 QR코드로 발행됩니다."),
        ("식사권", "모든 식권은 QR코드로 발행됩니다."),
    ]

    for query, text in test_cases:
        expanded = expand_query(query, synonyms)
        match = search_in_text(text, expanded)
        print(f"쿼리: '{query}'")
        print(f"텍스트: '{text}'")
        print(f"확장 쿼리: {expanded[:3]}...")
        print(f"매칭: {'✓ 성공' if match else '✗ 실패'}")
        print()


def test_relevance_score():
    """관련도 점수 계산 테스트"""
    print("=" * 50)
    print("4. 관련도 점수 계산 테스트")
    print("=" * 50)

    synonyms = load_synonyms("data/synonyms.json")

    test_cases = [
        ("정산업무", "시스템 도입으로 정산 업무가 얼마나 줄어드나요?"),
        ("QR코드", "식권은 QR코드로 발행됩니다."),
        ("큐알", "모든 식권은 QR코드로 발행됩니다."),
    ]

    for query, text in test_cases:
        expanded = expand_query(query, synonyms)
        score = calculate_relevance_score(text, expanded, query)
        print(f"쿼리: '{query}'")
        print(f"텍스트: '{text}'")
        print(f"점수: {score:.2f}")
        print()


def test_end_to_end():
    """전체 통합 테스트"""
    print("=" * 50)
    print("5. 전체 통합 테스트 (실제 QA 검색)")
    print("=" * 50)

    import os
    from google_calendar_webhook import search_hanbang_qa

    test_queries = [
        "정산업무",
        "QR코드",
        "큐알코드",
        "회원가입",
        "제로페이",
        "식당 정산",
    ]

    for query in test_queries:
        print(f"\n쿼리: '{query}'")
        print("-" * 40)
        result = search_hanbang_qa(query)
        print(result)
        print()


if __name__ == "__main__":
    test_load_synonyms()
    test_expand_query()
    test_search_in_text()
    test_relevance_score()

    # 전체 통합 테스트 (QA 파일이 있는 경우에만 실행)
    import os
    if os.path.exists("data/hanbang_qa.md"):
        test_end_to_end()
    else:
        print("\n⚠️ data/hanbang_qa.md 파일이 없어 전체 통합 테스트를 건너뜁니다.")

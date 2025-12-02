"""
검색 기능 독립 실행 테스트
-------------------------
Google 라이브러리 의존성 없이 검색 기능만 테스트합니다.
"""

import sys
import os

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

from search_utils import load_synonyms, expand_query, search_in_text, calculate_relevance_score


def search_hanbang_qa(query: str) -> str:
    """
    한방식권 Q&A 문서에서 쿼리를 검색합니다.
    """
    synonyms = load_synonyms("data/synonyms.json")
    expanded_queries = expand_query(query, synonyms)

    qa_file = "data/hanbang_qa.md"
    if not os.path.exists(qa_file):
        return "❌ Q&A 문서를 찾을 수 없습니다."

    with open(qa_file, "r", encoding="utf-8") as f:
        content = f.read()

    sections = content.split("\n##")
    results = []

    for section in sections:
        lines = section.split("\n")
        for line in lines:
            if search_in_text(line, expanded_queries):
                score = calculate_relevance_score(line, expanded_queries, query)
                results.append((score, line.strip()))

    if not results:
        return f"❌ '{query}'에 대한 검색 결과가 없습니다.\n💡 다른 키워드로 검색해보세요."

    results.sort(reverse=True, key=lambda x: x[0])

    output = [f"🔍 '{query}' 검색 결과 (확장: {', '.join(expanded_queries[:3])}...):\n"]
    for score, line in results[:5]:
        if line and not line.startswith("|:--"):
            output.append(f"• {line}")

    return "\n".join(output)


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("한방식권 Q&A 검색 테스트")
    print("=" * 60)
    print()

    test_queries = [
        "정산업무",
        "QR코드",
        "큐알코드",
        "회원가입",
        "제로페이",
        "식당 정산",
        "정산",
        "식권",
    ]

    for query in test_queries:
        print(f"\n{'=' * 60}")
        print(f"쿼리: '{query}'")
        print("=" * 60)
        result = search_hanbang_qa(query)
        print(result)
        print()


if __name__ == "__main__":
    main()

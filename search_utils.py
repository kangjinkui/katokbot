"""
검색 유틸리티 모듈
-------------------
동의어 사전 기반 쿼리 확장 및 검색 기능을 제공합니다.
"""

import json
import os
from typing import List, Set


def load_synonyms(filepath: str = "data/synonyms.json") -> dict:
    """
    동의어 사전을 JSON 파일에서 로드합니다.

    Args:
        filepath: 동의어 사전 JSON 파일 경로

    Returns:
        동의어 사전 딕셔너리
    """
    if not os.path.exists(filepath):
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def expand_query(query: str, synonyms: dict) -> List[str]:
    """
    입력 쿼리를 동의어 사전을 사용하여 확장합니다.

    Args:
        query: 검색 쿼리
        synonyms: 동의어 사전

    Returns:
        확장된 쿼리 리스트 (원본 쿼리 포함)
    """
    # 원본 쿼리는 항상 포함
    expanded = {query.lower()}

    # 공백 제거 버전도 추가
    no_space = query.replace(" ", "").lower()
    if no_space != query.lower():
        expanded.add(no_space)

    # 동의어 사전에서 매칭되는 단어 찾기
    query_lower = query.lower()
    for key, synonyms_list in synonyms.items():
        key_lower = key.lower()

        # 쿼리가 키에 포함되거나, 키가 쿼리에 포함된 경우
        if query_lower in key_lower or key_lower in query_lower:
            # 원본 키 추가
            expanded.add(key_lower)
            # 모든 동의어 추가
            expanded.update([s.lower() for s in synonyms_list])

        # 쿼리가 동의어 리스트에 있는 경우
        for synonym in synonyms_list:
            if query_lower in synonym.lower() or synonym.lower() in query_lower:
                # 원본 키 추가
                expanded.add(key_lower)
                # 모든 동의어 추가
                expanded.update([s.lower() for s in synonyms_list])
                break

    return list(expanded)


def search_in_text(text: str, queries: List[str]) -> bool:
    """
    텍스트에서 쿼리 리스트 중 하나라도 매칭되는지 확인합니다.

    Args:
        text: 검색 대상 텍스트
        queries: 검색 쿼리 리스트

    Returns:
        매칭 여부
    """
    text_lower = text.lower()
    return any(q in text_lower for q in queries)


def calculate_relevance_score(text: str, queries: List[str], original_query: str) -> float:
    """
    텍스트와 쿼리 리스트의 관련도 점수를 계산합니다.

    Args:
        text: 검색 대상 텍스트
        queries: 확장된 쿼리 리스트
        original_query: 원본 쿼리

    Returns:
        관련도 점수 (0.0 ~ 1.0)
    """
    text_lower = text.lower()
    score = 0.0

    # 원본 쿼리 매칭 시 높은 점수
    if original_query.lower() in text_lower:
        score += 1.0

    # 동의어 매칭 개수에 비례한 점수
    match_count = sum(1 for q in queries if q in text_lower)
    if match_count > 0:
        score += 0.5 + (match_count * 0.1)

    return min(score, 1.0)

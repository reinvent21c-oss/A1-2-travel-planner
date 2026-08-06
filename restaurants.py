"""Kakao Local 맛집 검색 기능."""

import requests

from api_helpers import append_error
from config import KAKAO_LOCAL_API_URL

def search_restaurants(city, kakao_api_key, errors):
    """Kakao Local API에서 추천 지역의 맛집을 최대 5곳 검색한다."""
    query = f"{city} 맛집"

    headers = {
        "Authorization": f"KakaoAK {kakao_api_key}",
    }

    params = {
        "query": query,
        "size": 5,
    }

    try:
        response = requests.get(
            KAKAO_LOCAL_API_URL,
            headers=headers,
            params=params,
            timeout=10,
        )

        if response.status_code in (401, 403):
            append_error(
                errors, "place_search", "AUTH_ERROR",
                f"HTTP {response.status_code}",
            )
            print(
                f"- 오류: 인증 실패({response.status_code}). "
                "Kakao REST API 키와 사용 설정을 확인하세요."
            )
            return []

        if response.status_code == 429:
            append_error(errors, "place_search", "QUOTA_ERROR", "HTTP 429")
            print("- 오류: Kakao API 요청 한도를 초과했습니다.")
            return []

        if not response.ok:
            append_error(
                errors, "place_search", "HTTP_ERROR",
                f"HTTP {response.status_code}",
            )
            print(
                f"- 오류: Kakao API 요청 실패 "
                f"(HTTP {response.status_code})"
            )
            return []

        response_data = response.json()

    except requests.RequestException as error:
        append_error(errors, "place_search", "NETWORK_ERROR", str(error))
        print(f"- 오류: Kakao API 네트워크 오류: {error}")
        return []

    except ValueError as error:
        append_error(errors, "place_search", "PARSE_ERROR", str(error))
        print("- 오류: Kakao API 응답을 JSON으로 읽지 못했습니다.")
        return []

    documents = response_data.get("documents", [])

    if not documents:
        append_error(
            errors, "place_search", "EMPTY_RESULT",
            f"0 results for query={query}",
        )
        print("- 검색 결과 0건")
        return []

    restaurants = []

    for place in documents[:5]:
        try:
            x = float(place["x"]) if place.get("x") else None
            y = float(place["y"]) if place.get("y") else None
        except (TypeError, ValueError):
            x = None
            y = None

        restaurant = {
            "name": place.get("place_name", "이름 없음"),
            "address": (
                place.get("road_address_name")
                or place.get("address_name")
                or "주소 없음"
            ),
            "category": place.get("category_name", ""),
            "url": place.get("place_url", ""),
            "x": x,
            "y": y,
        }

        restaurants.append(restaurant)

    return restaurants

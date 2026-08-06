"""여행 추천 Markdown 리포트 생성 기능."""

import json

import requests

from api_helpers import append_error, extract_api_error_message, extract_gemini_text
from config import GEMINI_API_URL

def build_fallback_report(
    travel_date,
    recommendation_data,
    restaurants_by_city,
    errors,
):
    """Gemini 최종 리포트 실패 시 복수 지역 Markdown을 생성한다."""
    recommendations = recommendation_data.get(
        "recommended_cities",
        [],
    )

    restaurant_map = {
        item.get("city"): item.get("restaurants", [])
        for item in restaurants_by_city
        if isinstance(item, dict)
    }

    lines = [
        f"# {travel_date} 국내 여행 추천 리포트",
        "",
        "## 지역별 여행 추천",
    ]

    if recommendations:
        for city_index, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            city = recommendation.get(
                "city",
                "지역 정보 없음",
            )
            events = recommendation.get("events", [])
            city_restaurants = restaurant_map.get(city, [])

            lines.extend(
                [
                    "",
                    f"### {city_index}. {city}",
                    "",
                    "#### 추천 이유",
                    recommendation.get(
                        "reason",
                        "데이터 없음",
                    ),
                    "",
                    "#### 날씨 요약",
                    recommendation.get(
                        "weather",
                        "데이터 없음",
                    ),
                    "",
                    "#### 행사/축제",
                ]
            )

            if events:
                for event in events:
                    lines.append(f"- {event}")
            else:
                lines.append("데이터 없음")

            lines.extend(
                [
                    "",
                    "#### 맛집 추천",
                ]
            )

            if city_restaurants:
                for restaurant_index, restaurant in enumerate(
                    city_restaurants,
                    start=1,
                ):
                    lines.extend(
                        [
                            f"##### {restaurant_index}. "
                            f"{restaurant.get('name', '이름 없음')}",
                            f"- 주소: "
                            f"{restaurant.get('address', '데이터 없음')}",
                            f"- 분류: "
                            f"{restaurant.get('category', '데이터 없음')}",
                            f"- 링크: "
                            f"{restaurant.get('url', '데이터 없음')}",
                            "",
                        ]
                    )
            else:
                lines.extend(
                    [
                        "데이터 없음",
                        "",
                    ]
                )

            lines.extend(
                [
                    "#### 1일 일정 제안",
                    "- 오전: 데이터 없음",
                    "- 오후: 데이터 없음",
                    "- 저녁: 데이터 없음",
                ]
            )
    else:
        lines.extend(
            [
                "",
                "추천 지역 데이터 없음",
            ]
        )
    lines.extend(
        [
            "",
            "※ 행사·축제 일정은 변경될 수 있으므로 "
            "방문 전에 확인이 필요합니다.",
            "",
            "최종 리포트 생성 API 오류로 인해 "
            "자동 일정 제안을 생성하지 못했습니다.",
            "",
            "## 오류 요약(errors)",
        ]
    )

    if errors:
        for error in errors:
            lines.append(
                f"- [{error.get('step', 'unknown')}/"
                f"{error.get('type', 'UNKNOWN_ERROR')}] "
                f"{error.get('message', '상세 메시지 없음')}"
            )
    else:
        lines.append("오류 없음")

    return "\n".join(lines)


def generate_final_report(
    travel_date,
    recommendation_data,
    restaurants_by_city,
    errors,
    gemini_api_key,
):
    """복수 지역 추천과 지역별 맛집으로 Markdown 리포트를 생성한다."""
    report_data = {
        "travel_date": travel_date,
        "recommendation_data": recommendation_data,
        "restaurants_by_city": restaurants_by_city,
        "errors": errors,
    }

    report_data_text = json.dumps(
        report_data,
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
아래 JSON 데이터를 바탕으로 국내 여행 추천 리포트를 작성하세요.

{report_data_text}

다음 조건을 모두 지켜야 합니다.

1. 결과는 Markdown 형식으로만 작성하세요.
2. Markdown 코드 블록 기호는 사용하지 마세요.
3. 가장 위 제목은 다음 형식으로 작성하세요.
   # {travel_date} 국내 여행 추천 리포트
4. 먼저 다음 제목 아래에 추천 지역 전체를 목록으로 정리하세요.
   ## 추천 지역
5. 그다음 다음 제목을 작성하세요.
   ## 지역별 상세 추천
6. 각 추천 지역을 다음 형식으로 각각 구분하세요.
   ### 1. 지역명
   #### 추천 이유
   #### 날씨 요약
   #### 행사/축제
   #### 맛집 추천
   #### 1일 일정 제안
7. 1일 일정은 각 지역마다 오전, 오후, 저녁으로 나누어 작성하세요.
8. restaurants_by_city에서 지역명이 같은 맛집만 해당 지역에 작성하세요.
9. 맛집 목록이 비어 있으면 '데이터 없음'이라고 작성하세요.
10. 제공된 JSON에 없는 맛집 이름이나 주소는 새로 만들지 마세요.
11. 행사와 축제는 실제 일정이 변경될 수 있음을 안내하세요.
12. 마지막에 다음 제목을 작성하세요.
    ## 오류 요약(errors)
13. 오류 목록이 비어 있으면 '오류 없음'이라고 작성하세요.
"""

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gemini_api_key,
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if not response.ok:
            error_message = extract_api_error_message(response)

            if response.status_code in (401, 403):
                error_type = "AUTH_ERROR"
            elif response.status_code == 429:
                error_type = "QUOTA_ERROR"
            else:
                error_type = "HTTP_ERROR"

            append_error(
                errors,
                "final_report",
                error_type,
                f"HTTP {response.status_code}: {error_message}",
            )

            print(
                f"최종 리포트 생성 오류: "
                f"HTTP {response.status_code}"
            )
            print(f"- 상세: {error_message}")
            print("- 로컬 대체 리포트를 생성합니다.")

            return build_fallback_report(
                travel_date,
                recommendation_data,
                restaurants_by_city,
                errors,
            )

        return extract_gemini_text(response.json())

    except (ValueError, KeyError, IndexError, TypeError) as error:
        append_error(errors, "final_report", "RESPONSE_ERROR", str(error))

        print(
            "Gemini 응답에서 올바른 최종 리포트를 "
            "찾지 못했습니다."
        )
        print("- 로컬 대체 리포트를 생성합니다.")

        return build_fallback_report(
            travel_date,
            recommendation_data,
            restaurants_by_city,
            errors,
        )

    except requests.RequestException as error:
        append_error(errors, "final_report", "NETWORK_ERROR", str(error))

        print(f"최종 리포트 생성 네트워크 오류: {error}")
        print("- 로컬 대체 리포트를 생성합니다.")

        return build_fallback_report(
            travel_date,
            recommendation_data,
            restaurants_by_city,
            errors,
        )

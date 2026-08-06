"""Gemini 여행지 추천 기능."""

import json

import requests

from api_helpers import extract_api_error_message, extract_gemini_text
from config import GEMINI_API_URL

def validate_recommendation_data(data):
    """Gemini 복수 지역 추천 JSON의 필수 키와 자료형을 검증한다."""
    if not isinstance(data, dict):
        raise ValueError(
            "추천 응답의 최상위 값은 JSON 객체여야 합니다."
        )

    recommended_cities = data.get("recommended_cities")

    if (
        not isinstance(recommended_cities, list)
        or not 2 <= len(recommended_cities) <= 3
    ):
        raise ValueError(
            "recommended_cities는 2~3개 지역 객체를 담은 배열이어야 합니다."
        )

    checked_city_names = set()

    for index, recommendation in enumerate(
        recommended_cities,
        start=1,
    ):
        if not isinstance(recommendation, dict):
            raise ValueError(
                f"{index}번째 추천 지역은 JSON 객체여야 합니다."
            )

        for key in ("city", "weather", "reason"):
            value = recommendation.get(key)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{index}번째 추천의 {key}는 "
                    "비어 있지 않은 문자열이어야 합니다."
                )

        events = recommendation.get("events")

        if not isinstance(events, list) or not 1 <= len(events) <= 3:
            raise ValueError(
                f"{index}번째 추천의 events는 "
                "1~3개의 문자열을 담은 배열이어야 합니다."
            )

        if not all(
            isinstance(event, str) and event.strip()
            for event in events
        ):
            raise ValueError(
                f"{index}번째 추천의 events 각 항목은 "
                "비어 있지 않은 문자열이어야 합니다."
            )

        city_name = recommendation["city"].strip()

        if city_name in checked_city_names:
            raise ValueError(
                f"추천 지역이 중복되었습니다: {city_name}"
            )

        checked_city_names.add(city_name)

    return data


def request_travel_recommendation(
    travel_date,
    gemini_api_key,
    retry_count=0,
):
    """Gemini API에 여행 날짜를 전달하고 추천 JSON을 반환한다."""
    prompt = f"""
여행 날짜는 {travel_date}입니다.

해당 시기에 여행하기 좋은 서로 다른 국내 지역 2~3곳을 추천하세요.
각 지역마다 정확한 실시간 예보가 아니라 일반적인 계절 날씨를 요약하세요.
각 지역마다 행사와 축제 후보를 1~3개 제시하세요.
각 지역의 추천 이유는 2~4문장으로 작성하세요.
지역 이름이 중복되지 않도록 하세요.
"""

    if retry_count == 1:
        prompt += """
이전 응답은 JSON 파싱 또는 구조 검증에 실패했습니다.
설명, 인사말, Markdown 코드 블록은 제외하세요.
다음 필수 키만 포함한 JSON 객체로 다시 출력하세요.

recommended_cities: array of 2~3 objects

각 객체의 필수 키:
city: string
weather: string
events: array of 1~3 strings
reason: string
"""

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gemini_api_key,
    }

    response_schema = {
        "type": "object",
        "properties": {
            "recommended_cities": {
                "type": "array",
                "description": "여행하기 좋은 서로 다른 국내 지역 2~3곳",
                "minItems": 2,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "추천하는 대한민국 도시 또는 지역",
                        },
                        "weather": {
                            "type": "string",
                            "description": "해당 시기의 일반적인 날씨 요약",
                        },
                        "events": {
                            "type": "array",
                            "description": "행사 또는 축제 후보 1~3개",
                            "items": {
                                "type": "string",
                            },
                            "minItems": 1,
                            "maxItems": 3,
                        },
                        "reason": {
                            "type": "string",
                            "description": "해당 지역을 추천한 이유 2~4문장",
                        },
                    },
                    "required": [
                        "city",
                        "weather",
                        "events",
                        "reason",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "recommended_cities",
        ],
        "additionalProperties": False,
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
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": response_schema,
        },
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

            print(f"Gemini API 요청 오류: HTTP {response.status_code}")
            print(f"- 상세: {error_message}")
            raise SystemExit(1)

        response_text = extract_gemini_text(response.json())

        recommendation = json.loads(response_text)
        return validate_recommendation_data(recommendation)

    except requests.RequestException as error:
        print(f"Gemini API 네트워크 오류: {error}")
        raise SystemExit(1) from error
    except (KeyError, IndexError, TypeError) as error:
        print("Gemini 응답에서 생성 결과를 찾지 못했습니다.")
        raise SystemExit(1) from error

    except ValueError as error:
        if retry_count == 0:
            print(
                "- JSON 파싱 또는 구조 검증 실패로 "
                "Gemini에 1회 재요청합니다."
            )

            return request_travel_recommendation(
                travel_date,
                gemini_api_key,
                retry_count=1,
            )

        print(
            "Gemini 응답을 재요청했지만 "
            "올바른 추천 JSON을 받지 못했습니다."
        )
        raise SystemExit(1) from error

"""Gemini API와 Kakao Local API를 활용한 국내 여행 추천 프로그램."""

import json
import os
from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)

KAKAO_LOCAL_API_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)


def validate_date(date_text):
    """입력값이 YYYY-MM-DD 형식의 실제 날짜인지 검증한다."""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError as error:
        raise ArgumentTypeError(
            "날짜는 YYYY-MM-DD 형식의 실제 날짜여야 합니다."
        ) from error

    return date_text


def parse_arguments():
    """터미널에서 여행 날짜 옵션을 입력받는다."""
    parser = ArgumentParser(
        description="여행 날짜를 기준으로 국내 여행지를 추천합니다."
    )

    parser.add_argument(
        "-date",
        "--date",
        required=True,
        type=validate_date,
        help='여행 날짜를 YYYY-MM-DD 형식으로 입력하세요. 예: "2026-08-15"',
    )

    return parser.parse_args()


def load_api_keys():
    """환경변수에서 Gemini와 Kakao API 키를 불러오고 검증한다."""
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    kakao_api_key = os.getenv("KAKAO_REST_API_KEY")

    missing_keys = []

    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY":
        missing_keys.append("GEMINI_API_KEY")

    if not kakao_api_key or kakao_api_key == "YOUR_KAKAO_REST_API_KEY":
        missing_keys.append("KAKAO_REST_API_KEY")

    if missing_keys:
        print("오류: 필요한 API 키가 설정되지 않았습니다.")
        print(f"미설정 항목: {', '.join(missing_keys)}")
        print(".env 파일에 실제 API 키를 입력한 뒤 다시 실행하세요.")
        raise SystemExit(1)

    return gemini_api_key, kakao_api_key


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
            try:
                error_message = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                error_message = response.text or "상세 메시지 없음"

            print(f"Gemini API 요청 오류: HTTP {response.status_code}")
            print(f"- 상세: {error_message}")
            raise SystemExit(1)

        response_data = response.json()
        response_text = (
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )

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
            errors.append(
                {
                    "step": "place_search",
                    "type": "AUTH_ERROR",
                    "message": f"HTTP {response.status_code}",
                }
            )
            print(
                f"- 오류: 인증 실패({response.status_code}). "
                "Kakao REST API 키와 사용 설정을 확인하세요."
            )
            return []

        if response.status_code == 429:
            errors.append(
                {
                    "step": "place_search",
                    "type": "QUOTA_ERROR",
                    "message": "HTTP 429",
                }
            )
            print("- 오류: Kakao API 요청 한도를 초과했습니다.")
            return []

        if not response.ok:
            errors.append(
                {
                    "step": "place_search",
                    "type": "HTTP_ERROR",
                    "message": f"HTTP {response.status_code}",
                }
            )
            print(
                f"- 오류: Kakao API 요청 실패 "
                f"(HTTP {response.status_code})"
            )
            return []

        response_data = response.json()

    except requests.RequestException as error:
        errors.append(
            {
                "step": "place_search",
                "type": "NETWORK_ERROR",
                "message": str(error),
            }
        )
        print(f"- 오류: Kakao API 네트워크 오류: {error}")
        return []

    except ValueError as error:
        errors.append(
            {
                "step": "place_search",
                "type": "PARSE_ERROR",
                "message": str(error),
            }
        )
        print("- 오류: Kakao API 응답을 JSON으로 읽지 못했습니다.")
        return []

    documents = response_data.get("documents", [])

    if not documents:
        errors.append(
            {
                "step": "place_search",
                "type": "EMPTY_RESULT",
                "message": f"0 results for query={query}",
            }
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
            try:
                error_message = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                error_message = (
                    response.text or "상세 메시지 없음"
                )

            if response.status_code in (401, 403):
                error_type = "AUTH_ERROR"
            elif response.status_code == 429:
                error_type = "QUOTA_ERROR"
            else:
                error_type = "HTTP_ERROR"

            errors.append(
                {
                    "step": "final_report",
                    "type": error_type,
                    "message": (
                        f"HTTP {response.status_code}: "
                        f"{error_message}"
                    ),
                }
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

        response_data = response.json()
        report_text = (
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )

        if (
            not isinstance(report_text, str)
            or not report_text.strip()
        ):
            raise ValueError(
                "최종 리포트 내용이 비어 있습니다."
            )

        return report_text.strip()

    except (ValueError, KeyError, IndexError, TypeError) as error:
        errors.append(
            {
                "step": "final_report",
                "type": "RESPONSE_ERROR",
                "message": str(error),
            }
        )

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
        errors.append(
            {
                "step": "final_report",
                "type": "NETWORK_ERROR",
                "message": str(error),
            }
        )

        print(f"최종 리포트 생성 네트워크 오류: {error}")
        print("- 로컬 대체 리포트를 생성합니다.")

        return build_fallback_report(
            travel_date,
            recommendation_data,
            restaurants_by_city,
            errors,
        )

def load_cached_results(travel_date):
    """같은 날짜의 기존 JSON과 Markdown 결과를 불러온다."""
    results_directory = Path("results")

    raw_data_path = (
        results_directory / f"{travel_date}_raw_data.json"
    )
    report_path = (
        results_directory / f"{travel_date}_travel_plan.md"
    )

    if not raw_data_path.exists():
        return None

    try:
        with raw_data_path.open(
            "r",
            encoding="utf-8",
        ) as json_file:
            raw_data = json.load(json_file)

    except (OSError, ValueError) as error:
        print(f"- 캐시 원본 JSON을 읽지 못했습니다: {error}")
        print("- 기존 캐시를 사용하지 않고 API를 다시 호출합니다.")
        return None

    if not isinstance(raw_data, dict):
        print("- 캐시 원본 JSON의 최상위 구조가 올바르지 않습니다.")
        print("- 기존 캐시를 사용하지 않고 API를 다시 호출합니다.")
        return None

    recommendation_data = raw_data.get("recommendation")
    restaurants_by_city = raw_data.get("restaurants")
    errors = raw_data.get("errors")

    if (
        not isinstance(recommendation_data, dict)
        or not isinstance(restaurants_by_city, list)
        or not isinstance(errors, list)
    ):
        print("- 캐시 원본 JSON의 필수 데이터 구조가 올바르지 않습니다.")
        print("- 기존 캐시를 사용하지 않고 API를 다시 호출합니다.")
        return None

    report_text = ""

    if report_path.exists():
        try:
            report_text = report_path.read_text(
                encoding="utf-8",
            ).strip()

        except OSError as error:
            print(f"- 기존 Markdown을 읽지 못했습니다: {error}")

    if not report_text:
        print("- 기존 Markdown이 없어 로컬 리포트를 재생성합니다.")

        report_text = build_fallback_report(
            travel_date,
            recommendation_data,
            restaurants_by_city,
            errors,
        )

        try:
            report_path.write_text(
                report_text + "\n",
                encoding="utf-8",
            )

        except OSError as error:
            print(f"- 재생성한 Markdown 저장 실패: {error}")
            return None

    return {
        "recommendation_data": recommendation_data,
        "restaurants_by_city": restaurants_by_city,
        "errors": errors,
        "report_text": report_text,
        "raw_data_path": raw_data_path,
        "report_path": report_path,
    }

def save_results(
    travel_date,
    recommendation,
    restaurants,
    errors,
    report_text,
):
    """원본 JSON과 최종 Markdown 리포트를 results 폴더에 저장한다."""
    results_directory = Path("results")
    results_directory.mkdir(exist_ok=True)

    raw_data_path = (
        results_directory / f"{travel_date}_raw_data.json"
    )
    report_path = (
        results_directory / f"{travel_date}_travel_plan.md"
    )

    raw_data = {
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }

    with raw_data_path.open(
        "w",
        encoding="utf-8",
    ) as json_file:
        json.dump(
            raw_data,
            json_file,
            ensure_ascii=False,
            indent=2,
        )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as markdown_file:
        markdown_file.write(report_text)
        markdown_file.write("\n")

    return raw_data_path, report_path


def main():
    """프로그램의 시작점."""
    args = parse_arguments()

    print(f"입력한 여행 날짜: {args.date}")

    cached_results = load_cached_results(args.date)

    if cached_results is not None:
        print("- 같은 날짜의 기존 결과를 발견했습니다.")
        print("- Gemini와 Kakao API 호출을 건너뜁니다.")

        print()
        print("완료! (캐시 사용)")
        print(
            f"- 원본 데이터: "
            f"{cached_results['raw_data_path']}"
        )
        print(
            f"- 여행 리포트: "
            f"{cached_results['report_path']}"
        )
        print(
            f"- 오류 기록: "
            f"{len(cached_results['errors'])}건"
        )
        return

    gemini_api_key, kakao_api_key = load_api_keys()
    errors = []

    print("[1/3] 복수 지역 추천 생성 중(Gemini)...")

    recommendation_data = request_travel_recommendation(
        args.date,
        gemini_api_key,
    )

    recommendations = recommendation_data["recommended_cities"]

    print(
        f"1차 추천 생성 완료 "
        f"- 총 {len(recommendations)}개 지역"
    )

    for index, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        print()
        print(f"[추천 지역 {index}]")
        print(f"- 지역: {recommendation['city']}")
        print(f"- 날씨: {recommendation['weather']}")
        print(
            f"- 행사·축제: "
            f"{', '.join(recommendation['events'])}"
        )
        print(f"- 추천 이유: {recommendation['reason']}")

    print()
    print("[2/3] 지역별 맛집 검색 중(Kakao Local)...")

    restaurants_by_city = []

    for recommendation in recommendations:
        city = recommendation["city"]

        print()
        print(f"- {city} 맛집 검색 중...")

        city_restaurants = search_restaurants(
            city,
            kakao_api_key,
            errors,
        )

        restaurants_by_city.append(
            {
                "city": city,
                "restaurants": city_restaurants,
            }
        )

        if city_restaurants:
            print(
                f"- {city} 맛집 "
                f"{len(city_restaurants)}곳 검색 완료"
            )

            for index, restaurant in enumerate(
                city_restaurants,
                start=1,
            ):
                print(
                    f"  {index}. {restaurant['name']} "
                    f"| {restaurant['address']}"
                )
        else:
            print(f"- {city} 맛집 데이터 없음")

    print()
    print("[3/3] 최종 리포트 생성 중(Gemini)...")

    report_text = generate_final_report(
        args.date,
        recommendation_data,
        restaurants_by_city,
        errors,
        gemini_api_key,
    )

    print("- 최종 리포트 생성 완료")

    raw_data_path, report_path = save_results(
        args.date,
        recommendation_data,
        restaurants_by_city,
        errors,
        report_text,
    )

    print()
    print("완료!")
    print(f"- 원본 데이터: {raw_data_path}")
    print(f"- 여행 리포트: {report_path}")
    print(f"- 오류 기록: {len(errors)}건")

if __name__ == "__main__":
    main()
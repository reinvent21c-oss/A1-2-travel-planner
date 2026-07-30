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


def request_travel_recommendation(
    travel_date,
    gemini_api_key,
    retry_count=0,
):
    """Gemini API에 여행 날짜를 전달하고 추천 JSON을 반환한다."""
    prompt = f"""
여행 날짜는 {travel_date}입니다.

해당 시기에 여행하기 좋은 국내 지역 한 곳을 추천하세요.
정확한 실시간 예보가 아니라 일반적인 계절 날씨를 요약하세요.
행사와 축제는 일정이 변경될 수 있는 후보 1~3개를 제시하세요.
추천 이유는 2~4문장으로 작성하세요.
"""

    if retry_count == 1:
        prompt += """
이전 응답은 JSON 파싱에 실패했습니다.
설명, 인사말, Markdown 코드 블록은 제외하세요.
다음 필수 키만 포함한 JSON 객체로 다시 출력하세요.

recommended_city: string
weather: string
events: array of string
reason: string
"""

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gemini_api_key,
    }

    response_schema = {
        "type": "object",
        "properties": {
            "recommended_city": {
                "type": "string",
                "description": "추천하는 대한민국 도시 또는 지역 한 곳",
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
                "description": "여행지를 추천한 이유 2~4문장",
            },
        },
        "required": [
            "recommended_city",
            "weather",
            "events",
            "reason",
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

        return json.loads(response_text)

    except requests.RequestException as error:
        print(f"Gemini API 네트워크 오류: {error}")
        raise SystemExit(1) from error

    except (KeyError, IndexError, TypeError) as error:
        print("Gemini 응답에서 생성 결과를 찾지 못했습니다.")
        raise SystemExit(1) from error

    except json.JSONDecodeError as error:
        if retry_count == 0:
            print("- JSON 파싱 실패로 Gemini에 1회 재요청합니다.")

            return request_travel_recommendation(
                travel_date,
                gemini_api_key,
                retry_count=1,
            )

        print(
            "Gemini 응답을 재요청했지만 "
            "JSON으로 변환하지 못했습니다."
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


def generate_final_report(
    travel_date,
    recommendation,
    restaurants,
    errors,
    gemini_api_key,
):
    """추천 정보와 맛집 목록을 바탕으로 Markdown 리포트를 생성한다."""
    report_data = {
        "travel_date": travel_date,
        "recommendation": recommendation,
        "restaurants": restaurants,
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
4. 다음 항목을 반드시 순서대로 포함하세요.
   ## 추천 지역
   ## 추천 이유
   ## 날씨 요약
   ## 행사/축제
   ## 맛집 추천
   ## 1일 일정 제안
   ## 오류 요약(errors)
5. 1일 일정은 오전, 오후, 저녁으로 나누어 작성하세요.
6. 맛집 목록이 비어 있으면 '데이터 없음'이라고 작성하세요.
7. 오류 목록이 비어 있으면 '오류 없음'이라고 작성하세요.
8. 행사와 축제는 실제 일정이 변경될 수 있음을 안내하세요.
9. 제공된 JSON에 없는 맛집 이름이나 주소는 새로 만들지 마세요.
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
                error_message = response.text or "상세 메시지 없음"

            print(f"최종 리포트 생성 오류: HTTP {response.status_code}")
            print(f"- 상세: {error_message}")
            raise SystemExit(1)

        response_data = response.json()
        report_text = (
            response_data["candidates"][0]["content"]["parts"][0]["text"]
        )

        return report_text.strip()

    except requests.RequestException as error:
        print(f"최종 리포트 생성 네트워크 오류: {error}")
        raise SystemExit(1) from error

    except (KeyError, IndexError, TypeError) as error:
        print("Gemini 응답에서 최종 리포트를 찾지 못했습니다.")
        raise SystemExit(1) from error


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
    gemini_api_key, kakao_api_key = load_api_keys()
    errors = []

    print(f"입력한 여행 날짜: {args.date}")
    print("[1/3] 1차 추천 생성 중(Gemini)...")

    recommendation = request_travel_recommendation(
        args.date,
        gemini_api_key,
    )

    print("1차 추천 생성 완료")
    print(f"- 추천 지역: {recommendation['recommended_city']}")
    print(f"- 날씨: {recommendation['weather']}")
    print(f"- 행사·축제: {', '.join(recommendation['events'])}")
    print(f"- 추천 이유: {recommendation['reason']}")

    print("[2/3] 맛집 검색 중(Kakao Local)...")

    restaurants = search_restaurants(
        recommendation["recommended_city"],
        kakao_api_key,
        errors,
    )

    if restaurants:
        print(f"- 맛집 {len(restaurants)}곳 검색 완료")

        for index, restaurant in enumerate(restaurants, start=1):
            print(
                f"  {index}. {restaurant['name']} "
                f"| {restaurant['address']}"
            )
    else:
        print("- 맛집 데이터 없음")

    print("[3/3] 최종 리포트 생성 중(Gemini)...")

    report_text = generate_final_report(
        args.date,
        recommendation,
        restaurants,
        errors,
        gemini_api_key,
    )

    print("- 최종 리포트 생성 완료")

    raw_data_path, report_path = save_results(
        args.date,
        recommendation,
        restaurants,
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
"""Gemini API와 Kakao Local API를 활용한 국내 여행 추천 프로그램."""

import json
import os
from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime

import requests
from dotenv import load_dotenv


GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
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


def request_travel_recommendation(travel_date, gemini_api_key):
    """Gemini API에 여행 날짜를 전달하고 추천 JSON을 반환한다."""
    prompt = f"""
여행 날짜는 {travel_date}입니다.

해당 시기에 여행하기 좋은 국내 지역 한 곳을 추천하세요.
정확한 실시간 예보가 아니라 일반적인 계절 날씨를 요약하세요.
행사와 축제는 일정이 변경될 수 있는 후보 1~3개를 제시하세요.
추천 이유는 2~4문장으로 작성하세요.
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
        print("Gemini 응답을 JSON으로 변환하지 못했습니다.")
        raise SystemExit(1) from error


def main():
    """프로그램의 시작점."""
    args = parse_arguments()
    gemini_api_key, _ = load_api_keys()

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


if __name__ == "__main__":
    main()
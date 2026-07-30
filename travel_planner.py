"""Gemini API와 Kakao Local API를 활용한 국내 여행 추천 프로그램."""

import os
from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime

from dotenv import load_dotenv


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


def main():
    """프로그램의 시작점."""
    args = parse_arguments()
    load_api_keys()

    print(f"입력한 여행 날짜: {args.date}")
    print("API 키 설정 확인 완료")


if __name__ == "__main__":
    main()
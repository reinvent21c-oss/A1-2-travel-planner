"""Gemini API와 Kakao Local API를 활용한 국내 여행 추천 프로그램."""

from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime


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


def main():
    """프로그램의 시작점."""
    args = parse_arguments()
    print(f"입력한 여행 날짜: {args.date}")


if __name__ == "__main__":
    main()
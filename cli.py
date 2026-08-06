"""명령행 인자 정의와 검증."""

from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime


def validate_date(date_text):
    """입력값이 실제 날짜이며 오늘보다 과거가 아닌지 검증한다."""
    try:
        parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ArgumentTypeError(
            "날짜는 YYYY-MM-DD 형식의 실제 날짜여야 합니다."
        ) from error

    if parsed_date < datetime.today().date():
        raise ArgumentTypeError("오늘보다 이전 날짜는 입력할 수 없습니다.")

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

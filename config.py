"""API와 결과 파일 관련 설정."""

import os
from pathlib import Path

from dotenv import load_dotenv


GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{GEMINI_MODEL}:generateContent"
)
KAKAO_LOCAL_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

RESULTS_DIRECTORY = Path("results")
RAW_DATA_FILENAME = "{travel_date}_raw_data.json"
REPORT_FILENAME = "{travel_date}_travel_plan.md"


def get_result_paths(travel_date):
    """여행 날짜에 대응하는 원본 데이터와 리포트 경로를 반환한다."""
    return (
        RESULTS_DIRECTORY / RAW_DATA_FILENAME.format(travel_date=travel_date),
        RESULTS_DIRECTORY / REPORT_FILENAME.format(travel_date=travel_date),
    )


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

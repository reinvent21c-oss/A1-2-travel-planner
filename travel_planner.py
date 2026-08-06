"""Gemini API와 Kakao Local API를 활용한 국내 여행 추천 프로그램."""

from api_helpers import (
    append_error,
    extract_api_error_message,
    extract_gemini_text,
)
from cli import parse_arguments, validate_date
from config import get_result_paths, load_api_keys
from planner import (
    create_travel_plan,
    print_recommendations,
    print_result_summary,
    search_restaurants_for_cities,
)
from recommendations import (
    request_travel_recommendation,
    validate_recommendation_data,
)
from reports import build_fallback_report, generate_final_report
from restaurants import search_restaurants
from storage import load_cached_results, save_results


def main():
    """캐시를 확인하고 여행 계획 생성 과정을 실행한다."""
    args = parse_arguments()
    print(f"입력한 여행 날짜: {args.date}")

    cached_results = load_cached_results(args.date)
    if cached_results is not None:
        print("- 같은 날짜의 기존 결과를 발견했습니다.")
        print("- Gemini와 Kakao API 호출을 건너뜁니다.")
        print_result_summary(
            cached_results["raw_data_path"],
            cached_results["report_path"],
            len(cached_results["errors"]),
            cached=True,
        )
        return

    gemini_api_key, kakao_api_key = load_api_keys()
    (
        recommendation_data,
        restaurants_by_city,
        errors,
        report_text,
    ) = create_travel_plan(args.date, gemini_api_key, kakao_api_key)

    raw_data_path, report_path = save_results(
        args.date,
        recommendation_data,
        restaurants_by_city,
        errors,
        report_text,
    )
    print_result_summary(raw_data_path, report_path, len(errors))


if __name__ == "__main__":
    main()

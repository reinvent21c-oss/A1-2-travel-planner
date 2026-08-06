"""여행 결과 캐시와 파일 저장 기능."""

import json

from config import RESULTS_DIRECTORY, get_result_paths
from reports import build_fallback_report

def load_cached_results(travel_date):
    """같은 날짜의 기존 JSON과 Markdown 결과를 불러온다."""
    raw_data_path, report_path = get_result_paths(travel_date)

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
    RESULTS_DIRECTORY.mkdir(exist_ok=True)
    raw_data_path, report_path = get_result_paths(travel_date)

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

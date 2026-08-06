"""여행 계획 생성 과정과 터미널 출력 기능."""

from recommendations import request_travel_recommendation
from reports import generate_final_report
from restaurants import search_restaurants

def print_recommendations(recommendations):
    """추천 지역의 핵심 정보를 터미널에 출력한다."""
    for index, recommendation in enumerate(recommendations, start=1):
        print()
        print(f"[추천 지역 {index}]")
        print(f"- 지역: {recommendation['city']}")
        print(f"- 날씨: {recommendation['weather']}")
        print(f"- 행사·축제: {', '.join(recommendation['events'])}")
        print(f"- 추천 이유: {recommendation['reason']}")


def search_restaurants_for_cities(
    recommendations,
    kakao_api_key,
    errors,
):
    """각 추천 지역의 맛집을 검색하고 지역별 결과로 묶는다."""
    restaurants_by_city = []

    for recommendation in recommendations:
        city = recommendation["city"]

        print()
        print(f"- {city} 맛집 검색 중...")

        restaurants = search_restaurants(city, kakao_api_key, errors)
        restaurants_by_city.append(
            {
                "city": city,
                "restaurants": restaurants,
            }
        )

        if not restaurants:
            print(f"- {city} 맛집 데이터 없음")
            continue

        print(f"- {city} 맛집 {len(restaurants)}곳 검색 완료")
        for index, restaurant in enumerate(restaurants, start=1):
            print(
                f"  {index}. {restaurant['name']} "
                f"| {restaurant['address']}"
            )

    return restaurants_by_city


def print_result_summary(raw_data_path, report_path, error_count, cached=False):
    """저장된 결과 파일과 오류 건수를 터미널에 출력한다."""
    print()
    print("완료! (캐시 사용)" if cached else "완료!")
    print(f"- 원본 데이터: {raw_data_path}")
    print(f"- 여행 리포트: {report_path}")
    print(f"- 오류 기록: {error_count}건")


def create_travel_plan(travel_date, gemini_api_key, kakao_api_key):
    """API를 이용해 추천, 맛집 검색, 리포트 생성을 순서대로 수행한다."""
    errors = []

    print("[1/3] 복수 지역 추천 생성 중(Gemini)...")
    recommendation_data = request_travel_recommendation(
        travel_date,
        gemini_api_key,
    )
    recommendations = recommendation_data["recommended_cities"]

    print(f"1차 추천 생성 완료 - 총 {len(recommendations)}개 지역")
    print_recommendations(recommendations)

    print()
    print("[2/3] 지역별 맛집 검색 중(Kakao Local)...")
    restaurants_by_city = search_restaurants_for_cities(
        recommendations,
        kakao_api_key,
        errors,
    )

    print()
    print("[3/3] 최종 리포트 생성 중(Gemini)...")
    report_text = generate_final_report(
        travel_date,
        recommendation_data,
        restaurants_by_city,
        errors,
        gemini_api_key,
    )
    print("- 최종 리포트 생성 완료")

    return recommendation_data, restaurants_by_city, errors, report_text

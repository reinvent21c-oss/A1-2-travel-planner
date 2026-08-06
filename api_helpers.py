"""외부 API 응답과 오류 처리에 사용하는 공통 함수."""


def extract_gemini_text(response_data):
    """Gemini 응답 객체에서 첫 번째 생성 텍스트를 추출한다."""
    response_text = response_data["candidates"][0]["content"]["parts"][0][
        "text"
    ]

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Gemini 생성 결과가 비어 있습니다.")

    return response_text.strip()


def extract_api_error_message(response):
    """HTTP 오류 응답에서 사용자에게 보여줄 상세 메시지를 추출한다."""
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return response.text or "상세 메시지 없음"


def append_error(errors, step, error_type, message):
    """실행 중 발생한 오류를 일관된 구조로 기록한다."""
    errors.append({"step": step, "type": error_type, "message": message})

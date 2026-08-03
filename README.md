# A1-2 국내 여행지 추천 프로그램

Google Gemini API와 Kakao Local API를 연동한 CLI 기반 국내 여행 추천 프로그램입니다.

사용자가 여행 날짜를 입력하면 Gemini가 해당 시기에 여행하기 좋은 국내 지역을 추천합니다. 이후 추천 지역을 Kakao Local API에 전달해 맛집을 검색하고, 추천 정보와 맛집 데이터를 바탕으로 최종 Markdown 여행 리포트를 생성합니다.

## 주요 기능

1. `argparse`를 이용한 여행 날짜 입력
2. `YYYY-MM-DD` 날짜 형식 검증
3. Gemini API를 이용한 여행지 추천 JSON 생성
4. 추천 지역을 활용한 Kakao Local 맛집 검색
5. Gemini API를 이용한 최종 Markdown 리포트 생성
6. 원본 JSON과 Markdown 결과 파일 저장
7. API 키 누락, 네트워크, 인증, 파싱 오류 처리
8. Gemini JSON 파싱 실패 시 최대 1회 재요청

## 프로그램 실행 흐름

```text
여행 날짜 입력
→ Gemini 여행지 추천
→ 추천 결과를 JSON으로 파싱
→ recommended_city를 Kakao Local API에 전달
→ 맛집 최대 5곳 검색
→ Gemini 최종 Markdown 리포트 생성
→ results/ 폴더에 JSON과 Markdown 저장
```

## API 요청 방식과 구조화된 데이터

### GET과 POST를 구분한 이유

이 프로그램은 각 API의 역할과 공식 요청 방식에 맞춰 HTTP 메서드를 구분해 사용합니다.

- **Gemini API는 POST 방식**으로 호출합니다. 여행 날짜, 프롬프트, 응답 스키마, 생성 설정처럼 여러 요청 데이터를 JSON 본문에 담아 새로운 추천 결과와 리포트를 생성하기 때문입니다.
- **Kakao Local API는 GET 방식**으로 호출합니다. 이미 존재하는 장소 데이터에서 검색어와 결과 개수 조건에 맞는 정보를 조회하며, 검색 조건을 쿼리 파라미터로 전달하기 때문입니다.
- Kakao REST API 키는 URL에 포함하지 않고 `Authorization` 요청 헤더에 전달합니다.

따라서 단순히 GET과 POST 중 하나를 임의로 선택한 것이 아니라, 각 API의 명세와 요청 목적에 맞는 방식을 사용했습니다.

### Gemini 응답을 JSON으로 받는 이유

Gemini의 추천 결과를 자유로운 문장으로 받으면 추천 지역, 날씨, 행사, 추천 이유를 코드에서 안정적으로 구분하기 어렵습니다.

그래서 다음과 같은 구조화된 JSON 형식으로 응답하도록 요청합니다.

```json
{
  "recommended_city": "강릉시",
  "weather": "일반적인 계절 날씨 요약",
  "events": [
    "행사 또는 축제 후보"
  ],
  "reason": "추천 이유"
}
```

구조화된 JSON을 사용하면 다음과 같은 장점이 있습니다.

- `recommended_city`를 Kakao Local API의 검색 입력으로 바로 전달할 수 있습니다.
- 필수 키가 모두 있는지 검사할 수 있습니다.
- 문자열과 배열 등 각 값의 자료형을 검증할 수 있습니다.
- 잘못된 응답 형식을 발견하면 Gemini에 한 번 다시 요청할 수 있습니다.
- 추천 결과를 원본 JSON 파일에 일관된 형식으로 저장할 수 있습니다.

즉, JSON은 두 API 사이에서 데이터를 안정적으로 전달하고, 응답 오류를 코드로 검증하기 위한 중간 데이터 형식입니다.


## 개발 환경

- Python 3.10 이상
- 테스트 환경: Python 3.12.13
- Google Gemini API
- 사용 모델: `gemini-3.5-flash-lite`
- Kakao Local API
- `requests`
- `python-dotenv`

## 프로젝트 구조

```text
A1-2-travel-planner/
├── results/
│   ├── .gitkeep
│   ├── 2026-08-15_raw_data.json
│   └── 2026-08-15_travel_plan.md
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── travel_planner.py
```

`.venv`와 실제 API 키가 들어 있는 `.env` 파일은 GitHub에 포함하지 않습니다.

## 설치 방법

저장소를 내려받습니다.

```bash
git clone https://github.com/reinvent21c-oss/A1-2-travel-planner.git
cd A1-2-travel-planner
```

가상환경을 생성하고 활성화합니다.

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

필요한 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt
```

## API 키 설정

`.env.example`을 복사하여 `.env` 파일을 만듭니다.

### macOS / Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

생성된 `.env` 파일에 발급받은 API 키를 입력합니다.

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
KAKAO_REST_API_KEY=YOUR_KAKAO_REST_API_KEY
```

`YOUR_...` 부분을 실제 API 키로 교체해야 합니다.

## 실행 방법

긴 옵션 `--date`로 실행할 수 있습니다.

```bash
python travel_planner.py --date "2026-08-15"
```

미션 안내문의 짧은 옵션 `-date`도 사용할 수 있습니다.

```bash
python travel_planner.py -date "2026-08-15"
```

날짜는 실제로 존재하는 `YYYY-MM-DD` 형식이어야 합니다.

## 실행 결과

정상 실행되면 터미널에 진행 상태가 출력됩니다.

```text
[1/3] 1차 추천 생성 중(Gemini)...
[2/3] 맛집 검색 중(Kakao Local)...
[3/3] 최종 리포트 생성 중(Gemini)...

완료!
```

`results/` 폴더에 다음 파일이 생성됩니다.

```text
results/2026-08-15_raw_data.json
results/2026-08-15_travel_plan.md
```

원본 JSON에는 다음 데이터가 포함됩니다.

```json
{
  "recommendation": {},
  "restaurants": [],
  "errors": []
}
```

## 오류 처리 원칙

- API 키가 없으면 설정 방법을 안내하고 즉시 종료합니다.
- Gemini JSON 파싱 실패 시 최대 1회만 다시 요청합니다.
- Kakao Local API가 실패하거나 검색 결과가 0건이면 맛집 데이터를 빈 목록으로 처리합니다.
- 맛집 검색에 실패해도 최종 여행 리포트 생성은 계속 진행합니다.
- 발생한 오류는 내부 `errors` 목록과 원본 JSON에 기록합니다.

## API 키 보안 주의사항

API 키는 코드에 직접 작성하지 않고 `.env` 파일에 저장합니다.

`.env`는 `.gitignore`에 등록되어 있으므로 GitHub에 업로드되지 않아야 합니다.

API 키를 코드나 GitHub에 직접 올리면 다음 문제가 발생할 수 있습니다.

- 다른 사람이 키를 무단으로 사용할 수 있음
- API 사용량이나 과금 피해가 발생할 수 있음
- 키가 유출되면 폐기하고 다시 발급해야 함

또한 README, 실행 로그, JSON, Markdown 결과물에도 실제 API 키가 포함되지 않도록 주의해야 합니다.

## 사용 API

- Google Gemini API: 여행지 추천 및 최종 리포트 생성
- Kakao Local API: 추천 지역의 맛집 검색

## 참고사항

Gemini가 생성하는 날씨와 행사 정보는 실시간 공식 데이터가 아니라 일반적인 계절 정보와 행사 후보입니다. 실제 여행 전에는 날씨, 행사 일정, 영업시간 등을 공식 정보로 다시 확인해야 합니다.
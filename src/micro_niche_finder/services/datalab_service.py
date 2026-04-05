from __future__ import annotations

from datetime import date, datetime, timedelta
from math import sin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import DataLabRequest, DataLabResponse


class NaverDataLabService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_request(
        self,
        group_name: str,
        queries: list[str],
        weeks: int = 12,
        *,
        time_unit: str = "week",
        device: str | None = None,
        ages: list[str] | None = None,
        gender: str | None = None,
    ) -> DataLabRequest:
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)
        cleaned_queries = list(dict.fromkeys(" ".join(query.strip().split()) for query in queries if query.strip()))
        limited_queries = cleaned_queries[:20]
        if not limited_queries:
            limited_queries = [group_name[:50]]
        return DataLabRequest(
            startDate=start_date,
            endDate=end_date,
            timeUnit=time_unit,
            keywordGroups=[{"groupName": group_name[:50], "keywords": limited_queries}],
            device=device,
            ages=ages,
            gender=gender,
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: DataLabRequest) -> DataLabResponse:
        if not self.settings.naver_datalab_client_id or not self.settings.naver_datalab_client_secret:
            return self._mock_response(request)

        headers = {
            "X-Naver-Client-Id": self.settings.naver_datalab_client_id,
            "X-Naver-Client-Secret": self.settings.naver_datalab_client_secret,
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                self.settings.naver_datalab_base_url,
                headers=headers,
                json=request.model_dump(mode="json", exclude_none=True),
            )
            response.raise_for_status()
        return DataLabResponse.model_validate(response.json())

    def _mock_response(self, request: DataLabRequest) -> DataLabResponse:
        points = []
        current = datetime.combine(request.startDate, datetime.min.time()).date()
        index = 0
        while current <= request.endDate:
            baseline = 40 + (index * 1.8)
            seasonal = 8 * sin(index / 2.5)
            points.append({"period": current, "ratio": round(max(5.0, baseline + seasonal), 2)})
            current += timedelta(days=7)
            index += 1

        return DataLabResponse.model_validate(
            {
                "startDate": request.startDate,
                "endDate": request.endDate,
                "timeUnit": request.timeUnit,
                "results": [
                    {
                        "title": request.keywordGroups[0].groupName,
                        "keywords": request.keywordGroups[0].keywords,
                        "data": points,
                    }
                ],
            }
        )

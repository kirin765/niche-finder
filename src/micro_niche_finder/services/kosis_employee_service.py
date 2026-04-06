from __future__ import annotations

import json
from datetime import date
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    KosisEmployeeRequest,
    KosisEmployeeResponse,
    KosisIndustryOption,
    KosisIndustrySelection,
    MarketSizeContext,
)


class KosisEmployeeService:
    SOURCE = "kosis_employee_count"
    SOURCE_LABEL = "KOSIS nationwide business census employee count"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        return bool(
            self.settings.kosis_api_key
            and self.settings.kosis_tbl_id
            and self.settings.kosis_employee_itm_id
        )

    def industry_options(self) -> list[KosisIndustryOption]:
        if not self.settings.kosis_industry_options_json:
            return []
        payload = json.loads(self.settings.kosis_industry_options_json)
        return [KosisIndustryOption.model_validate(item) for item in payload]

    def build_request(
        self,
        selection: KosisIndustrySelection,
        *,
        reference_year: int | None = None,
    ) -> KosisEmployeeRequest:
        year = reference_year or max(2000, date.today().year - self.settings.kosis_reference_year_offset)
        params = {
            "method": "getList",
            "apiKey": self.settings.kosis_api_key or "",
            "format": "json",
            "jsonVD": "Y",
            "orgId": self.settings.kosis_org_id,
            "tblId": self.settings.kosis_tbl_id or "",
            "itmId": self.settings.kosis_employee_itm_id or "",
            "prdSe": self.settings.kosis_prd_se,
            "startPrdDe": str(year),
            "endPrdDe": str(year),
            self.settings.kosis_industry_dimension_key: selection.code,
        }
        if self.settings.kosis_static_params_json:
            params.update({key: str(value) for key, value in json.loads(self.settings.kosis_static_params_json).items()})
        return KosisEmployeeRequest(
            industry_code=selection.code,
            industry_label=selection.label,
            reference_year=year,
            params=params,
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch(self, request: KosisEmployeeRequest) -> KosisEmployeeResponse:
        if not self.is_configured():
            raise RuntimeError("KOSIS employee service is not configured")
        with httpx.Client(timeout=20.0) as client:
            response = client.get(self.settings.kosis_base_url, params=request.params)
            response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else [payload]
        employee_count = self._extract_employee_count(rows)
        return KosisEmployeeResponse(
            industry_code=request.industry_code,
            industry_label=request.industry_label,
            reference_year=request.reference_year,
            employee_count=employee_count,
            source_label=self.SOURCE_LABEL,
            source_table_id=self.settings.kosis_tbl_id or "",
            rows=rows,
        )

    def build_market_size_context(
        self,
        response: KosisEmployeeResponse,
        *,
        rationale: str,
    ) -> MarketSizeContext:
        if response.employee_count is None:
            summary = (
                f"{response.industry_label} 종사자 수를 KOSIS에서 조회했지만 유효한 수치를 추출하지 못했다. "
                f"기준연도는 {response.reference_year}년이다."
            )
        else:
            summary = (
                f"KOSIS 전국사업체조사 기준 {response.reference_year}년 {response.industry_label} 종사자 수는 "
                f"약 {response.employee_count:,}명이다."
            )
        return MarketSizeContext(
            source=self.SOURCE,
            source_label=response.source_label,
            industry_code=response.industry_code,
            industry_label=response.industry_label,
            reference_year=response.reference_year,
            employee_count=response.employee_count,
            summary=summary,
            rationale=rationale,
        )

    @staticmethod
    def response_to_context(payload: dict[str, Any], *, rationale: str) -> MarketSizeContext:
        response = KosisEmployeeResponse.model_validate(payload)
        if response.employee_count is None:
            summary = (
                f"{response.industry_label} 종사자 수를 KOSIS에서 조회했지만 유효한 수치를 추출하지 못했다. "
                f"기준연도는 {response.reference_year}년이다."
            )
        else:
            summary = (
                f"KOSIS 전국사업체조사 기준 {response.reference_year}년 {response.industry_label} 종사자 수는 "
                f"약 {response.employee_count:,}명이다."
            )
        return MarketSizeContext(
            source=KosisEmployeeService.SOURCE,
            source_label=response.source_label,
            industry_code=response.industry_code,
            industry_label=response.industry_label,
            reference_year=response.reference_year,
            employee_count=response.employee_count,
            summary=summary,
            rationale=rationale,
        )

    @staticmethod
    def _extract_employee_count(rows: list[dict[str, Any]]) -> int | None:
        if not rows:
            return None
        candidate_keys = ("DT", "dt", "DATA_VALUE", "data_value", "value")
        for row in rows:
            for key in candidate_keys:
                value = row.get(key)
                if value in (None, "", "-"):
                    continue
                digits = "".join(ch for ch in str(value) if ch.isdigit())
                if digits:
                    return int(digits)
        return None

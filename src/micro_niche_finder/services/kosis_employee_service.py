from __future__ import annotations

import json
from datetime import date
from math import pow
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain.schemas import (
    KosisEmployeeRequest,
    KosisEmployeeResponse,
    KosisIndustryOption,
    KosisIndustrySelection,
    KosisMetricPoint,
    KosisProfileOption,
    KosisProfileRequest,
    KosisProfileResponse,
    MarketSizeContext,
)


class KosisEmployeeService:
    SOURCE = "kosis_employee_count"
    SOURCE_LABEL = "KOSIS market context"

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        if not self.settings.kosis_enabled:
            return False
        return bool(self.settings.kosis_api_key and self.profile_options())

    def industry_options(self) -> list[KosisIndustryOption]:
        if not self.settings.kosis_industry_options_json:
            return []
        payload = json.loads(self.settings.kosis_industry_options_json)
        if isinstance(payload, list):
            return [KosisIndustryOption.model_validate(item) for item in payload]
        if isinstance(payload, dict):
            mapping = payload.get("mapping")
            if isinstance(mapping, dict):
                description_prefix = " ".join(
                    str(value)
                    for value in (payload.get("classification"), payload.get("level"))
                    if value
                ).strip()
                return [
                    KosisIndustryOption(
                        code=str(code),
                        label=str(label),
                        description=f"{description_prefix} 산업 매핑".strip(),
                    )
                    for label, code in mapping.items()
                ]
        return []

    def profile_options(self) -> list[KosisProfileOption]:
        if self.settings.kosis_profile_options_json:
            payload = json.loads(self.settings.kosis_profile_options_json)
            return [KosisProfileOption.model_validate(item) for item in payload]
        legacy_profile = self._legacy_profile_option()
        return [legacy_profile] if legacy_profile else []

    def build_requests(
        self,
        selection: KosisIndustrySelection,
        *,
        reference_year: int | None = None,
    ) -> list[KosisProfileRequest]:
        requests: list[KosisProfileRequest] = []
        for profile in self.profile_options():
            if not self._profile_applies(profile, selection.code):
                continue
            start_year, end_year = self._resolve_year_range(profile, reference_year)
            for metric_key, metric_item_id in profile.metrics.items():
                params = {
                    "method": "getList",
                    "apiKey": self.settings.kosis_api_key or "",
                    "format": "json",
                    "jsonVD": "Y",
                    "orgId": self.settings.kosis_org_id,
                    "tblId": profile.tbl_id,
                    "itmId": metric_item_id,
                    "startPrdDe": str(start_year),
                    "endPrdDe": str(end_year),
                }
                if not any(key.lower().replace("_", "") == "prdse" for key in profile.static_params):
                    params["prdSe"] = self.settings.kosis_prd_se
                params.update({key: str(value) for key, value in profile.static_params.items()})
                if profile.industry_dimension_key:
                    params[profile.industry_dimension_key] = selection.code
                requests.append(
                    KosisProfileRequest(
                        profile_name=profile.name,
                        profile_label=profile.label,
                        profile_kind=profile.kind,
                        metric_key=metric_key,
                        metric_item_id=metric_item_id,
                        source_label=f"{self.SOURCE_LABEL} / {profile.label}",
                        source_table_id=profile.tbl_id,
                        industry_code=selection.code,
                        industry_label=selection.label,
                        start_year=start_year,
                        end_year=end_year,
                        params={key: str(value) for key, value in params.items()},
                    )
                )
        return requests

    def build_request(
        self,
        selection: KosisIndustrySelection,
        *,
        reference_year: int | None = None,
    ) -> KosisEmployeeRequest:
        requests = self.build_requests(selection, reference_year=reference_year)
        employee_request = next((item for item in requests if item.metric_key == "employee_count"), None)
        request = employee_request or (requests[0] if requests else None)
        if request is None:
            raise RuntimeError("KOSIS employee service is not configured")
        return KosisEmployeeRequest(
            industry_code=request.industry_code,
            industry_label=request.industry_label,
            reference_year=request.end_year,
            params=request.params,
        )

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    def fetch_profile(self, request: KosisProfileRequest) -> KosisProfileResponse:
        if not self.settings.kosis_api_key:
            raise RuntimeError("KOSIS employee service is not configured")
        with httpx.Client(timeout=20.0) as client:
            response = client.get(self.settings.kosis_base_url, params=request.params)
            response.raise_for_status()
        payload = response.json()
        rows = payload if isinstance(payload, list) else [payload]
        error_message = self._extract_error(rows)
        if error_message:
            raise RuntimeError(error_message)
        series = self._extract_series(rows)
        latest_value = series[-1].value if series else self._extract_numeric_value(rows[0]) if rows else None
        return KosisProfileResponse(
            profile_name=request.profile_name,
            profile_label=request.profile_label,
            profile_kind=request.profile_kind,
            metric_key=request.metric_key,
            source_label=request.source_label,
            source_table_id=request.source_table_id,
            industry_code=request.industry_code,
            industry_label=request.industry_label,
            start_year=request.start_year,
            end_year=request.end_year,
            latest_value=latest_value,
            cagr=self._compute_cagr(series),
            regional_concentration=self._compute_regional_concentration(rows),
            series=series,
            rows=rows,
        )

    def fetch(self, request: KosisEmployeeRequest) -> KosisEmployeeResponse:
        profile_request = KosisProfileRequest(
            profile_name="legacy-employee-count",
            profile_label="Legacy employee count",
            profile_kind="structure",
            metric_key="employee_count",
            metric_item_id=request.params.get("itmId", ""),
            source_label=self.SOURCE_LABEL,
            source_table_id=request.params.get("tblId", ""),
            industry_code=request.industry_code,
            industry_label=request.industry_label,
            start_year=request.reference_year,
            end_year=request.reference_year,
            params=request.params,
        )
        profile_response = self.fetch_profile(profile_request)
        employee_count = int(profile_response.latest_value) if profile_response.latest_value is not None else None
        return KosisEmployeeResponse(
            industry_code=request.industry_code,
            industry_label=request.industry_label,
            reference_year=request.reference_year,
            employee_count=employee_count,
            source_label=profile_response.source_label,
            source_table_id=profile_response.source_table_id,
            rows=profile_response.rows,
        )

    def build_market_context(
        self,
        *,
        selection: KosisIndustrySelection,
        responses: list[KosisProfileResponse],
        rationale: str,
    ) -> MarketSizeContext:
        latest = {response.metric_key: response.latest_value for response in responses if response.latest_value is not None}
        business_count = self._to_int(latest.get("business_count"))
        employee_count = self._to_int(latest.get("employee_count"))
        revenue = latest.get("revenue")
        value_added = latest.get("value_added")
        revenue_per_employee = (revenue / employee_count) if revenue is not None and employee_count else None
        business_cagr = self._first_metric_cagr(responses, "business_count")
        employee_cagr = self._first_metric_cagr(responses, "employee_count")
        regional_concentration = max(
            (response.regional_concentration for response in responses if response.regional_concentration is not None),
            default=None,
        )
        reference_year = max((response.end_year for response in responses), default=max(2000, date.today().year - 1))
        profile_summaries = [self._profile_summary(response) for response in responses]

        summary_parts: list[str] = []
        if business_count is not None and employee_count is not None:
            summary_parts.append(
                f"{reference_year}년 기준 {selection.label} 사업체 수는 약 {business_count:,}개, 종사자 수는 약 {employee_count:,}명이다."
            )
            avg_employees = employee_count / business_count if business_count else None
            if avg_employees is not None:
                summary_parts.append(f"사업체당 평균 종사자 수는 약 {avg_employees:.1f}명으로 추정된다.")
        elif employee_count is not None:
            summary_parts.append(f"{reference_year}년 기준 {selection.label} 종사자 수는 약 {employee_count:,}명이다.")
        elif business_count is not None:
            summary_parts.append(f"{reference_year}년 기준 {selection.label} 사업체 수는 약 {business_count:,}개다.")

        if revenue is not None:
            revenue_summary = f"매출액은 약 {revenue:,.0f}"
            if value_added is not None:
                revenue_summary += f", 부가가치는 약 {value_added:,.0f}"
            revenue_summary += "로 집계된다."
            summary_parts.append(revenue_summary)
            if revenue_per_employee is not None:
                summary_parts.append(f"종사자 1인당 매출은 약 {revenue_per_employee:,.0f} 수준이다.")

        growth_parts: list[str] = []
        if business_cagr is not None:
            growth_parts.append(f"사업체 CAGR {business_cagr * 100:.1f}%")
        if employee_cagr is not None:
            growth_parts.append(f"종사자 CAGR {employee_cagr * 100:.1f}%")
        if growth_parts:
            summary_parts.append(", ".join(growth_parts) + "로 계산된다.")

        if regional_concentration is not None:
            summary_parts.append(f"지역 집중도 지표는 약 {regional_concentration:.2f}배 수준이다.")

        if not summary_parts:
            summary_parts.append(
                f"{selection.label} 관련 KOSIS 프로필 조회는 완료됐지만 바로 해석 가능한 핵심 수치를 추출하지 못했다."
            )

        return MarketSizeContext(
            source=self.SOURCE,
            source_label=self.SOURCE_LABEL,
            industry_code=selection.code,
            industry_label=selection.label,
            reference_year=reference_year,
            employee_count=employee_count,
            business_count=business_count,
            revenue=revenue,
            value_added=value_added,
            revenue_per_employee=revenue_per_employee,
            employee_cagr=employee_cagr,
            business_cagr=business_cagr,
            regional_concentration=regional_concentration,
            profile_summaries=profile_summaries,
            summary=" ".join(summary_parts),
            rationale=rationale,
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
                f"KOSIS 기준 {response.reference_year}년 {response.industry_label} 종사자 수는 "
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
        return KosisEmployeeService().build_market_size_context(response, rationale=rationale)

    def _legacy_profile_option(self) -> KosisProfileOption | None:
        if not (self.settings.kosis_tbl_id and self.settings.kosis_employee_itm_id):
            return None
        static_params = json.loads(self.settings.kosis_static_params_json) if self.settings.kosis_static_params_json else {}
        return KosisProfileOption(
            name="legacy-employee-count",
            label="Legacy employee count",
            kind="structure",
            tbl_id=self.settings.kosis_tbl_id,
            metrics={"employee_count": self.settings.kosis_employee_itm_id},
            static_params={key: str(value) for key, value in static_params.items()},
            industry_dimension_key=self.settings.kosis_industry_dimension_key,
        )

    def _resolve_year_range(self, profile: KosisProfileOption, reference_year: int | None) -> tuple[int, int]:
        if profile.time_range:
            years = sorted(profile.time_range)
            return years[0], years[-1]
        year = reference_year or max(2000, date.today().year - self.settings.kosis_reference_year_offset)
        return year, year

    @staticmethod
    def _profile_applies(profile: KosisProfileOption, industry_code: str) -> bool:
        if profile.applies_to_prefixes and not any(
            industry_code.startswith(prefix) for prefix in profile.applies_to_prefixes
        ):
            return False
        if profile.exclude_prefixes and any(industry_code.startswith(prefix) for prefix in profile.exclude_prefixes):
            return False
        return True

    @staticmethod
    def _extract_series(rows: list[dict[str, Any]]) -> list[KosisMetricPoint]:
        points: list[KosisMetricPoint] = []
        for index, row in enumerate(rows):
            value = KosisEmployeeService._extract_numeric_value(row)
            if value is None:
                continue
            period = KosisEmployeeService._extract_period_label(row, index)
            points.append(KosisMetricPoint(period=period, value=value))
        digit_only = all(point.period.isdigit() for point in points)
        if digit_only:
            points.sort(key=lambda point: point.period)
        return points

    @staticmethod
    def _extract_period_label(row: dict[str, Any], index: int) -> str:
        candidate_keys = ("PRD_DE", "prdDe", "PRD_DE_NM", "C1_NM", "C2_NM", "C3_NM", "C4_NM")
        for key in candidate_keys:
            value = row.get(key)
            if value not in (None, ""):
                return str(value)
        return str(index)

    @staticmethod
    def _extract_numeric_value(row: dict[str, Any]) -> float | None:
        candidate_keys = ("DT", "dt", "DATA_VALUE", "data_value", "value")
        for key in candidate_keys:
            value = row.get(key)
            if value in (None, "", "-"):
                continue
            cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch in (".", "-"))
            if cleaned in ("", "-", "."):
                continue
            return float(cleaned)
        return None

    @staticmethod
    def _compute_cagr(series: list[KosisMetricPoint]) -> float | None:
        if len(series) < 2:
            return None
        start_value = series[0].value
        end_value = series[-1].value
        if start_value <= 0 or end_value <= 0:
            return None
        years = max(1, len(series) - 1)
        return pow(end_value / start_value, 1 / years) - 1

    @staticmethod
    def _compute_regional_concentration(rows: list[dict[str, Any]]) -> float | None:
        values = [value for row in rows if (value := KosisEmployeeService._extract_numeric_value(row)) is not None]
        if len(values) < 2:
            return None
        average = sum(values) / len(values)
        if average <= 0:
            return None
        return max(values) / average

    @staticmethod
    def _extract_error(rows: list[dict[str, Any]]) -> str | None:
        for row in rows:
            error_code = row.get("err") or row.get("ERR")
            error_message = row.get("errMsg") or row.get("ERR_MSG")
            if error_code and str(error_code) != "0":
                return str(error_message or error_code)
        return None

    @staticmethod
    def _to_int(value: float | None) -> int | None:
        return int(round(value)) if value is not None else None

    @staticmethod
    def _first_metric_cagr(responses: list[KosisProfileResponse], metric_key: str) -> float | None:
        for response in responses:
            if response.metric_key == metric_key and response.cagr is not None:
                return response.cagr
        return None

    @staticmethod
    def _profile_summary(response: KosisProfileResponse) -> str:
        parts = [f"{response.profile_label} / {response.metric_key}"]
        if response.latest_value is not None:
            parts.append(f"최근값 {response.latest_value:,.0f}")
        if response.cagr is not None:
            parts.append(f"CAGR {response.cagr * 100:.1f}%")
        if response.regional_concentration is not None:
            parts.append(f"집중도 {response.regional_concentration:.2f}")
        return ", ".join(parts)

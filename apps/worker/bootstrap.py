"""공통 worker 부트스트랩 유틸리티"""
from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """표준 로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )


def run_worker(main_fn, *, job_name: str) -> None:
    """worker 함수를 실행하고 에러를 표준 방식으로 처리"""
    setup_logging()
    logger = logging.getLogger(job_name)
    try:
        main_fn()
    except KeyboardInterrupt:
        logger.info("interrupted by user")
        sys.exit(0)
    except Exception as exc:
        logger.exception("worker failed: %s", exc)
        sys.exit(1)

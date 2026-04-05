from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from micro_niche_finder.api.deps import get_app_container, get_db_session
from micro_niche_finder.bootstrap import ApplicationContainer
from micro_niche_finder.domain.schemas import (
    CreateSeedCategoryRequest,
    FinalReportRead,
    PipelineRunRequest,
    PipelineRunResponse,
    SeedCategoryRead,
)
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


router = APIRouter()


@router.post("/seeds", response_model=SeedCategoryRead)
def create_seed_category(
    payload: CreateSeedCategoryRequest,
    db: Session = Depends(get_db_session),
) -> SeedCategoryRead:
    repo = SeedCategoryRepository(db)
    seed = repo.create(name=payload.name, description=payload.description)
    db.commit()
    db.refresh(seed)
    return SeedCategoryRead.model_validate(seed)


@router.get("/seeds", response_model=list[SeedCategoryRead])
def list_seed_categories(db: Session = Depends(get_db_session)) -> list[SeedCategoryRead]:
    repo = SeedCategoryRepository(db)
    return [SeedCategoryRead.model_validate(item) for item in repo.list_all()]


@router.post("/pipeline/run", response_model=PipelineRunResponse)
def run_pipeline(
    payload: PipelineRunRequest,
    db: Session = Depends(get_db_session),
    container: ApplicationContainer = Depends(get_app_container),
) -> PipelineRunResponse:
    try:
        response = container.pipeline_service.run(
            session=db,
            seed_category_id=payload.seed_category_id,
            candidate_count=payload.candidate_count,
            top_k=payload.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return response


@router.get("/reports", response_model=list[FinalReportRead])
def list_reports(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db_session),
) -> list[FinalReportRead]:
    repo = SeedCategoryRepository(db)
    return repo.list_reports(limit=limit)

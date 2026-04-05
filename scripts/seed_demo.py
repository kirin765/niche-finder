from sqlalchemy.orm import Session

from micro_niche_finder.config.database import SessionLocal
from micro_niche_finder.repos.candidate_repo import SeedCategoryRepository


def main() -> None:
    with SessionLocal() as session:
        repo = SeedCategoryRepository(session)
        existing = repo.get(1)
        if existing:
            print(f"Seed already exists: {existing.id} {existing.name}")
            return
        seed = repo.create(
            name="스마트스토어 운영",
            description="한국 소형 셀러의 반복 업무 SaaS 기회 탐색",
        )
        session.commit()
        print(f"Created seed category: {seed.id} {seed.name}")


if __name__ == "__main__":
    main()

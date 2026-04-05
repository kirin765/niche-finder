from micro_niche_finder.domain.schemas import CandidateGenerationResult
from micro_niche_finder.services.llm_service import OpenAIResearchService


def run(seed_category: str, candidate_count: int, llm_service: OpenAIResearchService) -> CandidateGenerationResult:
    return llm_service.generate_candidates(seed_category=seed_category, candidate_count=candidate_count)

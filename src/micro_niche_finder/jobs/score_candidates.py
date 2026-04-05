from micro_niche_finder.domain.schemas import ProblemCandidateGenerated, ScoreBreakdown, TrendFeatureSet
from micro_niche_finder.services.scoring_service import ScoringService


def run(
    *,
    candidate: ProblemCandidateGenerated,
    features: TrendFeatureSet,
    scoring_service: ScoringService,
) -> ScoreBreakdown:
    return scoring_service.score(candidate=candidate, features=features)

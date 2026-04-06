from micro_niche_finder.domain.schemas import OnlineGTMContext
from micro_niche_finder.jobs.pipeline import combine_online_gtm_contexts, combine_search_channel_scores


def test_combine_search_channel_scores_uses_available_sources_only() -> None:
    assert combine_search_channel_scores(
        naver_score=0.6,
        google_score=None,
        naver_weight=0.65,
        google_weight=0.35,
    ) == 0.6


def test_combine_search_channel_scores_respects_weights() -> None:
    score = combine_search_channel_scores(
        naver_score=0.8,
        google_score=0.4,
        naver_weight=0.65,
        google_weight=0.35,
    )

    assert round(score, 4) == 0.66


def test_combine_online_gtm_contexts_merges_counts_and_scores() -> None:
    naver = OnlineGTMContext(
        query="학원 상담 관리",
        channel_signals=["네이버 검색", "커뮤니티"],
        channel_counts={"community": 2, "blog_content": 1, "competitor": 1, "government": 0, "noise": 0},
        community_presence_score=0.5,
        seo_discoverability_score=0.4,
        competitor_presence_score=0.3,
        summary="naver",
    )
    google = OnlineGTMContext(
        query="학원 상담 관리",
        channel_signals=["Google 검색", "블로그 SEO"],
        channel_counts={"community": 0, "blog_content": 2, "competitor": 1, "government": 1, "noise": 0},
        community_presence_score=0.1,
        seo_discoverability_score=0.6,
        competitor_presence_score=0.5,
        summary="google",
    )

    merged = combine_online_gtm_contexts(
        naver_context=naver,
        google_context=google,
        naver_weight=0.65,
        google_weight=0.35,
    )

    assert merged is not None
    assert merged.channel_counts["community"] == 2
    assert merged.channel_counts["blog_content"] == 3
    assert merged.channel_counts["competitor"] == 2
    assert merged.community_presence_score == 0.36
    assert merged.seo_discoverability_score == 0.47
    assert merged.competitor_presence_score == 0.37
    assert "네이버 검색" in merged.channel_signals
    assert "Google 검색" in merged.channel_signals

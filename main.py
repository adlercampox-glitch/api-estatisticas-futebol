from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="Estatisticas Futebol API",
    version="1.0.0",
    description="API para análise estatística de jogos de futebol"
)


class MatchRef(BaseModel):
    home_team: str
    away_team: str
    competition: str
    match_date: date
    country: Optional[str] = None


class MatchAnalysisOptions(BaseModel):
    include_injuries: bool = True
    include_form: bool = True
    include_xg: bool = True
    include_odds_analysis: bool = False
    lookback_matches: int = Field(default=10, ge=3, le=20)
    markets: Optional[List[Literal["1x2", "over_under", "btts", "asian_handicap", "european_handicap"]]] = None
    bookmakers: Optional[List[str]] = None


class MatchAnalysisRequest(BaseModel):
    matches: List[MatchRef]
    options: Optional[MatchAnalysisOptions] = MatchAnalysisOptions()


class MatchMetrics(BaseModel):
    expected_home_goals: float
    expected_away_goals: float
    expected_total_goals: float
    handicap_strength_diff: float
    over_1_5_prob: float
    over_2_5_prob: float
    over_3_5_prob: float
    btts_prob: float


class MatchContext(BaseModel):
    injury_impact: Optional[str] = None
    rotation_risk: Optional[str] = None
    recent_form_summary: Optional[str] = None
    style_summary: Optional[str] = None


class MatchClassifications(BaseModel):
    goal_profile: Literal["low", "medium", "high"]
    technical_gap: Literal["low", "medium", "high"]
    reading_risk: Literal["low", "medium", "high"]


class OddsMarketAnalysis(BaseModel):
    market_name: str
    selection: str
    best_odd: float
    worst_odd: float
    average_odd: float
    implied_probability_best: float
    implied_probability_average: float
    dispersion_percent: float
    distortion_level: Literal["low", "medium", "high"]
    consensus_position: Literal["below_market", "near_consensus", "above_market"]
    bookmaker_best: Optional[str] = None
    bookmaker_worst: Optional[str] = None
    market_comment: Optional[str] = None


class OddsAnalysis(BaseModel):
    markets: List[OddsMarketAnalysis]


class MatchAnalysisItem(BaseModel):
    match: MatchRef
    metrics: MatchMetrics
    context: Optional[MatchContext] = None
    classifications: MatchClassifications
    odds_analysis: Optional[OddsAnalysis] = None
    confidence: Literal["low", "medium", "high"]
    source_summary: List[str]


class MatchAnalysisResponse(BaseModel):
    generated_at: datetime
    matches: List[MatchAnalysisItem]


class OddsComparisonRequest(BaseModel):
    matches: List[MatchRef]
    markets: List[Literal["1x2", "over_under", "btts", "asian_handicap", "european_handicap"]]
    bookmakers: Optional[List[str]] = None


class OddsComparisonItem(BaseModel):
    match: MatchRef
    odds_analysis: OddsAnalysis
    confidence: Literal["low", "medium", "high"]
    source_summary: List[str]


class OddsComparisonResponse(BaseModel):
    generated_at: datetime
    matches: List[OddsComparisonItem]


def classify_goal_profile(total_goals: float) -> str:
    if total_goals < 2.2:
        return "low"
    if total_goals < 3.0:
        return "medium"
    return "high"


def classify_technical_gap(diff: float) -> str:
    abs_diff = abs(diff)
    if abs_diff < 0.35:
        return "low"
    if abs_diff < 0.75:
        return "medium"
    return "high"


def build_mock_metrics(home_team: str, away_team: str) -> MatchMetrics:
    base_home = 1.45
    base_away = 1.05
    modifier = ((len(home_team) - len(away_team)) % 5) * 0.08

    home_xg = round(base_home + modifier, 2)
    away_xg = round(base_away - (modifier / 2), 2)
    total_xg = round(home_xg + away_xg, 2)
    diff = round(home_xg - away_xg, 2)

    return MatchMetrics(
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
        expected_total_goals=total_xg,
        handicap_strength_diff=diff,
        over_1_5_prob=0.78 if total_xg >= 2.4 else 0.66,
        over_2_5_prob=0.58 if total_xg >= 2.6 else 0.44,
        over_3_5_prob=0.31 if total_xg >= 2.9 else 0.20,
        btts_prob=0.57 if away_xg >= 1.0 else 0.46,
    )


def build_mock_odds_analysis(markets: Optional[List[str]] = None) -> OddsAnalysis:
    selected_markets = markets or ["over_under", "1x2"]
    items: List[OddsMarketAnalysis] = []

    if "over_under" in selected_markets:
        items.append(
            OddsMarketAnalysis(
                market_name="over_under",
                selection="over_2_5",
                best_odd=1.98,
                worst_odd=1.86,
                average_odd=1.91,
                implied_probability_best=0.5051,
                implied_probability_average=0.5236,
                dispersion_percent=6.45,
                distortion_level="high",
                consensus_position="above_market",
                bookmaker_best="Book A",
                bookmaker_worst="Book B",
                market_comment="Linha acima do consenso médio entre operadores."
            )
        )

    if "1x2" in selected_markets:
        items.append(
            OddsMarketAnalysis(
                market_name="1x2",
                selection="home_win",
                best_odd=1.87,
                worst_odd=1.78,
                average_odd=1.82,
                implied_probability_best=0.5348,
                implied_probability_average=0.5495,
                dispersion_percent=5.06,
                distortion_level="high",
                consensus_position="above_market",
                bookmaker_best="Book C",
                bookmaker_worst="Book D",
                market_comment="Preço acima da média do mercado."
            )
        )

    if "btts" in selected_markets:
        items.append(
            OddsMarketAnalysis(
                market_name="btts",
                selection="yes",
                best_odd=1.95,
                worst_odd=1.89,
                average_odd=1.92,
                implied_probability_best=0.5128,
                implied_probability_average=0.5208,
                dispersion_percent=3.17,
                distortion_level="medium",
                consensus_position="near_consensus",
                bookmaker_best="Book A",
                bookmaker_worst="Book C",
                market_comment="Mercado próximo do consenso, com dispersão moderada."
            )
        )

    return OddsAnalysis(markets=items)


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Estatisticas Futebol API online"
    }


@app.get("/matches/daily")
def get_daily_matches(
    match_date: date = Query(..., description="Data YYYY-MM-DD"),
    country: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    sample_matches = [
        {
            "home_team": "Flamengo",
            "away_team": "Palmeiras",
            "competition": competition or "Serie A",
            "match_date": match_date,
            "country": country or "Brazil",
        },
        {
            "home_team": "Liverpool",
            "away_team": "Arsenal",
            "competition": competition or "Premier League",
            "match_date": match_date,
            "country": country or "England",
        },
        {
            "home_team": "Barcelona",
            "away_team": "Atletico Madrid",
            "competition": competition or "La Liga",
            "match_date": match_date,
            "country": country or "Spain",
        },
    ]

    return {
        "generated_at": datetime.utcnow(),
        "matches": sample_matches[:limit]
    }


@app.post("/matches/analyze", response_model=MatchAnalysisResponse)
def analyze_matches(payload: MatchAnalysisRequest):
    results: List[MatchAnalysisItem] = []

    for match in payload.matches:
        metrics = build_mock_metrics(match.home_team, match.away_team)

        classifications = MatchClassifications(
            goal_profile=classify_goal_profile(metrics.expected_total_goals),
            technical_gap=classify_technical_gap(metrics.handicap_strength_diff),
            reading_risk="medium"
        )

        odds_analysis = None
        if payload.options and payload.options.include_odds_analysis:
            odds_analysis = build_mock_odds_analysis(payload.options.markets)

        results.append(
            MatchAnalysisItem(
                match=match,
                metrics=metrics,
                context=MatchContext(
                    injury_impact="unknown",
                    rotation_risk="medium",
                    recent_form_summary=f"{match.home_team} e {match.away_team} analisados com base mockada inicial.",
                    style_summary=f"Leitura preliminar de {match.home_team} x {match.away_team} com projeção estatística simplificada."
                ),
                classifications=classifications,
                odds_analysis=odds_analysis,
                confidence="medium",
                source_summary=["mock_engine", "initial_model"]
            )
        )

    return MatchAnalysisResponse(
        generated_at=datetime.utcnow(),
        matches=results
    )


@app.post("/odds/compare", response_model=OddsComparisonResponse)
def compare_odds(payload: OddsComparisonRequest):
    results: List[OddsComparisonItem] = []

    for match in payload.matches:
        results.append(
            OddsComparisonItem(
                match=match,
                odds_analysis=build_mock_odds_analysis(payload.markets),
                confidence="medium",
                source_summary=["mock_market_engine"]
            )
        )

    return OddsComparisonResponse(
        generated_at=datetime.utcnow(),
        matches=results
    )
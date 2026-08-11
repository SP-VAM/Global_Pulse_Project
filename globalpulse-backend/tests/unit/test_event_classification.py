"""
Unit tests for event classification services:
  - rules.classify_text (category classification)
  - country_tagger.tag_countries
  - company_tagger.tag_companies / extract_sectors
  - relevance_filter.score_relevance
  - EventClassificationService (orchestrator + deduplication)
"""
from __future__ import annotations

import pytest

from app.domain.news import CompanyTag, GlobalEventCategory
from app.services.classification.company_tagger import extract_sectors, tag_companies
from app.services.classification.country_tagger import tag_countries
from app.services.classification.relevance_filter import RELEVANCE_THRESHOLD, score_relevance
from app.services.classification.rules import classify_text
from app.services.event_classification_service import EventClassificationService


# ---------------------------------------------------------------------------
# Category classification tests
# ---------------------------------------------------------------------------

class TestClassifyText:
    def test_war_conflict_keywords(self):
        primary, tags, keywords = classify_text("missile strike kills dozens in military conflict")
        assert primary == GlobalEventCategory.WAR_CONFLICT

    def test_natural_disaster(self):
        primary, _, _ = classify_text("major earthquake devastates coastal city, tsunami advisory issued")
        assert primary == GlobalEventCategory.NATURAL_DISASTER

    def test_central_bank(self):
        primary, _, _ = classify_text("Federal Reserve raises interest rate decision by 25bps")
        assert primary == GlobalEventCategory.CENTRAL_BANK

    def test_supply_chain(self):
        primary, _, _ = classify_text("port closure disrupts global supply chain shipping")
        assert primary == GlobalEventCategory.SUPPLY_CHAIN

    def test_energy(self):
        primary, _, _ = classify_text("OPEC+ cuts crude oil production, energy supply concerns")
        assert primary == GlobalEventCategory.ENERGY

    def test_geopolitics(self):
        primary, _, _ = classify_text("diplomatic summit resolves territory dispute between nations")
        assert primary == GlobalEventCategory.GEOPOLITICS

    def test_corporate(self):
        primary, _, _ = classify_text("Apple reports record quarterly earnings, CEO announces share repurchase buyback")
        assert primary == GlobalEventCategory.CORPORATE

    def test_economy(self):
        primary, _, _ = classify_text("GDP growth rate slows amid rising inflation rate and budget deficit")
        assert primary == GlobalEventCategory.ECONOMY

    def test_financial_markets(self):
        primary, _, _ = classify_text("S&P 500 stock market dow jones rally as equity market rebounds")
        assert primary == GlobalEventCategory.FINANCIAL_MARKETS

    def test_technology(self):
        primary, _, _ = classify_text("new artificial intelligence model released by leading tech company")
        assert primary == GlobalEventCategory.TECHNOLOGY

    def test_unknown_is_other(self):
        primary, _, _ = classify_text("local weather report for tomorrow")
        assert primary == GlobalEventCategory.OTHER

    def test_priority_war_over_energy(self):
        """WAR_CONFLICT > ENERGY in priority order."""
        primary, tags, _ = classify_text("military airstrike destroys oil refinery and pipeline")
        assert primary == GlobalEventCategory.WAR_CONFLICT
        assert "ENERGY" in tags

    def test_priority_natural_disaster_over_supply_chain(self):
        """NATURAL_DISASTER > SUPPLY_CHAIN."""
        primary, tags, _ = classify_text("earthquake disrupts supply chain and port closure")
        assert primary == GlobalEventCategory.NATURAL_DISASTER

    def test_multiple_matches_produces_tags(self):
        primary, tags, _ = classify_text("central bank raises interest rate decision amid inflation rate gdp growth slowdown")
        assert primary == GlobalEventCategory.CENTRAL_BANK
        assert len(tags) > 0

    def test_empty_text_is_other(self):
        primary, tags, keywords = classify_text("")
        assert primary == GlobalEventCategory.OTHER
        assert tags == []
        assert keywords == []

    def test_matched_keywords_returned(self):
        _, _, keywords = classify_text("earthquake tsunami flood")
        assert "earthquake" in keywords or "tsunami" in keywords

    def test_war_not_matched_in_warning(self):
        """'war' should NOT match 'warning' or 'reward'."""
        primary, _, _ = classify_text("tsunami warning issued, reward offered for information")
        assert primary == GlobalEventCategory.NATURAL_DISASTER  # Only natural disaster keywords match


# ---------------------------------------------------------------------------
# Country tagger tests
# ---------------------------------------------------------------------------

class TestCountryTagger:
    def test_detects_united_states(self):
        assert "US" in tag_countries("The Federal Reserve in United States raised rates")

    def test_detects_india_from_rbi(self):
        assert "IN" in tag_countries("RBI keeps repo rate unchanged")

    def test_detects_india_from_mumbai(self):
        assert "IN" in tag_countries("Markets in Mumbai fell sharply")

    def test_detects_japan(self):
        assert "JP" in tag_countries("Bank of Japan policy decision in Tokyo")

    def test_detects_germany(self):
        assert "DE" in tag_countries("Frankfurt-based Bundesbank warns of slowdown")

    def test_detects_uk(self):
        assert "GB" in tag_countries("Bank of England in London raised interest rates")

    def test_detects_singapore(self):
        assert "SG" in tag_countries("MAS Singapore tightens monetary policy")

    def test_multiple_countries(self):
        result = tag_countries("Trade war between United States and China")
        assert "US" in result
        assert "CN" in result

    def test_empty_text_returns_empty(self):
        assert tag_countries("") == []

    def test_no_country_mention_returns_empty(self):
        assert tag_countries("the sky is blue today") == []

    def test_short_alias_no_false_positive(self):
        """'US' should not match 'bus', 'fuss', 'plus', etc."""
        result = tag_countries("the bus was late")
        assert "US" not in result

    def test_result_is_deduplicated(self):
        result = tag_countries("US America USA Wall Street")
        assert result.count("US") == 1


# ---------------------------------------------------------------------------
# Company tagger tests
# ---------------------------------------------------------------------------

class TestCompanyTagger:
    def test_detects_apple(self):
        tags = tag_companies("Apple reports record iPhone sales")
        names = [t.name for t in tags]
        assert "Apple" in names

    def test_detects_tsmc(self):
        tags = tag_companies("TSMC Taiwan semiconductor production cut")
        names = [t.name for t in tags]
        assert "TSMC" in names

    def test_detects_dbs(self):
        tags = tag_companies("DBS Bank Singapore raises dividend")
        names = [t.name for t in tags]
        assert "DBS Bank" in names

    def test_detects_toyota(self):
        tags = tag_companies("Toyota automobile recalls in Japan")
        names = [t.name for t in tags]
        assert "Toyota" in names

    def test_sector_is_correct(self):
        tags = tag_companies("TSMC chip maker reports strong results")
        tsmc = next((t for t in tags if t.name == "TSMC"), None)
        assert tsmc is not None
        assert tsmc.sector == "Semiconductors"

    def test_country_is_correct(self):
        tags = tag_companies("Infosys quarterly results beat estimates")
        infosys = next((t for t in tags if t.name == "Infosys"), None)
        assert infosys is not None
        assert infosys.country == "IN"

    def test_no_match_returns_empty(self):
        tags = tag_companies("local farmer reports good harvest this year")
        assert tags == []

    def test_deduplication(self):
        """Same company mentioned multiple times should appear only once."""
        tags = tag_companies("Apple iphone Apple aapl Apple")
        names = [t.name for t in tags]
        assert names.count("Apple") == 1

    def test_extract_sectors(self):
        tags = [
            CompanyTag(name="Apple", sector="Technology", country="US"),
            CompanyTag(name="TSMC", sector="Semiconductors", country="TW"),
            CompanyTag(name="Nvidia", sector="Semiconductors", country="US"),
        ]
        sectors = extract_sectors(tags)
        assert "Technology" in sectors
        assert "Semiconductors" in sectors
        assert len(sectors) == 2  # Deduplicated


# ---------------------------------------------------------------------------
# Relevance filter tests
# ---------------------------------------------------------------------------

class TestRelevanceFilter:
    def test_central_bank_category_is_relevant(self):
        is_rel, score = score_relevance(
            "Federal Reserve raises interest rate",
            GlobalEventCategory.CENTRAL_BANK,
            [],
            [],
        )
        assert is_rel is True
        assert score >= RELEVANCE_THRESHOLD

    def test_war_conflict_is_relevant(self):
        is_rel, score = score_relevance(
            "military invasion disrupts crude oil supply and sanctions imposed",
            GlobalEventCategory.WAR_CONFLICT,
            [],
            [],
        )
        assert is_rel is True

    def test_company_presence_increases_score(self):
        _, score_no_company = score_relevance(
            "quarterly earnings report released",
            GlobalEventCategory.CORPORATE,
            [],
            [],
        )
        company_tags = [CompanyTag(name="Apple", sector="Technology", country="US")]
        _, score_with_company = score_relevance(
            "quarterly earnings report released",
            GlobalEventCategory.CORPORATE,
            company_tags,
            ["Technology"],
        )
        assert score_with_company > score_no_company

    def test_irrelevant_article_scores_low(self):
        is_rel, score = score_relevance(
            "local sports team wins championship",
            GlobalEventCategory.OTHER,
            [],
            [],
        )
        assert is_rel is False


# ---------------------------------------------------------------------------
# EventClassificationService orchestrator tests
# ---------------------------------------------------------------------------

class TestEventClassificationService:
    def _make_article(self, headline, summary=None, url="http://example.com/1", article_id=None):
        from app.domain.news import NormalizedArticle
        return NormalizedArticle(
            id=article_id or "test-id",
            headline=headline,
            summary=summary,
            source_name="Test",
            source_url=None,
            article_url=url,
            author=None,
            published_at_utc="2024-01-26T14:00:00+00:00",
            published_at_ist="2024-01-26T19:30:00+05:30",
            primary_category=GlobalEventCategory.OTHER,
        )

    def test_war_conflict_classified(self):
        svc = EventClassificationService()
        article = self._make_article("missile attack kills dozens in military conflict")
        classified = svc.classify_batch([article])
        assert classified[0].primary_category == GlobalEventCategory.WAR_CONFLICT

    def test_natural_disaster_classified(self):
        svc = EventClassificationService()
        article = self._make_article("earthquake triggers tsunami warning, floods reported")
        classified = svc.classify_batch([article])
        assert classified[0].primary_category == GlobalEventCategory.NATURAL_DISASTER

    def test_geopolitics_classified(self):
        svc = EventClassificationService()
        article = self._make_article("diplomatic tensions escalate between US and China over trade war")
        classified = svc.classify_batch([article])
        assert classified[0].primary_category in (
            GlobalEventCategory.GEOPOLITICS, GlobalEventCategory.WAR_CONFLICT,
            GlobalEventCategory.ECONOMY, GlobalEventCategory.SUPPLY_CHAIN,
        )

    def test_supply_chain_classified(self):
        svc = EventClassificationService()
        article = self._make_article("port closure disrupts global supply chain logistics")
        classified = svc.classify_batch([article])
        assert classified[0].primary_category == GlobalEventCategory.SUPPLY_CHAIN

    def test_corporate_classified(self):
        svc = EventClassificationService()
        article = self._make_article("Apple quarterly earnings beat estimates, CEO announces buyback")
        classified = svc.classify_batch([article])
        assert classified[0].primary_category == GlobalEventCategory.CORPORATE

    def test_url_deduplication(self):
        svc = EventClassificationService()
        a1 = self._make_article("War breaks out", url="http://example.com/war")
        a2 = self._make_article("War spreads", url="http://example.com/war")  # Same URL
        classified = svc.classify_batch([a1, a2])
        assert len(classified) == 1

    def test_headline_deduplication(self):
        svc = EventClassificationService()
        a1 = self._make_article("War breaks out in region", url="http://source1.com/war")
        a2 = self._make_article("War breaks out in region", url="http://source2.com/war")  # Same headline
        classified = svc.classify_batch([a1, a2])
        assert len(classified) == 1

    def test_different_headlines_not_deduplicated(self):
        svc = EventClassificationService()
        a1 = self._make_article("War breaks out in region A", url="http://example.com/a")
        a2 = self._make_article("Floods hit coastal cities", url="http://example.com/b")
        classified = svc.classify_batch([a1, a2])
        assert len(classified) == 2

    def test_country_tagging(self):
        svc = EventClassificationService()
        article = self._make_article("Federal Reserve in United States raises rates")
        classified = svc.classify_batch([article])
        assert "US" in classified[0].countries

    def test_company_tagging(self):
        svc = EventClassificationService()
        article = self._make_article("TSMC Taiwan semiconductor announces expansion")
        classified = svc.classify_batch([article])
        names = [c.name for c in classified[0].companies]
        assert "TSMC" in names

    def test_sector_derived_from_companies(self):
        svc = EventClassificationService()
        article = self._make_article("Infosys TCS Wipro report quarterly results")
        classified = svc.classify_batch([article])
        assert "Technology" in classified[0].sectors

    def test_missing_summary_handled(self):
        svc = EventClassificationService()
        article = self._make_article("Interest rate decision", summary=None)
        classified = svc.classify_batch([article])
        assert classified[0].summary is None  # No crash
        assert classified[0].primary_category is not None

    def test_to_global_events_filters_irrelevant(self):
        svc = EventClassificationService()
        relevant = self._make_article("Federal Reserve FOMC interest rate decision", url="http://a.com/1")
        irrelevant = self._make_article("local dog show results announced", url="http://a.com/2")
        all_classified = svc.classify_batch([relevant, irrelevant])
        events = svc.to_global_events(all_classified)
        # Only financially relevant articles should be in events
        assert all(e.is_financially_relevant for e in events)

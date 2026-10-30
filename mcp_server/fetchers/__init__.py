"""Fetcher registry and dispatch logic."""

from typing import Dict
from mcp_server.fetchers.base import BaseFetcher
from mcp_server.fetchers.the_batch import TheBatchFetcher
from mcp_server.fetchers.guardian import GuardianFetcher
from mcp_server.fetchers.mit import MITTechReviewFetcher, MITNewsFetcher
from mcp_server.fetchers.hacker_news import HackerNewsFetcher
from mcp_server.fetchers.techcrunch import TechCrunchFetcher
from mcp_server.fetchers.ars_technica import ArsTechnicaFetcher

FETCHERS: Dict[str, BaseFetcher] = {
    "the_batch": TheBatchFetcher(),
    "the_guardian": GuardianFetcher(),
    "mit_tech_review": MITTechReviewFetcher(),
    "mit_news": MITNewsFetcher(),
    "hacker_news": HackerNewsFetcher(),
    "techcrunch": TechCrunchFetcher(),
    "ars_technica": ArsTechnicaFetcher(),
}


def get_fetcher(name: str) -> BaseFetcher:
    """Retrieve a fetcher instance by source name."""
    clean_name = name.lower().strip().replace("-", "_").replace(" ", "_")
    if clean_name not in FETCHERS:
        # Fuzzy match
        for key in FETCHERS:
            if key in clean_name or clean_name in key:
                return FETCHERS[key]
        raise ValueError(f"Unknown news source: '{name}'. Available: {list(FETCHERS.keys())}")
    return FETCHERS[clean_name]


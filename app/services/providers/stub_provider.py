"""
In-memory stub provider with a handful of fake sample records.

This exists purely so the API is runnable and testable end-to-end before
you've connected a real data source. Replace with a real DataProvider
implementation before going to production -- these records are fictional.
"""
from __future__ import annotations

from app.services.providers.base import DataProvider, PersonRecord, SearchFilters

_FAKE_RECORDS: list[PersonRecord] = [
    PersonRecord(
        first_name="Jordan",
        last_name="Lee",
        title="VP of Marketing",
        company_name="Northbridge Software",
        company_domain="northbridgesoftware.example",
        linkedin_url="https://linkedin.com/in/example-jordan-lee",
        location="Austin, TX",
        source="stub",
    ),
    PersonRecord(
        first_name="Priya",
        last_name="Natarajan",
        title="Head of Growth",
        company_name="Fernway Labs",
        company_domain="fernwaylabs.example",
        linkedin_url="https://linkedin.com/in/example-priya-natarajan",
        location="Seattle, WA",
        source="stub",
    ),
    PersonRecord(
        first_name="Marcus",
        last_name="Odom",
        title="Director of Demand Generation",
        company_name="Clearlake Analytics",
        company_domain="clearlakeanalytics.example",
        linkedin_url="https://linkedin.com/in/example-marcus-odom",
        location="Denver, CO",
        source="stub",
    ),
]


class StubProvider(DataProvider):
    def search_people(self, filters: SearchFilters) -> list[PersonRecord]:
        results = _FAKE_RECORDS
        if filters.titles:
            lowered = [t.lower() for t in filters.titles]
            results = [r for r in results if r.title and any(t in r.title.lower() for t in lowered)]
        return results[: filters.limit]

    def find_person_by_linkedin_url(self, linkedin_url: str) -> PersonRecord | None:
        for r in _FAKE_RECORDS:
            if r.linkedin_url == linkedin_url:
                return r
        return None


def get_default_provider() -> DataProvider:
    return StubProvider()

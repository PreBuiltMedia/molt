"""
Abstract interface for a people/company data source.

The idea: the API layer never talks to a data source directly. It talks to
this interface. That means you can start with a stub, swap in a licensed
dataset, add your own web-harvesting pipeline, or combine several providers
in a waterfall (try provider A, fall back to provider B) without touching
any API route code.

Nothing in this repo scrapes a named competitor's site. Build your own
providers against sources you have the legal right to use (owned data,
licensed datasets, your own compliant crawler against public pages that
don't prohibit it, carrier APIs for phone, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PersonRecord:
    first_name: str
    last_name: str
    title: str | None
    company_name: str | None
    company_domain: str | None
    linkedin_url: str | None
    location: str | None
    source: str = "unknown"
    extra: dict = field(default_factory=dict)


@dataclass
class SearchFilters:
    titles: list[str] = field(default_factory=list)
    company_employee_min: int | None = None
    company_employee_max: int | None = None
    company_country: str | None = None
    industries: list[str] = field(default_factory=list)
    limit: int = 25


class DataProvider(ABC):
    """Implement this against a real, legally-sourced data backend."""

    @abstractmethod
    def search_people(self, filters: SearchFilters) -> list[PersonRecord]:
        ...

    @abstractmethod
    def find_person_by_linkedin_url(self, linkedin_url: str) -> PersonRecord | None:
        ...

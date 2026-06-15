"""Registry domain module. Domain baru cukup didaftarkan di sini."""

from __future__ import annotations

from app.domains.base import DomainModule
from app.domains.personal import PersonalDomain

DOMAINS: dict[str, DomainModule] = {
    PersonalDomain.domain_id: PersonalDomain(),
    # Phase 2: organizational; Phase 4: sector; Phase 5: product.
}


def get_domain(domain_id: str) -> DomainModule | None:
    return DOMAINS.get(domain_id)

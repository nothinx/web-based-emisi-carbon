"""Registry domain module. Domain baru cukup didaftarkan di sini."""

from __future__ import annotations

from app.domains.base import DomainModule
from app.domains.organizational import OrganizationalDomain
from app.domains.personal import PersonalDomain
from app.domains.sector import SectorDomain

DOMAINS: dict[str, DomainModule] = {
    PersonalDomain.domain_id: PersonalDomain(),
    OrganizationalDomain.domain_id: OrganizationalDomain(),
    SectorDomain.domain_id: SectorDomain(),
    # Phase 5: product.
}


def get_domain(domain_id: str) -> DomainModule | None:
    return DOMAINS.get(domain_id)

from __future__ import annotations

from dataclasses import dataclass


def normalize_domain(domain: str) -> str:
    return domain.strip().rstrip(".").lower().encode("idna").decode("ascii")


@dataclass(frozen=True, slots=True)
class DomainRule:
    domain_id: int
    root_domain_ascii: str
    accept_exact: bool
    accept_subdomains: bool
    plus_addressing_mode: str = "keep"
    local_part_case_sensitive: bool = False

    def normalized_root(self) -> str:
        return normalize_domain(self.root_domain_ascii)


@dataclass(frozen=True, slots=True)
class DomainMatch:
    domain_id: int
    domain_ascii: str
    root_domain_ascii: str
    local_part: str
    local_part_canonical: str
    address_canonical: str


class DomainMatcher:
    def __init__(self, rules: list[DomainRule]) -> None:
        self._rules = sorted(rules, key=lambda rule: len(rule.normalized_root()), reverse=True)

    def match_address(self, address: str) -> DomainMatch | None:
        if "@" not in address:
            return None

        local_part, domain_part = address.rsplit("@", 1)
        normalized_domain = normalize_domain(domain_part)

        for rule in self._rules:
            normalized_root = rule.normalized_root()
            is_exact = normalized_domain == normalized_root
            is_subdomain = normalized_domain.endswith(f".{normalized_root}")
            if not is_exact and not is_subdomain:
                continue
            if is_exact and not rule.accept_exact:
                return None
            if is_subdomain and not rule.accept_subdomains:
                return None

            local_part_canonical = local_part
            if rule.plus_addressing_mode == "strip":
                local_part_canonical = local_part_canonical.split("+", 1)[0]
            if not rule.local_part_case_sensitive:
                local_part_canonical = local_part_canonical.lower()

            return DomainMatch(
                domain_id=rule.domain_id,
                domain_ascii=normalized_domain,
                root_domain_ascii=normalized_root,
                local_part=local_part,
                local_part_canonical=local_part_canonical,
                address_canonical=f"{local_part_canonical}@{normalized_domain}",
            )

        return None

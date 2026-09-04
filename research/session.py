from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
from urllib.parse import urlparse

from core.models import ResearchItem


@dataclass(slots=True)
class ResearchClaim:
    text: str
    source_url: str
    confidence: float = 0.5
    observed_at: str = ""
    corroborated_by: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.observed_at:
            self.observed_at = datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(slots=True)
class ResearchSession:
    query: str
    items: list[ResearchItem] = field(default_factory=list)
    claims: list[ResearchClaim] = field(default_factory=list)
    comparison: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))

    @classmethod
    def from_items(cls, query: str, items: list[ResearchItem], comparison: dict | None = None) -> "ResearchSession":
        claims = []
        for item in items:
            text = (item.relevant_text or item.snippet).strip()
            if text and item.url:
                claims.append(ResearchClaim(text=text[:700], source_url=item.url, confidence=0.55, observed_at=item.observed_at))
        session = cls(query=query, items=items, claims=claims, comparison=comparison or {})
        session.cross_check()
        return session

    def cross_check(self) -> None:
        """Raises confidence only when similar wording appears on another domain."""
        stop = {"para", "com", "uma", "que", "por", "dos", "das", "the", "and", "from"}
        tokens = [set(word.casefold() for word in re.findall(r"\w+", claim.text) if len(word) > 3 and word.casefold() not in stop) for claim in self.claims]
        for index, claim in enumerate(self.claims):
            domain = urlparse(claim.source_url).netloc.casefold()
            for other_index, other in enumerate(self.claims):
                if index == other_index or urlparse(other.source_url).netloc.casefold() == domain:
                    continue
                union = tokens[index] | tokens[other_index]
                similarity = len(tokens[index] & tokens[other_index]) / len(union) if union else 0
                if similarity >= 0.35:
                    claim.corroborated_by.append(other.source_url)
            if claim.corroborated_by:
                claim.confidence = max(claim.confidence, 0.75)

    def payload(self) -> dict:
        return {
            "query": self.query,
            "created_at": self.created_at,
            "items": [asdict(item) for item in self.items],
            "claims": [asdict(claim) for claim in self.claims],
            "comparison": self.comparison,
        }

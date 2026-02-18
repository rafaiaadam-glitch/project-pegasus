"""Type definitions for the dice rotation system."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Literal


# Dice face names (mapped to facets)
DiceFace = Literal["RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE"]

# Facet dimensions
Facet = Literal["how", "what", "when", "where", "who", "why"]


# Face to Facet mapping
FACE_TO_FACET: Dict[DiceFace, Facet] = {
    "RED": "how",      # 🔴 How - Methods, mechanisms, processes
    "ORANGE": "what",  # 🟠 What - Concepts, definitions, entities
    "YELLOW": "when",  # 🟡 When - Temporal context, sequences
    "GREEN": "where",  # 🟢 Where - Spatial, institutional context
    "BLUE": "who",     # 🔵 Who - Actors, agents, stakeholders
    "PURPLE": "why",   # 🟣 Why - Rationale, purpose, causation
}

# Facet to Face mapping (reverse)
FACET_TO_FACE: Dict[Facet, DiceFace] = {v: k for k, v in FACE_TO_FACET.items()}

# Face colors (for UI)
FACE_COLORS: Dict[DiceFace, str] = {
    "RED": "#FF3B30",
    "ORANGE": "#FF9500",
    "YELLOW": "#FFCC00",
    "GREEN": "#34C759",
    "BLUE": "#007AFF",
    "PURPLE": "#AF52DE",
}


@dataclass
class FacetScores:
    """Confidence scores for each facet dimension."""
    how: float = 0.0
    what: float = 0.0
    when: float = 0.0
    where: float = 0.0
    who: float = 0.0
    why: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "how": self.how,
            "what": self.what,
            "when": self.when,
            "where": self.where,
            "who": self.who,
            "why": self.why,
        }

    def as_face_scores(self) -> Dict[DiceFace, float]:
        """Convert to face-indexed scores."""
        return {
            "RED": self.how,
            "ORANGE": self.what,
            "YELLOW": self.when,
            "GREEN": self.where,
            "BLUE": self.who,
            "PURPLE": self.why,
        }

    def get(self, facet: Facet) -> float:
        """Get score for a specific facet."""
        return getattr(self, facet)

    def set(self, facet: Facet, value: float) -> None:
        """Set score for a specific facet."""
        setattr(self, facet, value)


@dataclass
class IterationResult:
    """Result from a single rotation iteration."""
    index: int
    permutation: List[DiceFace]
    primary_facet: Facet
    threads_found: int
    facet_scores: FacetScores
    timestamp: str


@dataclass
class RotationState:
    """Complete state of the dice rotation system."""
    schedule: List[List[DiceFace]]  # Full permutation schedule
    active_index: int  # Current position in schedule
    scores: FacetScores  # Cumulative facet scores
    entropy: float  # Shannon entropy of score distribution
    equilibrium_gap: float  # Gap to equilibrium threshold
    collapsed: bool  # Whether system has collapsed (imbalance detected)
    iteration_history: List[IterationResult] = field(default_factory=list)
    max_iterations: int = 6  # Safety limit

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "schedule": self.schedule,
            "activeIndex": self.active_index,
            "scores": self.scores.as_face_scores(),
            "entropy": self.entropy,
            "equilibriumGap": self.equilibrium_gap,
            "collapsed": self.collapsed,
            "iterationHistory": [
                {
                    "index": r.index,
                    "permutation": r.permutation,
                    "primaryFacet": r.primary_facet,
                    "threadsFound": r.threads_found,
                    "facetScores": r.facet_scores.to_dict(),
                    "timestamp": r.timestamp,
                }
                for r in self.iteration_history
            ],
            "maxIterations": self.max_iterations,
        }

"""Explicit, user-assigned primary application domains for comparison."""
from typing import Literal

PaperDomain = Literal[
    "computing", "medicine", "agriculture", "environment", "civil_engineering",
    "engineering", "natural_sciences", "business", "education", "social_sciences", "humanities",
]

DOMAIN_LABELS = {
    "computing": "Computer science & AI",
    "medicine": "Medicine & healthcare",
    "agriculture": "Agriculture & food science",
    "environment": "Environment & climate",
    "civil_engineering": "Civil engineering & construction",
    "engineering": "Other engineering",
    "natural_sciences": "Natural sciences",
    "business": "Business & economics",
    "education": "Education",
    "social_sciences": "Social sciences",
    "humanities": "Humanities",
}

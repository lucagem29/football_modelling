"""Unified id rules (docs/schema.md): team slugs and match ids."""

import re
import unicodedata

# Suffixes providers use to mark women's sides; the gender goes into the "-w" suffix instead
_WOMEN_SUFFIX = re.compile(r"\s+(women'?s?|wfc|ladies|femenino|féminin|frauen)$", re.IGNORECASE)


def slugify(text: str) -> str:
    """Lowercase ASCII words joined by hyphens: 'Bayer 04 Leverkusen' -> 'bayer-04-leverkusen'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def team_slug(name: str, gender: str = "m") -> str:
    """Unified team_id. Women's sides end in '-w' whatever the provider called them."""
    if gender == "w":
        return slugify(_WOMEN_SUFFIX.sub("", name.strip())) + "-w"
    return slugify(name)


def make_match_id(date: str, home_team_id: str, away_team_id: str) -> str:
    """'<YYYY-MM-DD>_<home team_id>_<away team_id>'."""
    return f"{str(date)[:10]}_{home_team_id}_{away_team_id}"

"""Optional post-processing that turns reconstructed subject names into clean
display names while keeping a subject and its laboratory strictly distinct.

Key correctness rules:

* A subject and its lab are **different** subjects and must both survive.
* Two columns are only treated as a theory/lab pair when their *raw*
  reconstructed text is identical (the PDF truncates the trailing "Lab", so the
  theory and its lab render as the same string, e.g. ``Object Oriented Progra``
  twice). The second such column becomes the ``... Lab``.
* When two *different* raw names happen to match the same canonical (e.g. the
  truncated ``COMPU TER NETWO`` for a ``CN&O`` subject collides with the real
  ``Computer Networks``), we keep the stronger match on the canonical and let
  the weaker one fall back to a title-cased name. We never fabricate a "Lab".

The extraction pipeline stays fully dynamic; this layer only improves display.
"""
from __future__ import annotations

import logging
import re
from collections import OrderedDict

from utils import subject_aliases

logger = logging.getLogger(__name__)

# Match strengths.
_EXACT = 2
_PREFIX = 1
_NONE = 0


def _compress(text: str) -> str:
    """Reduce a name to ``[a-z0-9&]`` for tolerant matching.

    ``&`` is preserved so that ``Computer Networks`` and ``Computer Networks &``
    (a different subject) do not collapse onto the same key.
    """
    return re.sub(r"[^a-z0-9&]", "", text.lower())


class SubjectNormalizer:
    """Maps reconstructed subject names onto clean, distinct display names."""

    _CATALOGUE: list[tuple[str, str]] = [
        (_compress(name), name) for name in subject_aliases.KNOWN_SUBJECTS
    ]

    # ------------------------------------------------------------------
    @classmethod
    def normalize_name(cls, raw: str) -> str:
        """Return a clean display name for a single reconstructed subject."""
        raw = re.sub(r"\s+", " ", raw).strip()
        if not raw:
            return raw
        canon, _strength = cls._match(_compress(raw))
        return canon if canon is not None else cls._smart_title_case(raw)

    @classmethod
    def _match(cls, compressed: str) -> tuple[str | None, int]:
        """Match a compressed reconstruction to a canonical name.

        Returns ``(canonical, strength)`` where strength is exact/prefix/none.
        Truncated columns are treated as a prefix of their canonical form; the
        shortest such canonical (closest in length) wins.
        """
        if not compressed:
            return None, _NONE
        best: tuple[int, str] | None = None
        for canon_compressed, canon_name in cls._CATALOGUE:
            if canon_compressed == compressed:
                return canon_name, _EXACT
            if canon_compressed.startswith(compressed):
                score = len(canon_compressed)
                if best is None or score < best[0]:
                    best = (score, canon_name)
        return (best[1], _PREFIX) if best else (None, _NONE)

    @classmethod
    def _smart_title_case(cls, raw: str) -> str:
        """Title-case a name, preserving acronyms and lower-casing connectors."""
        words = raw.split()
        out: list[str] = []
        for idx, word in enumerate(words):
            upper = word.upper()
            lower = word.lower()
            if not any(c.isalpha() for c in word):
                out.append(word)
            elif upper in subject_aliases.ACRONYMS:
                out.append(upper)
            elif idx > 0 and lower in subject_aliases.LOWERCASE_WORDS:
                out.append(lower)
            else:
                out.append(word[:1].upper() + word[1:].lower())
        return " ".join(out)

    # ------------------------------------------------------------------
    @classmethod
    def normalize_list(cls, raw_subjects: list[str]) -> list[str]:
        """Normalise an ordered subject list, keeping every column distinct.

        Duplicate decisions are made on the *raw* reconstructed text so that a
        genuine theory/lab pair (identical raw text) is preserved while two
        different subjects that merely truncate alike are never merged.
        """
        n = len(raw_subjects)
        raw_keys = [_compress(r) for r in raw_subjects]
        matches = [cls._match(k) for k in raw_keys]  # (canon|None, strength)

        results: list[str | None] = [None] * n

        # Group column indices by the canonical they matched.
        by_canon: "OrderedDict[str, list[int]]" = OrderedDict()
        for i, (canon, _s) in enumerate(matches):
            if canon is not None:
                by_canon.setdefault(canon, []).append(i)

        for canon, idxs in by_canon.items():
            if len(idxs) == 1:
                results[idxs[0]] = canon
                continue

            # Do the colliding columns share the *same* raw text?
            distinct_raw = {raw_keys[i] for i in idxs}
            if len(distinct_raw) == 1:
                # Genuine theory/lab pair: keep them all on the canonical and
                # let ensure_unique turn repeats into "... Lab".
                for i in idxs:
                    results[i] = canon
            else:
                # Different subjects that truncated to the same canonical.
                # Strongest match (exact > prefix, then longest raw) keeps the
                # canonical; the rest fall back to a title-cased name.
                strongest = max(idxs, key=lambda i: (matches[i][1], len(raw_keys[i])))
                for i in idxs:
                    results[i] = canon if i == strongest else cls._smart_title_case(raw_subjects[i])

        for i in range(n):
            if results[i] is None:
                results[i] = cls._smart_title_case(raw_subjects[i])

        return cls.ensure_unique([r for r in results if r is not None])

    @staticmethod
    def ensure_unique(names: list[str]) -> list[str]:
        """Guarantee unique names so no grade is lost to a colliding key.

        A repeated name is treated as the laboratory of the earlier column (the
        observed layout is always *theory* then *lab*); further collisions fall
        back to a numeric suffix.
        """
        seen: set[str] = set()
        result: list[str] = []
        for name in names:
            candidate = name
            if candidate in seen:
                lab = f"{name} Lab" if not name.endswith("Lab") else name
                if lab not in seen:
                    candidate = lab
                else:
                    counter = 2
                    while f"{name} ({counter})" in seen:
                        counter += 1
                    candidate = f"{name} ({counter})"
            seen.add(candidate)
            result.append(candidate)
        return result

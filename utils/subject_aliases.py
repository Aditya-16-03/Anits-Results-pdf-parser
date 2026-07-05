"""Editable catalogue of canonical subject names for optional normalisation.

The PDF prints subject names inside narrow columns, so they arrive either
truncated (``Chemical Process Calculat``) or, on all-caps pages, over-split
(``DATA STRUCT URES``). The reconstruction algorithm stays fully dynamic and
never depends on this list; it is used only as an *optional* post-processing
step that maps a reconstructed name onto a clean display name.

How matching works (see :mod:`services.normalization_service`):
    A reconstructed name is compressed to ``[a-z0-9]`` only and matched against
    the compressed form of each canonical name. Because column text is
    truncated, a compressed reconstruction is treated as a **prefix** of its
    canonical form, e.g. ``chemicalprocesscalculat`` -> ``Chemical Process
    Calculations``.

To support a new branch/semester simply add its clean subject names here; no
code changes are required. Unrecognised subjects are still returned (title
cased), so the service never drops data.
"""
from __future__ import annotations

# Canonical, human-friendly subject names. Order does not matter.
KNOWN_SUBJECTS: list[str] = [
    # --- Common / first-year-ish ---
    "Vector Calculus & Statistical Methods",
    "Vector Calculus and Transforms",
    "Vector Calculus & Partial Differential Equations",
    "Logical Reasoning & Corporate Skills",
    "Logical Reasoning and Corporate Skills",
    "Entrepreneurship Development & IPR",
    "Entrepreneurship and IPR",
    "Entrepreneurship & IPR",
    "Universal Human Values",
    "Constitution of India",
    "Financial Literacy",
    "Design Thinking",
    "Skill Oriented Course",

    # --- Chemical ---
    "Instrumentation and Analytical Techniques",
    "Biology for Engineers",
    "Chemical Process Calculations",
    "Momentum Transfer",
    "Momentum Transfer Lab",
    "Mechanical Operations",
    "Mechanical Operations Lab",

    # --- Civil ---
    "Engineering Mechanics",
    "Strength of Materials",
    "Strength of Materials Lab",
    "Surveying and Geomatics",
    "Water Supply Engineering",

    # --- CSE / IT / AIML / Data Science ---
    "Discrete Mathematical Structures",
    "Data Structures",
    "Data Structures Lab",
    "Data Structures and Algorithms",
    "Data Structures and Algorithms Lab",
    "Advanced Data Structures",
    "Advanced Data Structures Lab",
    "Theory of Computation",
    "Operating Systems",
    "Operating Systems Lab",
    "Computer Networks",
    "Computer Networks Lab",
    "Computer Organisation",
    "Computer Organisation Lab",
    "Object Oriented Programming",
    "Object Oriented Programming Lab",
    "Probability and Statistics",
    "Probability & Statistics",
    "Java Programming Practice",
    "Java Lab",
    "Software Engineering",
    "Network Fundamentals",
    "UI/UX Design Tools",

    # --- EEE ---
    "Electrical Measurements",
    "Electronic Circuit Analysis",
    "Electronic Circuit Laboratory",
    "Network Theory",
    "Performance of DC Machines",
    "Networks & Measurements",
    "Foundations of Data Visualization",

    # --- ECE ---
    "Random Variables & Stochastic Processes",
    "Signals and Systems",
    "Signals and Systems Lab",
    "Control Systems",
    "Analog Electronic Circuits",
    "Analog Electronic Circuits Lab",

    # --- Mechanical ---
    "Fluid Mechanics & Hydraulics",
    "Mechanics of Solids",
    "Mechanics of Solids & Materials",
    "Engineering Thermodynamics",
    "Manufacturing Processes",
    "Manufacturing Processes Lab",
    "Computer Aided Geometric Design",
]

# Words that stay lower-case in the title-case fallback (unless first word).
LOWERCASE_WORDS: set[str] = {"of", "and", "for", "the", "to", "in", "with", "or", "a", "an"}

# Tokens that should keep their upper-case form in the title-case fallback.
ACRONYMS: set[str] = {"IPR", "DC", "AC", "UI", "UX", "IT", "AI", "ML", "IoT", "VLSI"}

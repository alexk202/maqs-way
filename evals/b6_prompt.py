"""B6 fix: verbatim entity preservation, injected as mem0 add(prompt=...).

Mechanism (verified in mem0@0724291b source): Memory.add(prompt=...) flows
to _add_to_vector_store -> custom_instructions -> "## Custom Instructions"
section of the additive extraction user prompt. No canon logic duplicated.
"""
B6_VERBATIM = (
    "ENTITY FIDELITY (highest priority):\n"
    "1. Copy proper names of people, organizations, and places EXACTLY as "
    "written in the input. Never paraphrase, translate, transliterate, or "
    "shorten them.\n"
    "2. Copy titles of works (books, films, plays, shows, songs, products) "
    "EXACTLY as written. Never replace a title with a genre or a description.\n"
    "3. Copy every number EXACTLY as written: dates, times, ages, quantities, "
    "durations, prices, measurements, addresses.\n"
    "4. Verbatim fidelity outranks stylistic smoothness: never sacrifice an "
    "exact name, title, or number to make a sentence read more naturally.\n"
    "5. Do not merge distinct named entities into one generic statement."
)

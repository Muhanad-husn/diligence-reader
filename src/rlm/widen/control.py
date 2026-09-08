"""The identity knob: sample 1's pinned sections written as a markdown data room.

Nothing is renamed, nothing is dropped and nothing is added. The control separates what the
markdown rendition costs from what a knob costs.
"""

from __future__ import annotations

from rlm.widen import Source, Variant, identity

NAME = "control"


def build(source: Source) -> Variant:
    """The variant of one sample with no knob turned."""
    return identity(source, NAME)

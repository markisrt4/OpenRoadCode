"""Geographic presentation and additive selection; no download or process access."""
from dataclasses import dataclass

LAYERS = ('Roads, search & routing', 'Basic terrain', '3D buildings',
          'Detailed terrain', 'High-resolution imagery')
# These are user-facing areas, not promises of finished artifacts or exact boundaries.
AREAS = {
    'us': 'United States',
    'mi': 'Michigan statewide',
    'metro-detroit': 'Metro Detroit',
    'ann-arbor': 'Ann Arbor / Southeast Michigan',
    'mid-michigan': 'Lansing / Mid-Michigan',
    'west-michigan': 'Grand Rapids / West Michigan',
    'northern-michigan': 'Northern Lower Michigan',
    'upper-peninsula': 'Upper Peninsula',
    'detroit-midtown': 'Detroit Downtown–Midtown',
    'auburn-hills': 'Rochester / Auburn Hills',
    'southfield': 'Southfield',
}
MICHIGAN_AREAS = ('mi', 'metro-detroit', 'ann-arbor', 'mid-michigan',
                  'west-michigan', 'northern-michigan', 'upper-peninsula')
METRO_AREAS = ('detroit-midtown', 'auburn-hills', 'southfield')


@dataclass(frozen=True, order=True)
class Selection:
    area: str
    layer: int


def toggle(selected, area, layer):
    if not 0 <= layer < len(LAYERS):
        raise ValueError('Unknown layer')
    key = Selection(area, layer)
    if key in selected:
        selected.remove(key)
    else:
        selected.add(key)


def effective_selection(selected):
    """Deduplicate identical choices without discarding finer or unpublished layers.

    Geographic containment does not imply equal resolution or available coverage.
    Archive identity/checksum reuse remains the existing installers' responsibility.
    """
    return tuple(sorted(set(selected)))

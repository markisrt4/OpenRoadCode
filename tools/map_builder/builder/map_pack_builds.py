"""Translate geographic choices into exact supported build requests, without I/O."""
from dataclasses import dataclass

from .map_pack_selection import effective_selection


@dataclass(frozen=True)
class BuildRequest:
    target: str
    fields: tuple[tuple[str, str], ...] = ()


def plan_builds(selected):
    requests = set()
    unavailable = []
    details = {}
    for item in effective_selection(selected):
        if item.layer == 2 and item.area in ('mi', 'metro-detroit'):
            # Statewide supersedes the same building product in the Metro subset.
            if item.area == 'metro-detroit' and any(
                    value.area == 'mi' and value.layer == 2 for value in selected):
                continue
            requests.add(BuildRequest('michigan-buildings' if item.area == 'mi'
                                      else 'metro-detroit-buildings'))
        elif item.area in ('detroit-midtown', 'auburn-hills') and item.layer in (3, 4):
            coverages = ('rochester', 'auburn-hills') if item.area == 'auburn-hills' else (item.area,)
            for coverage in coverages:
                details.setdefault(coverage, set()).add('terrain' if item.layer == 3 else 'imagery')
        else:
            unavailable.append(item)
    for coverage, layers in details.items():
        requests.add(BuildRequest('selected-detail', (('detail_coverage', coverage),
                          ('detail_layers', 'both' if len(layers) == 2 else next(iter(layers))))))
    return tuple(sorted(requests, key=lambda request: (request.target, request.fields))), tuple(unavailable)


def detail_matrix(target, coverage='', layers=''):
    """Workflow input allowlist; never interpolate unchecked coverage into commands."""
    if target == 'selected-detail':
        if coverage not in ('detroit-midtown', 'auburn-hills', 'rochester'):
            raise ValueError('Unsupported detail coverage')
        if layers not in ('imagery', 'terrain', 'both'):
            raise ValueError('Unsupported detail layers')
        return [coverage], layers, 17
    if target == 'michigan-detail-pilot':
        return ['detroit-midtown', 'auburn-hills', 'rochester'], 'both', 17
    if target == 'imagery-detail-pilot':
        return ['detroit-midtown', 'auburn-hills'], 'imagery', 16
    raise ValueError('Not a detail build')

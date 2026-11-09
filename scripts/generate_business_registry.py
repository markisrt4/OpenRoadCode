# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Reproducible offline NSI subset generator; refresh only with an explicit pin."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

CATALOG = Path(__file__).resolve().parents[1] / 'controllers/poi/catalog'


def generate(snapshot, overrides):
    if snapshot.get('schema_version') != 1 or overrides.get('schema_version') != 1:
        raise ValueError('Unsupported business registry schema')
    revision = snapshot['revision']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('NSI revision must be a full commit SHA')
    businesses = {}
    for entry in snapshot['items']:
        key, item = entry['provider_id'], entry['item']
        if key in businesses or not re.fullmatch(r'[a-z0-9-]+', key):
            raise ValueError('Duplicate or invalid business ID')
        tags = item['tags']
        wikidata = tags['brand:wikidata']
        if not re.fullmatch(r'Q[1-9][0-9]*', wikidata):
            raise ValueError('Invalid Wikidata identifier')
        manual = overrides['businesses'].get(key, {})
        title_style = manual.get('title_style')
        if title_style is not None and (not re.fullmatch(r'#[0-9a-fA-F]{6}', title_style.get('color', ''))
                or not title_style.get('font_families')
                or any(not isinstance(font, str) or not font or len(font) > 80
                       for font in title_style['font_families'])):
            raise ValueError('Invalid business title appearance')
        if any(not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}', domain)
               for domain in manual.get('domains', [])):
            raise ValueError('Domains must be lowercase hostnames, not URLs or wildcard suffixes')
        aliases = {value for value in (tags.get('name'), tags.get('short_name'), *manual.get('aliases', [])) if value}
        businesses[key] = {
            'name': tags['brand'], 'aliases': sorted(aliases), 'wikidata': [wikidata],
            'categories': ['food'], 'domains': manual.get('domains', []),
            'icon_id': manual.get('icon_id'), 'location_set': item['locationSet'],
            'title_style': title_style,
            'source': {'url': f'https://github.com/osmlab/name-suggestion-index/blob/{revision}/{entry["path"]}',
                       'revision': revision, 'nsi_id': item['id'], 'license': snapshot['license']},
        }
    if set(overrides['businesses']) - businesses.keys():
        raise ValueError('An override references a missing business')
    return {'schema_version': 1, 'businesses': dict(sorted(businesses.items()))}


def refresh(snapshot, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Supply a full NSI commit SHA, not a moving branch')
    documents = {}
    updated = json.loads(json.dumps(snapshot))
    for entry in updated['items']:
        path = entry['path']
        if not re.fullmatch(r'data/brands/amenity/[a-z_]+\.json', path):
            raise ValueError('Unexpected NSI source path')
        if path not in documents:
            url = f'https://raw.githubusercontent.com/osmlab/name-suggestion-index/{revision}/{path}'
            with urlopen(url, timeout=30) as response:
                documents[path] = json.loads(response.read(8_000_001))
        identity = entry['item']['tags']['brand:wikidata']
        matches = [item for item in documents[path]['items'] if item['id'] == entry['item']['id']
                   and item.get('tags', {}).get('brand:wikidata') == identity]
        if len(matches) != 1:
            raise ValueError(f'NSI identity changed for {entry["provider_id"]}; review before updating')
        entry['item'] = matches[0]
    updated['revision'] = revision
    return updated


def serialized(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def validate_assets(registry):
    """CI needs only the standard library; never import runtime/UI packages."""
    apps = json.loads((CATALOG / 'android_apps.json').read_text())
    icons = json.loads((CATALOG / 'icons/manifest.json').read_text())
    if apps.get('schema_version') != 1 or icons.get('schema_version') != 1:
        raise ValueError('Unsupported app/icon schema')
    for key, app in apps['apps'].items():
        package = app['package']
        if key not in registry['businesses'] or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)+', package):
            raise ValueError('Unknown business or invalid Android package')
        if app['source'] != 'https://play.google.com/store/apps/details?id=' + package:
            raise ValueError('App source must identify the exact official store listing')
    for key, entry in icons['icons'].items():
        if not re.fullmatch(r'[a-z0-9-]{1,64}', key) or entry['file'] != key + '.png':
            raise ValueError('Invalid icon asset name')
        for filename, digest in ((entry['file'], entry['sha256']), (key + '.svg', entry['source_sha256'])):
            if hashlib.sha256((CATALOG / 'icons' / filename).read_bytes()).hexdigest() != digest:
                raise ValueError('Icon checksum mismatch: ' + filename)
    for brand in registry['businesses'].values():
        if brand.get('icon_id') and brand['icon_id'] not in icons['icons']:
            raise ValueError('Brand references an unapproved icon')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--refresh', metavar='COMMIT_SHA')
    args = parser.parse_args()
    if args.check and args.refresh:
        parser.error('--check is offline; use --refresh separately')
    snapshot = json.loads((CATALOG / 'nsi_snapshot.json').read_text())
    overrides = json.loads((CATALOG / 'overrides.json').read_text())
    if args.refresh:
        snapshot = refresh(snapshot, args.refresh)
    registry = generate(snapshot, overrides)
    validate_assets(registry)
    output = serialized(registry)
    destination = CATALOG / 'brands.json'
    if args.check:
        if destination.read_text() != output:
            raise SystemExit('Business registry differs; run python -m scripts.generate_business_registry')
    else:
        if args.refresh:
            (CATALOG / 'nsi_snapshot.json').write_text(serialized(snapshot))
        destination.write_text(output)


if __name__ == '__main__':
    main()

# Business identities, map logos and Android apps

The first registry resolves **brands**, not individual stores. Physical locations
remain in the offline POI index. Search results and POI cards share one resolved
business ID, so an icon and an Android action refer to the same identity.

## Current coverage

| Brand | Identity | Bundled logo | Android mapping |
| --- | --- | --- | --- |
| Panera Bread | NSI / Q7130852 | Category fallback | com.panera.bread |
| McDonald's | NSI / Q38076 | Yes | com.mcdonalds.app |
| Burger King | NSI / Q177054 | Yes | None yet |
| Starbucks | NSI / Q37158 | Yes | None yet |

Package mappings are the existing curated ORC integrations, not packages inferred
from a brand name. McDonald's mapping is the US app; store availability and
eligibility vary by region/device. Opening an app does **not** select the physical
store. Store-specific deep links need separate verification before being added.

Panera deliberately retains its category marker until an approved icon is added.
Unknown businesses and missing/corrupt assets also retain category markers.
There is no runtime favicon crawler or third-party favicon service in this first
version. That can be added separately after the bundled path is validated.

## Data and matching

All registry files are under `controllers/poi/catalog/`:

- `nsi_snapshot.json`: a small verbatim subset of Name Suggestion Index entries,
  pinned to an upstream commit, with their NSI IDs and geographic metadata.
- `overrides.json`: reviewed website domains, extra aliases and icon references.
- `brands.json`: deterministic generated output, including source provenance.
- `android_apps.json`: curated packages and exact Google Play listing sources.
- `icons/manifest.json`: approved local PNG/SVG assets, hashes, sources and rights
  metadata. Icons are normalized to a 64×64 circular badge; the renderer uses
  their registered IDs, never arbitrary image paths or URLs.
- `businesses/*.toml` and `integrations/web.toml`: existing capabilities, aliases
  and ordering links, retained for compatibility. Android mappings have moved
  from `integrations/android.toml` into the JSON app registry.

The NSI subset includes its BSD-3-Clause license. The initial SVG sources come
from a pinned Simple Icons commit with its CC0 license; trademark rights and
brand usage guidelines still apply. The normalized PNG hashes are separate from
the source SVG hashes. A new icon needs a reviewed source and rights metadata.

Matching prefers brand Wikidata IDs, then exact official website domains
(including subdomains), then exact normalized brand/operator/name aliases.
Category mismatches are rejected; ambiguous matches return no business.
The resolver does not do substring/fuzzy matching or derive package names.
NSI's full geographic rules are retained as provenance but are not interpreted
by this initial four-brand resolver. Additional regional identities must remain
unresolved when ambiguous until geographic matching is implemented.

SQLite POI results already carry brand Wikidata, operator and website when those
columns exist. Older databases still work through exact brand/name matching.
The resolver runs before search markers are presented, not only when a card is
opened. Search logos replace the category circle/glyph at the same zoom levels
as search badges (zoom 7 and above). Logos are not suppressed by label placement.
Only a successfully loaded native image hides the circle/glyph; an unknown or
failed image keeps the category fallback. Ordinary base-map
POIs are not globally replaced, and clearing a search clears its logo markers.
Renderer restarts replay the current search results and their icon payloads.
This rendering integration currently targets the native MapLibre map.

## Open or install an app

For known ordering businesses, the POI card shows one **ORDER** action. It opens
the installed Android app when available, otherwise the configured ordering
website. It does not also show **OPEN / INSTALL APP** and **WEBSITE** as competing
ways to order. A business without an ordering integration still gets its website
action when one is known. Opening an app is not a verified store-specific handoff.

The separate app/store capability remains available to integrations without an
ordering capability; it is not displayed alongside ORDER. Its two outcomes are:

1. Installed app: launch it through the existing Android integration. On
   Waydroid, show it in ORC's Android container.
2. Missing app: open its package-specific Google Play listing inside Waydroid,
   using the same embedded container. The user reviews the listing and installs
   through Android. Return to the POI and press the action again to launch it;
   installed applications are queried afresh for each request.

Waydroid must have a functioning Play Store, Internet access and any required
account/device eligibility. Without the Play Store, ORC reports that requirement;
it does not send the user to a Linux browser as though it were the Android store.
On Termux, the existing Android Bridge performs the app-first handoff and uses
the official HTTPS Play listing if the package is unavailable. Android controls
the resulting foreground app/store/browser experience there.

This action does not download APKs, accept terms, create accounts or install
silently. Production provisioning of a selected app set is a separate concern;
Play licensing, CPU compatibility and region restrictions still apply. The
**ORDER** action retains its app-first/web-fallback behavior.

## Generate and validate offline

```bash
git switch feature/waze-live-map
python3 -m scripts.generate_business_registry --check
```

To regenerate after editing the reviewed overrides, omit `--check`. No network
is used. Validation also checks app IDs/listing URLs and icon asset hashes.

To refresh the existing subset, select and review a full upstream commit SHA:

```bash
git switch feature/waze-live-map
python3 -m scripts.generate_business_registry --refresh <full-40-character-NSI-commit-SHA>
```

The refresh downloads only the configured NSI category files and requires each
selected NSI ID and Wikidata identity to remain intact. An upstream identity
change stops generation for review; failed downloads do not replace the previous
snapshot or generated output. Icons and app mappings are never scraped or
replaced by that operation. No timestamps are added merely to create diffs.

The **Business registry** GitHub Actions workflow validates relevant PRs offline.
Its manual dispatch can take an explicit NSI revision and upload candidate JSON
files for review. It has read-only repository permissions and never commits or
publishes updates automatically. Scheduled update PRs and broader brand coverage
are the next stage after device validation of this small initial catalog.

## Validation and trying it

Focused Python checks:

```bash
git switch feature/waze-live-map
python3 -m pytest -q controllers/poi/unit_test/test_business_registry.py controllers/poi/unit_test/test_poi_search_controller.py apps/launchers/unit_test/test_android_app_launcher.py controllers/map_renderer/unit_test/test_map_request_handler.py
```

The native map renderer must be rebuilt with this commit to display logos.
The updated binary logs `Business POI logo replacement enabled` at startup;
this distinguishes it from a still-installed older renderer.
On an already configured Termux build, close ORC and update only the renderer:

```bash
git switch feature/waze-live-map
git pull --ff-only
bash development/termux/build_navigation_stack.sh --renderer-only
./runOrcUi
```

The normal navigation-stack build/install workflows pick up the new headers;
there are no new runtime library dependencies. The C++ component check is
`apps/map_renderer/component_test/poi_brand_cli.cpp`; it takes a search GeoJSON
fixture with the three approved image payloads, then the map-style path.

On the VM, search food near a covered business. At street zoom, check the logo,
click it and confirm its card still identifies the correct store. Clear/repeat
the search and leave/reopen navigation. For an ordering brand, confirm the card
shows ORDER alone, opens the installed Android app, and falls back to the ordering
website when the app is absent. Validate explicit app/store integrations separately
when adding a brand without an ordering capability.
Actual app installation/store behavior and GPU rendering require device tests;
Python and C++ component tests cannot establish those results.

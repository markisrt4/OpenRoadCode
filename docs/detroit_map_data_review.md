# Detroit map data review

Reviewed 2026-10-08 for an ORC navigation/3D-view experiment. This is a source
and feasibility review, not a downloaded or benchmarked Detroit scene. No paid
service, new build dependency, or Cesium runtime has been introduced.

## Recommended first dataset combination

Use public-domain USGS orthoimagery and 3DEP elevation with open building
footprints. These provide a credible satellite/terrain/3D-building experiment
without using Google Earth imagery. Start with a small downtown Detroit area,
then assess whether a Cesium globe adds enough value over the existing MapLibre
renderer. The aerial imagery is a top-down photograph; buildings would initially
be untextured extrusions, not Google's photogrammetric city mesh.

| Layer | Candidate and coverage evidence | Rights and limits | Preparation |
| --- | --- | --- | --- |
| Aerial imagery | USGS NAIP Plus advertises roughly six-inch to one-meter source imagery. Michigan publishes a 2022 NAIP service; newer 2024 state imagery is also listed. | USGS explicitly offers public-domain downloadable orthoimagery. Check each selected source record and retain credits. Michigan service metadata has an empty license field, which is not permission by itself. | Download a bounded area, inspect its actual acquisition date/resolution, and create imagery tiles. A published state service does not establish every Detroit tile's freshness. |
| Terrain | USGS 3DEP offers DEMs and lidar; USGS shows the Detroit skyline in its 3DEP point cloud. Michigan reports downloadable QL2 lidar collected during 2015–2020. | USGS 3DEP datasets are public domain. Distinguish ground elevation from surface/building returns. | Reproject and tile DEMs. Cesium commonly uses quantized-mesh terrain; MapLibre terrain uses its supported elevation encoding. A raw GeoTIFF is not automatically a ready-to-stream terrain layer. |
| Buildings | Microsoft Global ML Building Footprints includes the United States, with height estimates for some buildings. Existing OSM buildings are another candidate. | Microsoft data is CDLA-Permissive-2.0; include the agreement when sharing data. OSM has ODbL attribution and database obligations. These licenses are separate from restrictions on streaming Bing imagery through Cesium ion. | Clip footprints to Detroit, inspect completeness/height availability, and extrude polygons. Missing heights need an explicitly approximate fallback. Footprints are not detailed roof or facade models. |
| Detailed city geometry | Detroit 3DEP lidar establishes a local source of 3D measurements. | Prefer the public-domain USGS acquisition records. No verified ready-made, textured Detroit city mesh was identified in this review. | Producing roof meshes or classified point-cloud 3D Tiles is a separate processing project, not a free substitute for Google's textured city mesh. |

## Source evidence

- [USGS NAIP Plus service](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer)
  describes resolution ranges and public-domain imagery downloads.
- [Michigan 2022 NAIP metadata](https://imagery.michigan.gov/server/rest/services/Michigan_NAIP_2022/ImageServer/info/iteminfo)
  and [Michigan 2024 imagery metadata](https://imagery.michigan.gov/server/rest/services/Michigan_imagery_2024/ImageServer/info/iteminfo)
  establish published regional services, but do not supply a license statement.
- [Michigan MiSAIL](https://www.michigan.gov/dtmb/services/maps/misail),
  [USGS Michigan 3DEP fact sheet](https://pubs.usgs.gov/publication/fs20243031/full),
  and [Detroit lidar example](https://www.usgs.gov/media/images/lidar-point-cloud-image-detroit-michigan)
  establish regional terrain/lidar availability.
- [USGS 3DEP products](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
  and [3DEP specifications](https://pubs.usgs.gov/tm/11b9/tm11B9.pdf)
  describe the elevation products and public-domain status.
- [Microsoft building data](https://github.com/microsoft/GlobalMLBuildingFootprints),
  [CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/), and
  [OSM copyright/license](https://www.openstreetmap.org/copyright)
  provide the building-data options and obligations.

## Why this could improve ORC

MapLibre can already render imagery, terrain, and extruded buildings. Adding
licensed data there preserves the navigation controls, route overlays, radar,
and offline infrastructure. Check the installed renderer's exact supported
formats rather than assuming MapLibre GL JS examples apply unchanged to the
native renderer.

CesiumJS becomes attractive when a continuous globe, long-distance flyovers,
3D Tiles, and large lidar/building scenes are actual requirements. Its engine is
Apache-2.0, but data preparation, storage, hosting, attribution, and device GPU
limits still apply. ORC's routing service would remain responsible for routing.

Avoid substituting Cesium ion's Bing imagery without examining the restrictions:
its content guide prohibits routing and asset tracking with those assets. Google
assets also retain provider-specific restrictions. MapTiler or other commercial
imagery could reduce processing effort, but navigation, caching, redistribution,
pricing, and the exact contracted product would need separate qualification.
No commercial imagery provider is approved by this review.

## Next experiment to agree on

A bounded downtown Detroit imagery tile set and low-detail 3DEP terrain in the
existing MapLibre viewer is the smallest useful data-quality test. Add a small
footprint layer after that, then compare a standalone Cesium scene using the same
data if globe/3D Tiles behavior is still wanted. Measure loading time, memory,
frame rate, and storage before expanding coverage. Dataset acquisition/conversion
and build-workflow changes require a separately agreed implementation scope.

The direct USGS feature query was blocked by the development environment's
network policy. This review therefore does not claim a verified acquisition year,
resolution, download size, or height coverage for the exact downtown test tile.

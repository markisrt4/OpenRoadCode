"""Actual raster pixels, not only mocked browser path calls."""

from PIL import Image, ImageColor

from development.maps.build_reference_globe import LAND, WATER, build, paint


def test_reference_has_us_land_and_real_lakes(tmp_path):
    output = tmp_path / "world.png"
    build(output)
    image = Image.open(output)
    for longitude, latitude in [(-105, 39), (-98, 38), (-110, 47), (-100, 20), (-60, -10)]:
        assert image.getpixel(
            (int((longitude + 180) * 2048 / 360), int((90 - latitude) * 1024 / 180))
        ) == ImageColor.getrgb(LAND)
    for longitude, latitude in [(-140, 0), (-87, 44)]:
        assert image.getpixel(
            (int((longitude + 180) * 2048 / 360), int((90 - latitude) * 1024 / 180))
        ) == ImageColor.getrgb(WATER)
    assert image.mode == "RGB"  # An opaque base under transparent regional tiles.


def test_polygon_hole_does_not_erase_other_multipolygon_members():
    image = Image.new("RGB", (360, 180), WATER)
    outer = [[-20, -20], [20, -20], [20, 20], [-20, 20], [-20, -20]]
    hole = [[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]
    island = [[-5, -5], [5, -5], [5, 5], [-5, 5], [-5, -5]]
    paint(
        image,
        {
            "features": [
                {"geometry": {"type": "MultiPolygon", "coordinates": [[outer, hole], [island]]}}
            ]
        },
        LAND,
    )
    assert image.getpixel((180, 90)) == ImageColor.getrgb(LAND)
    assert image.getpixel((188, 90)) == ImageColor.getrgb(WATER)

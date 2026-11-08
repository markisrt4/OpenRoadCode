// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/poi_brand_payload.hpp"
#include "../src/poi_brand_style.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>

int main(int argc, char** argv) {
    assert(argc == 3);
    std::ifstream input(argv[1]);
    std::string geojson{std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
    auto images = poiBrandImages(geojson);
    assert(images.size() == 3);
    for (const auto& [id, data] : images) {
        assert(id.rfind("business:", 0) == 0);
        assert(data.size() > 24 && data.size() < 65536);
    }
    assert(!poiPngBytes("not-an-image"));
    assert(!poiPngBytes(std::string(90001, 'A')));
    assert(poiBrandImages("{}").empty());
    assert(poiBrandImages(R"({"features":[{"properties":{"brand_icon":"file:/etc/passwd","brand_icon_png":"AA=="}}]})").empty());
    std::ifstream styleInput(argv[2]);
    std::string style{std::istreambuf_iterator<char>{styleInput}, std::istreambuf_iterator<char>{}};
    const auto transformed = withPoiBrandStyle(style);
    assert(withPoiBrandStyle(transformed) == transformed);
    rapidjson::Document parsed;
    parsed.Parse(transformed.c_str());
    bool found = false;
    for (const auto& layer : parsed["layers"].GetArray()) {
        if (std::string(layer["id"].GetString()) != "poi-results-brand") continue;
        found = true;
        assert(std::string(layer["source"].GetString()) == "poi-results");
        assert(layer["minzoom"].GetInt() == 13);
        assert(!layer["layout"]["icon-allow-overlap"].GetBool());
    }
    assert(found);
    assert(withPoiBrandStyle("{\"sources\":{},\"layers\":[]}") == "{\"sources\":{},\"layers\":[]}");
    std::cout << "POI brand payload/style checks passed\n";
}

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
    const auto readyData = withPoiBrandAvailability(geojson, [](const std::string& id) {
        return id == "business:mcdonalds";
    });
    rapidjson::Document ready;
    ready.Parse(readyData.c_str());
    for (const auto& feature : ready["features"].GetArray()) {
        const auto& properties = feature["properties"];
        assert(properties["brand_icon_ready"].GetBool() ==
               (std::string(properties["brand_icon"].GetString()) == "business:mcdonalds"));
    }
    const auto fallbackData = withPoiBrandAvailability(
        R"({"features":[{"properties":{"brand_icon":"business:missing","brand_icon_ready":true}}]})",
        [](const std::string&) { return false; });
    ready.Parse(fallbackData.c_str());
    assert(!ready["features"][0]["properties"]["brand_icon_ready"].GetBool());
    std::ifstream styleInput(argv[2]);
    std::string style{std::istreambuf_iterator<char>{styleInput}, std::istreambuf_iterator<char>{}};
    const auto transformed = withPoiBrandStyle(style);
    assert(withPoiBrandStyle(transformed) == transformed);
    rapidjson::Document parsed;
    parsed.Parse(transformed.c_str());
    bool found = false;
    int fallbacks = 0;
    for (const auto& layer : parsed["layers"].GetArray()) {
        const std::string id = layer["id"].GetString();
        if (id == "poi-results-badge" || id == "poi-results-glow" || id == "poi-results-icon") {
            assert(std::string(layer["filter"][0].GetString()) == "!=");
            assert(std::string(layer["filter"][1][1].GetString()) == "brand_icon_ready");
            assert(layer["filter"][2].GetBool());
            ++fallbacks;
        }
        if (id != "poi-results-brand") continue;
        found = true;
        assert(std::string(layer["source"].GetString()) == "poi-results");
        assert(layer["minzoom"].GetInt() == 7);
        assert(layer["layout"]["icon-allow-overlap"].GetBool());
    }
    assert(found);
    assert(fallbacks == 3);
    assert(withPoiBrandStyle("{\"sources\":{},\"layers\":[]}") == "{\"sources\":{},\"layers\":[]}");
    std::cout << "POI brand payload/style checks passed\n";
}

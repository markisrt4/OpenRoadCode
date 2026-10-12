// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "../src/vehicle_style.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>

int main(int argc, char** argv) {
    assert(argc == 2);
    std::ifstream input(argv[1]);
    assert(input);
    const std::string original{std::istreambuf_iterator<char>{input}, std::istreambuf_iterator<char>{}};
    const auto upgraded = withVehicleStyle(original);
    assert(withVehicleStyle(upgraded) == upgraded);
    rapidjson::Document document;
    document.Parse(upgraded.c_str());
    assert(document["sources"].HasMember("vehicle"));
    bool chevron = false, unknown = false, blueDot = false, rings = false;
    for (const auto& layer : document["layers"].GetArray()) {
        const std::string id = layer["id"].GetString();
        assert(id != "vehicle-heading" && id != "vehicle-veloster");
        if (id == "vehicle-orc-chevron") {
            chevron = true;
            const auto& layout = layer["layout"];
            assert(std::string(layout["icon-rotation-alignment"].GetString()) == "map");
            assert(std::string(layout["icon-pitch-alignment"].GetString()) == "viewport");
            assert(std::string(layout["icon-rotate"][1].GetString()) == "heading");
            assert(layout["icon-allow-overlap"].GetBool());
        }
        unknown |= id == "vehicle-position-unknown";
        blueDot |= id == "vehicle-blue-dot";
        rings |= id == "radar-position-ring-inner";
    }
    assert(chevron && unknown && blueDot && rings);
    // Already installed styles need no dataset rebuild; legacy layers are removed.
    const auto legacy = withVehicleStyle(R"({"sources":{},"layers":[
        {"id":"vehicle-veloster","type":"circle","source":"vehicle"},
        {"id":"vehicle-heading","type":"circle","source":"vehicle"}]})");
    rapidjson::Document legacyDocument;
    legacyDocument.Parse(legacy.c_str());
    assert(legacyDocument["layers"].Size() == 2);
    assert(legacyDocument["sources"].HasMember("vehicle"));
    bool rejected = false;
    try { withVehicleStyle("{}"); } catch (const std::runtime_error&) { rejected = true; }
    assert(rejected);
    std::cout << "Vehicle style upgrade checks passed\n";
}

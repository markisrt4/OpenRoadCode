-- SPDX-FileCopyrightText: 2026 Mark G. Russell
-- SPDX-License-Identifier: MIT

-- Adapt TIGER/Line Primary Roads fields to the OpenMapTiles-compatible
-- attributes consumed by the existing OpenRoadCode MapLibre style.
node_keys = {}
way_keys = {}

function node_function() end
function way_function() end

function attribute_function(attributes, layer)
  local fullname = attributes["FULLNAME"] or ""
  local result = {
    class = "motorway",
    subclass = "motorway",
    brunnel = "",
    ramp = 0,
    one_way = 0,
    surface = "",
    level = 0,
    layer = 0,
    indoor = 0,
    mtfcc = attributes["MTFCC"] or "",
    route_type = attributes["RTTYP"] or ""
  }
  if fullname ~= "" then
    result["name"] = fullname
    result["name:latin"] = fullname
    result["ref"] = fullname
  end
  if layer == "transportation_name" then result["_minzoom"] = 7 end
  return result
end

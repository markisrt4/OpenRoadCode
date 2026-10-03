// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#pragma once

#include <spdlog/spdlog.h>
#include <spdlog/sinks/stdout_sinks.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <chrono>
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <ctime>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <unistd.h>

namespace orc {
inline std::string normalized(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    return value.substr(first, value.find_last_not_of(" \t\r\n") - first + 1);
}
inline spdlog::level::level_enum level(const std::string& input) {
    std::string name = normalized(input);
    std::transform(name.begin(), name.end(), name.begin(), [](unsigned char c) { return std::toupper(c); });
    if (name == "DEBUG") return spdlog::level::debug;
    if (name == "WARNING") return spdlog::level::warn;
    if (name == "ERROR") return spdlog::level::err;
    if (name == "CRITICAL") return spdlog::level::critical;
    return spdlog::level::info;
}
inline spdlog::level::level_enum threshold(const std::string& component) {
    const char* global = std::getenv("ORC_LOG_LEVEL");
    auto selected = level(global ? global : "INFO");
    const char* overrides = std::getenv("ORC_LOG_COMPONENT_LEVELS");
    std::istringstream entries(overrides ? overrides : "");
    std::string entry;
    std::size_t longest = 0;
    while (std::getline(entries, entry, ',')) {
        const auto equals = entry.find('=');
        if (equals == std::string::npos) continue;
        auto prefix = normalized(entry.substr(0, equals));
        if ((component == prefix || component.rfind(prefix + ".", 0) == 0) && prefix.size() >= longest) {
            selected = level(entry.substr(equals + 1));
            longest = prefix.size();
        }
    }
    return selected;
}
inline void log(const char* severity, const char* component, const char* event,
                const std::string& message, const std::string& operationId = "",
                const std::string& command = "", const std::string& endpoint = "") {
    const auto severityLevel = level(severity);
    if (severityLevel < threshold(component)) return;
    static auto logger = [] {
        auto result = std::make_shared<spdlog::logger>("orc", std::make_shared<spdlog::sinks::stderr_sink_mt>());
        result->set_pattern("%v");
        result->set_level(spdlog::level::debug);
        result->flush_on(spdlog::level::debug);
        return result;
    }();
    const auto now = std::chrono::system_clock::now();
    const auto seconds = std::chrono::system_clock::to_time_t(now);
    std::tm utc{};
    gmtime_r(&seconds, &utc);
    const auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count() % 1000;
    std::ostringstream timestamp;
    timestamp << std::put_time(&utc, "%Y-%m-%dT%H:%M:%S") << '.' << std::setfill('0') << std::setw(3) << millis << 'Z';
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
    writer.StartObject();
    auto field = [&](const char* key, const std::string& value) {
        writer.Key(key); writer.String(value.c_str(), static_cast<rapidjson::SizeType>(value.size()));
    };
    field("timestamp", timestamp.str());
    field("level", severity);
    field("component", component);
    field("event", event);
    field("message", message);
    writer.Key("pid"); writer.Int(static_cast<int>(getpid()));
    if (!operationId.empty()) field("operation_id", operationId);
    if (!command.empty()) field("command", command);
    if (!endpoint.empty()) field("endpoint", endpoint);
    writer.EndObject();
    logger->log(severityLevel, "{}", buffer.GetString());
}
} // namespace orc

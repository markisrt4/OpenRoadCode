#include <core.h>
#include <gui/gui.h>
#include <module.h>
#include <utils/flog.h>
#include <utils/networking.h>

#include <algorithm>
#include <cctype>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

#define MAX_COMMAND_LENGTH 1024

SDRPP_MOD_INFO{
    "remote_control",
    "Remote application control and telemetry server for SDR++",
    "OpenRoadCode contributors",
    0, 4, 0,
    1
};

namespace {
std::string trim(std::string value) {
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.back()))) value.pop_back();
    return value;
}
std::string join(const std::vector<std::string>& values, const char* separator) {
    std::ostringstream stream;
    for (std::size_t i = 0; i < values.size(); ++i) { if (i) stream << separator; stream << values[i]; }
    return stream.str();
}
std::string number(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(3) << value;
    return stream.str();
}
const char* onOff(bool value) { return value ? "on" : "off"; }
}

class RemoteControlModule : public ModuleManager::Instance {
public:
    explicit RemoteControlModule(std::string name) : name(std::move(name)) { startServer(); }
    ~RemoteControlModule() override { if (client) client->close(); if (listener) listener->close(); }
    void postInit() override {}
    void enable() override { enabled = true; }
    void disable() override { enabled = false; }
    bool isEnabled() override { return enabled; }

private:
    void startServer() {
        try { listener = net::listen("127.0.0.1", 4533); listener->acceptAsync(clientHandler, this); flog::info("Remote Control listening on 127.0.0.1:4533"); }
        catch (const std::exception& e) { flog::error("Could not start Remote Control server: {}", e.what()); }
    }
    static void clientHandler(net::Conn client, void* ctx) {
        auto* self = static_cast<RemoteControlModule*>(ctx); self->client = std::move(client);
        self->client->readAsync(sizeof(self->dataBuf), self->dataBuf, dataHandler, self, false);
        self->client->waitForEnd(); self->client->close();
        if (self->listener) self->listener->acceptAsync(clientHandler, self);
    }
    static void dataHandler(int count, uint8_t* data, void* ctx) {
        auto* self = static_cast<RemoteControlModule*>(ctx);
        for (int i = 0; i < count; ++i) {
            if (data[i] == '\n') { self->commandHandler(trim(self->command)); self->command.clear(); continue; }
            if (data[i] != '\r' && self->command.size() < MAX_COMMAND_LENGTH) self->command += static_cast<char>(data[i]);
        }
        if (self->client && self->client->isOpen()) self->client->readAsync(sizeof(self->dataBuf), self->dataBuf, dataHandler, self, false);
    }
    void writeResponse(const std::string& response) {
        if (client && client->isOpen()) client->write(response.size(), reinterpret_cast<uint8_t*>(const_cast<char*>(response.c_str())));
    }
    bool configBool(const char* key) {
        core::configManager.acquire(); bool value = core::configManager.conf[key]; core::configManager.release(); return value;
    }
    void saveBool(const char* key, bool value) {
        core::configManager.acquire(); core::configManager.conf[key] = value; core::configManager.release(true);
    }
    void setWaterfall(bool value) { value ? gui::waterfall.showWaterfall() : gui::waterfall.hideWaterfall(); saveBool("showWaterfall", value); }
    void setBandplan(bool value) { value ? gui::waterfall.showBandplan() : gui::waterfall.hideBandplan(); saveBool("bandPlanEnabled", value); }
    void setFFTHold(bool value) { gui::waterfall.setFFTHold(value); saveBool("fftHold", value); }

    bool handleToggleProperty(const std::string& command, const std::string& property, const char* configKey, void (RemoteControlModule::*setter)(bool)) {
        if (command == "GET " + property) { writeResponse("VALUE " + property + " " + onOff(configBool(configKey)) + "\n"); return true; }
        if (command == "TOGGLE " + property) {
            if (!enabled) { writeResponse("ERROR disabled\n"); return true; }
            bool value = !configBool(configKey); (this->*setter)(value); writeResponse("VALUE " + property + " " + onOff(value) + "\n"); return true;
        }
        const std::string prefix = "SET " + property + " ";
        if (command.rfind(prefix, 0) == 0) {
            if (!enabled) { writeResponse("ERROR disabled\n"); return true; }
            const std::string requested = trim(command.substr(prefix.size()));
            if (requested == "on") (this->*setter)(true);
            else if (requested == "off") (this->*setter)(false);
            else { writeResponse("ERROR invalid-value\n"); return true; }
            writeResponse("OK\n"); return true;
        }
        return false;
    }

    void commandHandler(const std::string& command) {
        if (command.empty()) return;
        if (command == "PING") { writeResponse("OK\n"); return; }
        if (handleToggleProperty(command, "waterfall", "showWaterfall", &RemoteControlModule::setWaterfall)) return;
        if (handleToggleProperty(command, "bandplan", "bandPlanEnabled", &RemoteControlModule::setBandplan)) return;
        if (handleToggleProperty(command, "fft_hold", "fftHold", &RemoteControlModule::setFFTHold)) return;
        if (command == "ACTION auto_range") {
            if (!enabled) { writeResponse("ERROR disabled\n"); return; }
            gui::waterfall.autoRange(); writeResponse("OK\n"); return;
        }
        if (command == "GET snr") { writeResponse("VALUE snr " + number(gui::waterfall.selectedVFOSNR) + "\n"); return; }
        if (command == "GET center_frequency") { writeResponse("VALUE center_frequency " + number(gui::waterfall.getCenterFrequency()) + "\n"); return; }
        if (command == "GET bandwidth") { writeResponse("VALUE bandwidth " + number(gui::waterfall.getBandwidth()) + "\n"); return; }
        if (command == "GET view_bandwidth") { writeResponse("VALUE view_bandwidth " + number(gui::waterfall.getViewBandwidth()) + "\n"); return; }
        if (command == "GET fft_min") { writeResponse("VALUE fft_min " + number(gui::waterfall.getFFTMin()) + "\n"); return; }
        if (command == "GET fft_max") { writeResponse("VALUE fft_max " + number(gui::waterfall.getFFTMax()) + "\n"); return; }
        if (command == "GET waterfall_min") { writeResponse("VALUE waterfall_min " + number(gui::waterfall.getWaterfallMin()) + "\n"); return; }
        if (command == "GET waterfall_max") { writeResponse("VALUE waterfall_max " + number(gui::waterfall.getWaterfallMax()) + "\n"); return; }
        if (command == "GET selected_vfo") { writeResponse("VALUE selected_vfo " + (gui::waterfall.selectedVFO.empty() ? std::string("none") : gui::waterfall.selectedVFO) + "\n"); return; }
        if (command == "GET telemetry") {
            writeResponse(
                "TELEMETRY snr=" + number(gui::waterfall.selectedVFOSNR) +
                " center_frequency=" + number(gui::waterfall.getCenterFrequency()) +
                " bandwidth=" + number(gui::waterfall.getBandwidth()) +
                " view_bandwidth=" + number(gui::waterfall.getViewBandwidth()) +
                " fft_min=" + number(gui::waterfall.getFFTMin()) +
                " fft_max=" + number(gui::waterfall.getFFTMax()) +
                " waterfall_min=" + number(gui::waterfall.getWaterfallMin()) +
                " waterfall_max=" + number(gui::waterfall.getWaterfallMax()) +
                " selected_vfo=" + (gui::waterfall.selectedVFO.empty() ? std::string("none") : gui::waterfall.selectedVFO) + "\n"
            );
            return;
        }
        if (command == "GET theme") {
            core::configManager.acquire(); std::string theme = core::configManager.conf["theme"]; core::configManager.release();
            writeResponse("VALUE theme " + theme + "\n"); return;
        }
        if (command == "GET themes") { writeResponse("VALUES themes " + join(gui::themeManager.getThemeNames(), "|") + "\n"); return; }
        constexpr const char* themePrefix = "SET theme ";
        if (command.rfind(themePrefix, 0) == 0) {
            if (!enabled) { writeResponse("ERROR disabled\n"); return; }
            const std::string requested = trim(command.substr(std::char_traits<char>::length(themePrefix)));
            const auto themeNames = gui::themeManager.getThemeNames();
            if (std::find(themeNames.begin(), themeNames.end(), requested) == themeNames.end()) { writeResponse("ERROR invalid-value\n"); return; }
            if (!gui::themeManager.applyTheme(requested)) { writeResponse("ERROR apply-failed\n"); return; }
            core::configManager.acquire(); core::configManager.conf["theme"] = requested; core::configManager.release(true);
            flog::info("Remote Control applied theme '{}'", requested); writeResponse("OK\n"); return;
        }
        writeResponse("ERROR unknown-command\n");
    }

    std::string name;
    bool enabled = true;
    uint8_t dataBuf[1024]{};
    net::Listener listener;
    net::Conn client;
    std::string command;
};

MOD_EXPORT void _INIT_() {}
MOD_EXPORT ModuleManager::Instance* _CREATE_INSTANCE_(std::string name) { return new RemoteControlModule(std::move(name)); }
MOD_EXPORT void _DELETE_INSTANCE_(void* instance) { delete static_cast<RemoteControlModule*>(instance); }
MOD_EXPORT void _END_() {}

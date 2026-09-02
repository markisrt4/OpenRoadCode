#include <core.h>
#include <gui/gui.h>
#include <module.h>
#include <utils/flog.h>
#include <utils/networking.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <string>

#define MAX_COMMAND_LENGTH 1024

SDRPP_MOD_INFO{
    "telemetry",
    "Read-only runtime telemetry server for SDR++",
    "OpenRoadCode contributors",
    0, 1, 0,
    1
};

namespace {
std::string trim(std::string value) {
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.front()))) value.erase(value.begin());
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.back()))) value.pop_back();
    return value;
}

std::string number(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(3) << value;
    return stream.str();
}

std::string selectedVFO() {
    return gui::waterfall.selectedVFO.empty() ? "none" : gui::waterfall.selectedVFO;
}

struct SignalMetrics {
    double peakDb = NAN;
    double noiseFloorDb = NAN;
};

SignalMetrics measureSelectedVFO() {
    SignalMetrics metrics;
    const auto selected = gui::waterfall.selectedVFO;
    const auto vfoIt = gui::waterfall.vfos.find(selected);
    if (selected.empty() || vfoIt == gui::waterfall.vfos.end() || vfoIt->second == nullptr) return metrics;

    float* fft = nullptr;
    int width = 0;
    gui::waterfall.acquireLatestFFT(fft, width);
    if (fft == nullptr || width <= 0) {
        gui::waterfall.releaseLatestFFT();
        return metrics;
    }

    const double viewBandwidth = gui::waterfall.getViewBandwidth();
    if (viewBandwidth <= 0.0) {
        gui::waterfall.releaseLatestFFT();
        return metrics;
    }

    const double viewLower = gui::waterfall.getViewOffset() - (viewBandwidth / 2.0);
    const double lower = vfoIt->second->lowerOffset;
    const double upper = vfoIt->second->upperOffset;
    int first = static_cast<int>(std::floor(((lower - viewLower) / viewBandwidth) * width));
    int last = static_cast<int>(std::ceil(((upper - viewLower) / viewBandwidth) * width));
    first = std::max(0, std::min(width - 1, first));
    last = std::max(first + 1, std::min(width, last));

    double peak = -INFINITY;
    double sum = 0.0;
    int samples = 0;
    for (int i = first; i < last; ++i) {
        const double value = fft[i];
        if (!std::isfinite(value)) continue;
        peak = std::max(peak, value);
        sum += value;
        ++samples;
    }
    gui::waterfall.releaseLatestFFT();

    if (samples > 0) {
        metrics.peakDb = peak;
        metrics.noiseFloorDb = sum / samples;
    }
    return metrics;
}

std::string metric(double value) {
    return std::isfinite(value) ? number(value) : "nan";
}
}

class TelemetryModule : public ModuleManager::Instance {
public:
    explicit TelemetryModule(std::string name) : name(std::move(name)) { startServer(); }
    ~TelemetryModule() override { if (client) client->close(); if (listener) listener->close(); }
    void postInit() override {}
    void enable() override { enabled = true; }
    void disable() override { enabled = false; }
    bool isEnabled() override { return enabled; }

private:
    void startServer() {
        try {
            listener = net::listen("127.0.0.1", 4534);
            listener->acceptAsync(clientHandler, this);
            flog::info("Telemetry listening on 127.0.0.1:4534");
        }
        catch (const std::exception& e) {
            flog::error("Could not start Telemetry server: {}", e.what());
        }
    }

    static void clientHandler(net::Conn client, void* ctx) {
        auto* self = static_cast<TelemetryModule*>(ctx);
        self->client = std::move(client);
        self->client->readAsync(sizeof(self->dataBuf), self->dataBuf, dataHandler, self, false);
        self->client->waitForEnd();
        self->client->close();
        if (self->listener) self->listener->acceptAsync(clientHandler, self);
    }

    static void dataHandler(int count, uint8_t* data, void* ctx) {
        auto* self = static_cast<TelemetryModule*>(ctx);
        for (int i = 0; i < count; ++i) {
            if (data[i] == '\n') {
                self->commandHandler(trim(self->command));
                self->command.clear();
                continue;
            }
            if (data[i] != '\r' && self->command.size() < MAX_COMMAND_LENGTH) {
                self->command += static_cast<char>(data[i]);
            }
        }
        if (self->client && self->client->isOpen()) {
            self->client->readAsync(sizeof(self->dataBuf), self->dataBuf, dataHandler, self, false);
        }
    }

    void writeResponse(const std::string& response) {
        if (client && client->isOpen()) {
            client->write(response.size(), reinterpret_cast<uint8_t*>(const_cast<char*>(response.c_str())));
        }
    }

    void commandHandler(const std::string& command) {
        if (command.empty()) return;
        if (!enabled) { writeResponse("ERROR disabled\n"); return; }
        if (command == "PING") { writeResponse("OK\n"); return; }
        if (command == "GET snr") { writeResponse("VALUE snr " + number(gui::waterfall.selectedVFOSNR) + "\n"); return; }
        if (command == "GET selected_vfo") { writeResponse("VALUE selected_vfo " + selectedVFO() + "\n"); return; }
        if (command == "GET center_frequency") { writeResponse("VALUE center_frequency " + number(gui::waterfall.getCenterFrequency()) + "\n"); return; }
        if (command == "GET bandwidth") { writeResponse("VALUE bandwidth " + number(gui::waterfall.getBandwidth()) + "\n"); return; }
        if (command == "GET view_bandwidth") { writeResponse("VALUE view_bandwidth " + number(gui::waterfall.getViewBandwidth()) + "\n"); return; }
        if (command == "GET signal_peak" || command == "GET noise_floor") {
            const auto metrics = measureSelectedVFO();
            if (command == "GET signal_peak") writeResponse("VALUE signal_peak " + metric(metrics.peakDb) + "\n");
            else writeResponse("VALUE noise_floor " + metric(metrics.noiseFloorDb) + "\n");
            return;
        }
        if (command == "GET telemetry") {
            const auto metrics = measureSelectedVFO();
            writeResponse(
                "TELEMETRY snr=" + number(gui::waterfall.selectedVFOSNR) +
                " signal_peak=" + metric(metrics.peakDb) +
                " noise_floor=" + metric(metrics.noiseFloorDb) +
                " center_frequency=" + number(gui::waterfall.getCenterFrequency()) +
                " bandwidth=" + number(gui::waterfall.getBandwidth()) +
                " view_bandwidth=" + number(gui::waterfall.getViewBandwidth()) +
                " fft_min=" + number(gui::waterfall.getFFTMin()) +
                " fft_max=" + number(gui::waterfall.getFFTMax()) +
                " waterfall_min=" + number(gui::waterfall.getWaterfallMin()) +
                " waterfall_max=" + number(gui::waterfall.getWaterfallMax()) +
                " selected_vfo=" + selectedVFO() + "\n"
            );
            return;
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
MOD_EXPORT ModuleManager::Instance* _CREATE_INSTANCE_(std::string name) { return new TelemetryModule(std::move(name)); }
MOD_EXPORT void _DELETE_INSTANCE_(void* instance) { delete static_cast<TelemetryModule*>(instance); }
MOD_EXPORT void _END_() {}

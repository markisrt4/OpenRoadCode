#include <core.h>
#include <gui/gui.h>
#include <module.h>
#include <utils/flog.h>
#include <utils/networking.h>

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string>
#include <vector>

#define MAX_COMMAND_LENGTH 1024

SDRPP_MOD_INFO{
    /* Name:            */ "remote_control",
    /* Description:     */ "Remote application control server for SDR++",
    /* Author:          */ "OpenRoadCode contributors",
    /* Version:         */ 0, 1, 1,
    /* Max instances    */ 1
};

namespace {
std::string trim(std::string value) {
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.front()))) {
        value.erase(value.begin());
    }
    while (!value.empty() && std::isspace(static_cast<unsigned char>(value.back()))) {
        value.pop_back();
    }
    return value;
}

std::string join(const std::vector<std::string>& values, const char* separator) {
    std::ostringstream stream;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) { stream << separator; }
        stream << values[i];
    }
    return stream.str();
}
}

class RemoteControlModule : public ModuleManager::Instance {
public:
    explicit RemoteControlModule(std::string name) : name(std::move(name)) {
        startServer();
    }

    ~RemoteControlModule() override {
        if (client) { client->close(); }
        if (listener) { listener->close(); }
    }

    void postInit() override {}
    void enable() override { enabled = true; }
    void disable() override { enabled = false; }
    bool isEnabled() override { return enabled; }

private:
    void startServer() {
        try {
            listener = net::listen("127.0.0.1", 4533);
            listener->acceptAsync(clientHandler, this);
            flog::info("Remote Control listening on 127.0.0.1:4533");
        }
        catch (const std::exception& e) {
            flog::error("Could not start Remote Control server: {}", e.what());
        }
    }

    static void clientHandler(net::Conn client, void* ctx) {
        auto* self = static_cast<RemoteControlModule*>(ctx);
        self->client = std::move(client);
        self->client->readAsync(sizeof(self->dataBuf), self->dataBuf, dataHandler, self, false);
        self->client->waitForEnd();
        self->client->close();
        if (self->listener) { self->listener->acceptAsync(clientHandler, self); }
    }

    static void dataHandler(int count, uint8_t* data, void* ctx) {
        auto* self = static_cast<RemoteControlModule*>(ctx);
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
        if (command.empty()) { return; }

        if (command == "PING") {
            writeResponse("OK\n");
            return;
        }

        if (command == "GET theme") {
            core::configManager.acquire();
            std::string theme = core::configManager.conf["theme"];
            core::configManager.release();
            writeResponse("VALUE theme " + theme + "\n");
            return;
        }

        if (command == "GET themes") {
            writeResponse("VALUES themes " + join(gui::themeManager.getThemeNames(), "|") + "\n");
            return;
        }

        constexpr const char* prefix = "SET theme ";
        if (command.rfind(prefix, 0) == 0) {
            if (!enabled) {
                writeResponse("ERROR disabled\n");
                return;
            }

            const std::string requested = trim(command.substr(std::char_traits<char>::length(prefix)));
            const auto themeNames = gui::themeManager.getThemeNames();
            if (std::find(themeNames.begin(), themeNames.end(), requested) == themeNames.end()) {
                writeResponse("ERROR invalid-value\n");
                return;
            }

            if (!gui::themeManager.applyTheme(requested)) {
                flog::error("Remote Control could not apply theme '{}'", requested);
                writeResponse("ERROR apply-failed\n");
                return;
            }

            core::configManager.acquire();
            core::configManager.conf["theme"] = requested;
            core::configManager.release(true);

            flog::info("Remote Control applied theme '{}'", requested);
            writeResponse("OK\n");
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

MOD_EXPORT ModuleManager::Instance* _CREATE_INSTANCE_(std::string name) {
    return new RemoteControlModule(std::move(name));
}

MOD_EXPORT void _DELETE_INSTANCE_(void* instance) {
    delete static_cast<RemoteControlModule*>(instance);
}

MOD_EXPORT void _END_() {}

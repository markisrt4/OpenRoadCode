#include <core.h>
#include <gui/gui.h>
#include <gui/menus/theme.h>
#include <module.h>
#include <utils/flog.h>
#include <utils/networking.h>

#include <algorithm>
#include <cctype>
#include <mutex>
#include <string>
#include <vector>

#define MAX_COMMAND_LENGTH 1024

SDRPP_MOD_INFO{
    /* Name:            */ "remote_control",
    /* Description:     */ "Remote application control server for SDR++",
    /* Author:          */ "OpenRoadCode contributors",
    /* Version:         */ 0, 1, 0,
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

        constexpr const char* prefix = "SET theme ";
        if (command.rfind(prefix, 0) == 0) {
            const std::string requested = trim(command.substr(std::char_traits<char>::length(prefix)));
            if (requested != "Dark" && requested != "Light") {
                writeResponse("ERROR invalid-value\n");
                return;
            }

            // The networking callbacks execute away from the ImGui render path.
            // Queue the request and apply it from the module's menu callback,
            // which SDR++ invokes on its GUI thread.
            {
                std::lock_guard<std::mutex> lock(pendingMutex);
                pendingTheme = requested;
            }
            writeResponse("OK\n");
            return;
        }

        writeResponse("ERROR unknown-command\n");
    }

public:
    // Called by SDR++ from its GUI path. The setup script creates one module
    // instance and registers this handler under the instance name.
    static void menuHandler(void* ctx) {
        auto* self = static_cast<RemoteControlModule*>(ctx);
        std::string requested;
        {
            std::lock_guard<std::mutex> lock(self->pendingMutex);
            requested.swap(self->pendingTheme);
        }
        if (requested.empty()) { return; }

        const auto it = std::find(thememenu::themeNames.begin(), thememenu::themeNames.end(), requested);
        if (it == thememenu::themeNames.end()) {
            flog::error("Remote Control requested unavailable theme '{}'", requested);
            return;
        }

        thememenu::themeId = static_cast<int>(std::distance(thememenu::themeNames.begin(), it));
        thememenu::applyTheme();

        core::configManager.acquire();
        core::configManager.conf["theme"] = requested;
        core::configManager.release(true);
        flog::info("Remote Control applied theme '{}'", requested);
    }

    void registerGuiHandler() {
        gui::menu.registerEntry(name, menuHandler, this, nullptr);
    }

    void unregisterGuiHandler() {
        gui::menu.removeEntry(name);
    }

private:
    std::string name;
    bool enabled = true;
    uint8_t dataBuf[1024]{};
    net::Listener listener;
    net::Conn client;
    std::string command;
    std::mutex pendingMutex;
    std::string pendingTheme;
};

MOD_EXPORT void _INIT_() {}

MOD_EXPORT ModuleManager::Instance* _CREATE_INSTANCE_(std::string name) {
    auto* instance = new RemoteControlModule(std::move(name));
    instance->registerGuiHandler();
    return instance;
}

MOD_EXPORT void _DELETE_INSTANCE_(void* instance) {
    auto* remote = static_cast<RemoteControlModule*>(instance);
    remote->unregisterGuiHandler();
    delete remote;
}

MOD_EXPORT void _END_() {}

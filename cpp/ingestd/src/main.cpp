#include "config.h"
#include "ingest_app.h"
#include "smtp_server.h"

#include <chrono>
#include <exception>
#include <filesystem>
#include <iostream>
#include <string>
#include <thread>

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--help") {
        std::cout << "usage: rapid-inbox-ingestd [--base-dir PATH] [--writer-smoke]\n";
        return 0;
    }

    std::filesystem::path base_dir = std::filesystem::current_path();
    bool writer_smoke = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--base-dir" && i + 1 < argc) {
            base_dir = argv[++i];
        } else if (arg == "--writer-smoke") {
            writer_smoke = true;
        }
    }

    try {
        auto config = rapid_inbox::ingestd::Config::load(base_dir);
        rapid_inbox::ingestd::IngestApp app(config);
        app.start_writer();
        if (writer_smoke) {
            app.stop_and_drain();
            std::cout << "writer smoke ok\n";
            return 0;
        }
        rapid_inbox::ingestd::SmtpServer server(config.smtp_host,
                                                config.smtp_port,
                                                app.domains(),
                                                app.queue(),
                                                config.max_recipients_per_message,
                                                config.max_message_size_bytes);
        server.start();
        std::cout << "rapid-inbox-ingestd listening on " << config.smtp_host << ":"
                  << config.smtp_port << "\n";
        while (true) {
            std::this_thread::sleep_for(std::chrono::hours(24));
        }
    } catch (const std::exception& exc) {
        std::cerr << "rapid-inbox-ingestd failed: " << exc.what() << "\n";
        return 1;
    }
}

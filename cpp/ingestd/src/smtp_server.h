#pragma once

#include "domain_cache.h"
#include "mail_queue.h"

#include <atomic>
#include <string>
#include <thread>
#include <vector>

namespace rapid_inbox::ingestd {

class SmtpServer {
public:
    SmtpServer(std::string host,
               int port,
               DomainCache& domains,
               MailQueue& queue,
               int max_recipients,
               int max_message_size_bytes);
    ~SmtpServer();

    void start();
    void stop();

private:
    void accept_loop();
    void handle_client(int client_fd);

    std::string host_;
    int port_;
    DomainCache& domains_;
    MailQueue& queue_;
    int max_recipients_;
    int max_message_size_bytes_;
    std::atomic<bool> running_{false};
    int listen_fd_ = -1;
    std::thread accept_thread_;
    std::vector<std::thread> client_threads_;
};

}

// client.cpp (con corrección de resolución IPv4)
#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <asio.hpp>
#include <asio/ts/buffer.hpp>
#include <asio/ts/internet.hpp>
#include <chrono>
#include <mutex>
#include "json.hpp"

using json = nlohmann::json;

std::mutex cout_mutex;

struct LogData {
    std::string client_full_id;
    std::string server_ip;
    int server_port;
    int messages_sent = 0;
    int messages_received = 0;
    bool connection_success = false;
    double total_latency_ms = 0.0;
    std::vector<std::string> errors;
    double average_latency_ms = 0.0;
};

void to_json(json& j, const LogData& p) {
    j = json{
        {"client_full_id", p.client_full_id},
        {"server_ip", p.server_ip},
        {"server_port", p.server_port},
        {"messages_sent", p.messages_sent},
        {"messages_received", p.messages_received},
        {"connection_success", p.connection_success},
        {"total_latency_ms", p.total_latency_ms},
        {"errors", p.errors},
        {"average_latency_ms", p.average_latency_ms}
    };
}

void outputLogData(const LogData& data) {
    json j = data;
    std::lock_guard<std::mutex> lock(cout_mutex);
    std::cout << j.dump() << std::endl;
}

void connectAndSend(int client_instance_id, const std::string& server_ip, int server_port, const std::string& client_id_base, int num_messages_per_client) {
    LogData logData;
    logData.client_full_id = client_id_base + "-" + std::to_string(client_instance_id);
    logData.server_ip = server_ip;
    logData.server_port = server_port;

    try {
        asio::io_context io_context;
        asio::ip::tcp::socket socket(io_context);
        asio::ip::tcp::resolver resolver(io_context);

        // CORRECCIÓN CLAVE: Forzamos la resolución de DNS a usar explícitamente el protocolo IPv4.
        auto endpoints = resolver.resolve(asio::ip::tcp::v4(), server_ip, std::to_string(server_port));

        asio::connect(socket, endpoints);
        logData.connection_success = true;

        for (int i = 0; i < num_messages_per_client; ++i) {
            try {
                std::string fullMessage = "msg " + std::to_string(i + 1) + " from " + logData.client_full_id;
                
                auto start = std::chrono::high_resolution_clock::now();

                asio::write(socket, asio::buffer(fullMessage));
                logData.messages_sent++;
                
                char reply[1024];
                
                asio::error_code ec;
                // Usamos asio::read para asegurar que leemos la respuesta completa del eco.
                size_t reply_length = asio::read(socket, asio::buffer(reply, fullMessage.length()), ec);

                if (ec) {
                    throw std::system_error(ec);
                }

                auto end = std::chrono::high_resolution_clock::now();
                std::chrono::duration<double, std::milli> latency = end - start;
                
                logData.total_latency_ms += latency.count();
                logData.messages_received++;
            
            } catch (const std::system_error& e) {
                 logData.errors.push_back("Error during message exchange: " + std::string(e.what()));
                 break;
            }
        }
    } catch (const std::system_error& e) {
        logData.errors.push_back("Connection failed: " + std::string(e.what()));
    }

    if (logData.messages_received > 0) {
        logData.average_latency_ms = logData.total_latency_ms / logData.messages_received;
    }

    outputLogData(logData);
}

std::string getEnv(const char* name, const std::string& defaultValue) {
    const char* value = std::getenv(name);
    return value ? value : defaultValue;
}

int main() {
    try {
        const std::string server_ip = getEnv("SERVER_IP", "localhost");
        const int server_port = std::stoi(getEnv("SERVER_PORT", "8080"));
        const std::string client_id_base = getEnv("CLIENT_ID", "default_client_pod");
        const int num_messages_per_client = std::stoi(getEnv("NUM_MESSAGES_PER_CLIENT", "1"));
        const int num_concurrent_clients = std::stoi(getEnv("NUM_CONCURRENT_CLIENTS", "1"));

        std::vector<std::thread> clients;
        for (int i = 0; i < num_concurrent_clients; ++i) {
            clients.emplace_back(connectAndSend, i, server_ip, server_port, client_id_base, num_messages_per_client);
        }

        for (auto& t : clients) {
            if (t.joinable()) {
                t.join();
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "Critical error in main: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
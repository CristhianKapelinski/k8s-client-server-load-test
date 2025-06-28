// server.cpp (com log de depuração)
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <asio.hpp>
#include <asio/ts/buffer.hpp>
#include <asio/ts/internet.hpp>

class session : public std::enable_shared_from_this<session> {
public:
    session(asio::ip::tcp::socket socket) : socket_(std::move(socket)) {}

    void start() {
        do_read();
    }

private:
    void do_read() {
        auto self(shared_from_this());
        socket_.async_read_some(asio::buffer(data_, max_length),
            [this, self](std::error_code ec, std::size_t length) {
                if (!ec) {
                    // PRINT DE DEPURAÇÃO: Confirma o recebimento e a tentativa de eco
                    std::cerr << "[DEBUG SERVER] Received " << length << " bytes. Echoing back..." << std::endl;
                    do_write(length);
                } else if (ec != asio::error::eof) {
                    std::cerr << "[-] Error reading from client: " << ec.message() << std::endl;
                }
            });
    }

    void do_write(std::size_t length) {
        auto self(shared_from_this());
        asio::async_write(socket_, asio::buffer(data_, length),
            [this, self](std::error_code ec, std::size_t /*length*/) {
                if (!ec) {
                    do_read();
                } else {
                    std::cerr << "[-] Error writing to client: " << ec.message() << std::endl;
                }
            });
    }

    asio::ip::tcp::socket socket_;
    enum { max_length = 1024 };
    char data_[max_length];
};

class server {
public:
    server(asio::io_context& io_context, short port)
        : acceptor_(io_context, asio::ip::tcp::endpoint(asio::ip::tcp::v4(), port)) {
        do_accept();
    }

private:
    void do_accept() {
        acceptor_.async_accept(
            [this](std::error_code ec, asio::ip::tcp::socket socket) {
                if (!ec) {
                    std::make_shared<session>(std::move(socket))->start();
                } else {
                     std::cerr << "[-] Error accepting connection: " << ec.message() << std::endl;
                }
                do_accept(); 
            });
    }

    asio::ip::tcp::acceptor acceptor_;
};

int main() {
    try {
        unsigned short port = 8080;
        if (const char* port_str = std::getenv("PORT")) {
            try {
                port = std::stoi(port_str);
            } catch (const std::exception& e) {
                std::cerr << "Warning: Invalid PORT environment variable '" << port_str 
                          << "'. Using default port 8080. Error: " << e.what() << std::endl;
            }
        }

        asio::io_context io_context;
        server s(io_context, port);

        std::cout << "[*] C++ Server Serving on 0.0.0.0:" << port << std::endl;

        unsigned int thread_pool_size = std::thread::hardware_concurrency();
        if (thread_pool_size == 0) thread_pool_size = 2; 
        std::vector<std::thread> threads;
        for (unsigned int i = 0; i < thread_pool_size; ++i) {
            threads.emplace_back([&io_context]() { io_context.run(); });
        }

        for (auto& t : threads) {
            if (t.joinable()) {
                t.join();
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    return 0;
}
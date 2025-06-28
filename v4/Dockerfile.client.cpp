# Dockerfile.client.cpp
# Estágio 1: Builder - Usando Alpine como base para consistência
FROM alpine:latest as builder

# Instala as dependências de compilação (g++, make, libstdc++, asio, etc.)
RUN apk add --no-cache g++ make libstdc++-dev asio-dev

WORKDIR /app
COPY client.cpp .
COPY json.hpp .

# Compila o cliente com otimizações (-O3) em um ambiente Alpine
RUN g++ -std=c++20 -O3 -o client client.cpp -lstdc++ -lpthread

# Estágio 2: Final - Imagem leve
FROM alpine:latest

# Instala dependências de tempo de execução
RUN apk add --no-cache libstdc++ asio

WORKDIR /app
# Copia o executável compilado do estágio 'builder'
COPY --from=builder /app/client .

# Comando para iniciar o cliente quando o container for executado
CMD ["./client"]
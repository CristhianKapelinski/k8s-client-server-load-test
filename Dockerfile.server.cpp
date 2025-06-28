# Dockerfile.server.cpp
# Estágio 1: Builder - Usando Alpine como base para consistência
FROM alpine:latest as builder

# Instala as dependências de compilação (g++, make, libstdc++, asio, etc.)
RUN apk add --no-cache g++ make libstdc++-dev asio-dev

WORKDIR /app
COPY server.cpp .

# Compila o servidor com otimizações (-O3) em um ambiente Alpine
RUN g++ -std=c++20 -O3 -o server server.cpp -lstdc++ -lpthread

# Estágio 2: Final - Imagem leve apenas com o executável e suas dependências
FROM alpine:latest

# Instala apenas as dependências de tempo de execução (runtime)
# A 'asio' aqui é a biblioteca de runtime, não os cabeçalhos de desenvolvimento (-dev)
RUN apk add --no-cache libstdc++ asio

WORKDIR /app
# Copia o executável compilado do estágio 'builder' (que agora é compatível)
COPY --from=builder /app/server .

# Expõe a porta que o servidor irá escutar
EXPOSE 8080

# Comando para iniciar o servidor quando o container for executado
CMD ["./server"]
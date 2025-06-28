#!/bin/bash

# --- Configurações ---
DOCKER_USER="kapelinsky" # Seu usuário do Docker Hub

# Imagens Docker Python
SERVER_IMAGE_PYTHON="$DOCKER_USER/tcp-server:latest"
CLIENT_IMAGE_PYTHON="$DOCKER_USER/tcp-client:latest"
SERVER_DOCKERFILE_PYTHON="Dockerfile.server"
CLIENT_DOCKERFILE_PYTHON="Dockerfile.client"

# Imagens Docker Go
SERVER_IMAGE_GO="$DOCKER_USER/tcp-server-go:latest"
CLIENT_IMAGE_GO="$DOCKER_USER/tcp-client-go:latest"
SERVER_DOCKERFILE_GO="Dockerfile.server.go"
CLIENT_DOCKERFILE_GO="Dockerfile.client.go"

# --- Função de Construção e Envio (Push) ---
build_and_push() {
    local lang_name=$1
    local image_name=$2
    local dockerfile_name=$3
    local app_type=$4 # "servidor" ou "cliente"

    echo "--- Testando construção e envio da imagem do $app_type $lang_name ($image_name) com $dockerfile_name ---"
    
    echo "Construindo imagem..."
    docker build -t "$image_name" -f "$dockerfile_name" .
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao construir a imagem do $app_type $lang_name. Verifique o Dockerfile e o código fonte."
        return 1
    fi
    echo "Construção da imagem do $app_type $lang_name CONCLUÍDA."

    echo "Enviando imagem para o Docker Hub..."
    docker push "$image_name"
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao enviar a imagem do $app_type $lang_name para o Docker Hub. Verifique seu login (docker login) e permissões."
        return 1
    fi
    echo "Envio da imagem do $app_type $lang_name CONCLUÍDO."
    echo "" # Linha em branco para separação
    return 0
}

# --- Execução dos Testes de Construção ---

echo "Iniciando testes de construção e envio de imagens..."
echo "Certifique-se de que está logado no Docker Hub (docker login) e que os Dockerfiles e arquivos de código fonte estão no diretório atual."
echo ""

# Testar Python Server
build_and_push "Python" "$SERVER_IMAGE_PYTHON" "$SERVER_DOCKERFILE_PYTHON" "servidor" || exit 1

# Testar Python Client
build_and_push "Python" "$CLIENT_IMAGE_PYTHON" "$CLIENT_DOCKERFILE_PYTHON" "cliente" || exit 1

# Testar Go Server
build_and_push "Go" "$SERVER_IMAGE_GO" "$SERVER_DOCKERFILE_GO" "servidor" || exit 1

# Testar Go Client
build_and_push "Go" "$CLIENT_IMAGE_GO" "$CLIENT_DOCKERFILE_GO" "cliente" || exit 1

echo "Todos os testes de construção e envio concluídos com sucesso (se você não viu mensagens de ERRO acima)."
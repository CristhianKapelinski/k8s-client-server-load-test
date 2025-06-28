#!/bin/bash

# Define seu usuário do Docker Hub
DOCKER_USER="kapelinsky" # Default, can be overridden by argument

# Imagens Docker Python
SERVER_IMAGE_PYTHON="$DOCKER_USER/tcp-server:latest"
CLIENT_IMAGE_PYTHON="$DOCKER_USER/tcp-client:latest"

# Imagens Docker Go
SERVER_IMAGE_GO="$DOCKER_USER/tcp-server-go:latest"
CLIENT_IMAGE_GO="$DOCKER_USER/tcp-client-go:latest"

# Dockerfiles correspondentes
SERVER_DOCKERFILE_PYTHON="Dockerfile.server"
CLIENT_DOCKERFILE_PYTHON="Dockerfile.client"
SERVER_DOCKERFILE_GO="Dockerfile.server.go"
CLIENT_DOCKERFILE_GO="Dockerfile.client.go"

# Diretório para salvar os logs
LOG_DIR="logs"
RAW_LOG_DIR="$LOG_DIR/raw_client_logs" # Base directory for raw client logs

# Configurações de teste padrão
SERVER_REPLICAS_ARRAY=(2 4 6 8 10)
CLIENT_CONCURRENCY_ARRAY=(10 20 30 40 50 60 70 80 90 100 1000)
MESSAGES_PER_CLIENT_ARRAY=(1 10 100 1000)

# Função para exibir uso
usage() {
    echo "Uso: $0 [-u <docker_user>] [-s <server_replicas>] [-c <client_concurrency>] [-m <messages_per_client>]"
    echo "  -u <docker_user>: Usuário do Docker Hub (padrão: $DOCKER_USER)"
    echo "  -s <server_replicas>: Lista de réplicas de servidor separadas por vírgula (padrão: ${SERVER_REPLICAS_ARRAY[*]//$'\n'/,})"
    echo "  -c <client_concurrency>: Lista de clientes concorrentes por pod separados por vírgula (padrão: ${CLIENT_CONCURRENCY_ARRAY[*]//$'\n'/,})"
    echo "  -m <messages_per_client>: Lista de mensagens por cliente separado por vírgula (padrão: ${MESSAGES_PER_CLIENT_ARRAY[*]//$'\n'/,})"
    echo "Este script executa os testes para as implementações Python e Go e compara os resultados."
    exit 1
}

# Parse argumentos da linha de comando
while getopts "u:s:c:m:" opt; do
    case "$opt" in
        u) DOCKER_USER="$OPTARG"
           SERVER_IMAGE_PYTHON="$DOCKER_USER/tcp-server:latest"
           CLIENT_IMAGE_PYTHON="$DOCKER_USER/tcp-client:latest"
           SERVER_IMAGE_GO="$DOCKER_USER/tcp-server-go:latest"
           CLIENT_IMAGE_GO="$DOCKER_USER/tcp-client-go:latest"
           ;;
        s) IFS=',' read -r -a SERVER_REPLICAS_ARRAY <<< "$OPTARG" ;;
        c) IFS=',' read -r -a CLIENT_CONCURRENCY_ARRAY <<< "$OPTARG" ;;
        m) IFS=',' read -r -a MESSAGES_PER_CLIENT_ARRAY <<< "$OPTARG" ;;
        \?) usage ;;
    esac
done
shift $((OPTIND-1))

# Limpa qualquer resquício de execuções anteriores no Kubernetes
cleanup_kubernetes() {
    echo "Limpando recursos Kubernetes..."
    kubectl delete deployment server-deployment --ignore-not-found --wait=false
    kubectl delete service server-service --ignore-not-found --wait=false
    kubectl delete jobs -l app=client --ignore-not-found --wait=false
    # Espera para garantir que os recursos foram removidos antes de prosseguir
    sleep 5
    echo "Recursos Kubernetes limpos."
}

# Constrói e envia as imagens Docker para uma dada linguagem
build_and_push_images_for_lang() {
    local lang_name=$1
    local server_image=$2
    local client_image=$3
    local server_dockerfile=$4
    local client_dockerfile=$5

    echo "Construindo imagem do servidor $lang_name ($server_image) com $server_dockerfile..."
    docker build -t "$server_image" -f "$server_dockerfile" .
    docker push "$server_image" || { echo "Erro ao enviar imagem do servidor $lang_name para o Docker Hub. Verifique seu login e permissões."; exit 1; }

    echo "Construindo imagem do cliente $lang_name ($client_image) com $client_dockerfile..."
    docker build -t "$client_image" -f "$client_dockerfile" .
    docker push "$client_image" || { echo "Erro ao enviar imagem do cliente $lang_name para o Docker Hub. Verifique seu login e permissões."; exit 1; }
    echo "Imagens $lang_name construídas e enviadas para o Docker Hub."
}

# Função para aguardar os pods de deployment estarem prontos
wait_for_deployment() {
    local deployment_name=$1
    echo "Aguardando o deployment '$deployment_name' estar pronto..."
    kubectl wait --for=condition=Available deployment/"$deployment_name" --timeout=300s
    if [ $? -ne 0 ]; then
        echo "Erro: O deployment '$deployment_name' não ficou pronto a tempo."
        echo "Verifique o status do seu cluster Kubernetes (kubectl cluster-info, kubectl get nodes) e os logs dos pods."
        exit 1
    fi
    echo "Deployment '$deployment_name' pronto."
}

# Executa os testes para uma dada linguagem
run_tests_for_lang() {
    local lang_name=$1
    local server_image=$2
    local client_image=$3
    local raw_log_subdir="$RAW_LOG_DIR/$lang_name" # Subdiretório para logs brutos desta linguagem

    mkdir -p "$raw_log_subdir"

    echo "--- Iniciando testes para a linguagem: $lang_name ---"

    # Aplica o deployment inicial do servidor (que já inclui o Service)
    echo "Aplicando deployment e serviço iniciais do servidor para $lang_name..."
    # Usamos sed para substituir a imagem no yaml antes de aplicar
    sed "s|image: kapelinsky/tcp-server:latest|image: $server_image|" server-deployment.yaml > server-deployment-temp.yaml
    kubectl apply -f server-deployment-temp.yaml
    rm server-deployment-temp.yaml

    wait_for_deployment server-deployment

    # Testes
    for num_servers in "${SERVER_REPLICAS_ARRAY[@]}"; do
        echo "--- Testando com $num_servers instâncias de servidor ($lang_name) ---"
        
        # Atualiza o número de réplicas do servidor e aplica o deployment
        # Usamos sed para substituir a imagem e o número de réplicas
        sed -e "s/replicas: [0-9]*/replicas: $num_servers/" -e "s|image: kapelinsky/tcp-server:latest|image: $server_image|" server-deployment.yaml > server-deployment-temp.yaml
        kubectl apply -f server-deployment-temp.yaml
        rm server-deployment-temp.yaml

        wait_for_deployment server-deployment

        echo "Salvando status dos pods do servidor ($num_servers, $lang_name) em $LOG_DIR/server_pods_${num_servers}_${lang_name}.log"
        kubectl get pods -l app=server > "$LOG_DIR/server_pods_${num_servers}_${lang_name}.log"
        kubectl describe deployment server-deployment >> "$LOG_DIR/server_pods_${num_servers}_${lang_name}.log"
        
        # Testes de cliente
        for num_concurrent_clients in "${CLIENT_CONCURRENCY_ARRAY[@]}"; do
            for num_messages_per_client in "${MESSAGES_PER_CLIENT_ARRAY[@]}"; do
                echo "--- Testando com $num_concurrent_clients clientes (concorrentes) e $num_messages_per_client mensagens ($lang_name, com $num_servers servidores) ---"
                
                # Limpa Jobs de cliente anteriores
                kubectl delete jobs -l app=client --ignore-not-found --wait=false
                sleep 5 # Garante que os jobs foram removidos

                CLIENT_JOB_NAME="client-job-${lang_name}-${num_servers}s-${num_concurrent_clients}c-${num_messages_per_client}m"
                RAW_LOG_FILE="$raw_log_subdir/client_raw_log_${num_servers}s_${num_concurrent_clients}c_${num_messages_per_client}m.log"

                # Cria Job de cliente (apenas um pod cliente por vez para este cenário)
                cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $CLIENT_JOB_NAME
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app: client
    spec:
      restartPolicy: Never
      containers:
      - name: client
        image: $client_image # Usando a imagem da linguagem atual
        env:
        - name: SERVER_IP
          value: "server-service"
        - name: SERVER_PORT
          value: "8080"
        - name: CLIENT_ID
          value: "$CLIENT_JOB_NAME-$(date +%s%N)" # Unique ID for the pod
        - name: NUM_CONCURRENT_CLIENTS
          value: "$num_concurrent_clients"
        - name: NUM_MESSAGES_PER_CLIENT
          value: "$num_messages_per_client"
EOF
                echo "Aguardando a conclusão do Job do cliente '$CLIENT_JOB_NAME' (pode levar um tempo)..."
                # Calcula um timeout mais inteligente baseado no número de mensagens e clientes concorrentes
                estimated_time_per_message_ms=100
                total_message_interactions=$((num_concurrent_clients * num_messages_per_client))
                timeout_seconds=$((total_message_interactions / 10 + 60)) # Base 100ms/message, plus 60s buffer
                if [ $timeout_seconds -lt 120 ]; then timeout_seconds=120; fi # Minimum 2 minutes

                kubectl wait --for=condition=complete job/"$CLIENT_JOB_NAME" --timeout=${timeout_seconds}s
                if [ $? -ne 0 ]; then
                    echo "Erro: O Job '$CLIENT_JOB_NAME' não foi concluído a tempo ou falhou."
                    echo "Salvando logs do pod do cliente falho em $RAW_LOG_FILE"
                    failed_pod=$(kubectl get pods -l job-name="$CLIENT_JOB_NAME" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                    if [ -n "$failed_pod" ]; then
                        kubectl logs "$failed_pod" > "$RAW_LOG_FILE"
                    else
                        echo "Nenhum pod encontrado para o job $CLIENT_JOB_NAME." >> "$RAW_LOG_FILE"
                    fi
                else
                    echo "Job '$CLIENT_JOB_NAME' concluído."
                    echo "Salvando logs do pod do cliente em $RAW_LOG_FILE"
                    client_pod_name=$(kubectl get pods -l job-name="$CLIENT_JOB_NAME" --field-selector=status.phase=Succeeded -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                    if [ -n "$client_pod_name" ]; then
                        kubectl logs "$client_pod_name" > "$RAW_LOG_FILE"
                    else
                        echo "Nenhum pod concluído encontrado para o job $CLIENT_JOB_NAME." > "$RAW_LOG_FILE"
                    fi
                fi
            done # num_messages_per_client
        done # num_concurrent_clients
    done # num_servers
}

# Processa logs e gera CSV
process_and_generate_csv_for_lang() {
    local lang_name=$1
    local raw_log_subdir="$RAW_LOG_DIR/$lang_name"
    local output_csv="$LOG_DIR/results_${lang_name}.csv"
    echo "Processando logs brutos de $lang_name e gerando CSV em $output_csv..."
    python3 process_logs.py "$raw_log_subdir" "$output_csv" || { echo "Erro ao processar logs de $lang_name e gerar CSV."; exit 1; }
    echo "Dados de teste de $lang_name salvos em $output_csv"
}

# Combina os CSVs e adiciona a coluna 'language'
combine_csvs() {
    echo "Combinando CSVs de Python e Go..."
    PYTHON_CSV="$LOG_DIR/results_python.csv"
    GO_CSV="$LOG_DIR/results_go.csv"
    FINAL_CSV="$LOG_DIR/results_combined.csv"

    if [ ! -f "$PYTHON_CSV" ] || [ ! -f "$GO_CSV" ]; then
        echo "Erro: Um ou ambos os CSVs de linguagem não foram encontrados. Verifique as execuções anteriores."
        exit 1
    fi

    # Adiciona a coluna 'language' e combina
    # Use awk para adicionar a coluna 'language' no final e depois concatene
    # Para o Python CSV
    awk -v lang="python" 'BEGIN {FS=OFS=","} NR==1 {$0=$0",language"} NR>1 {$0=$0","lang} 1' "$PYTHON_CSV" > "${PYTHON_CSV}.tmp"
    # Para o Go CSV
    awk -v lang="go" 'BEGIN {FS=OFS=","} NR==1 {$0=$0",language"} NR>1 {$0=$0","lang} 1' "$GO_CSV" > "${GO_CSV}.tmp"

    # Concatena (ignorando o cabeçalho do segundo arquivo)
    head -n 1 "${PYTHON_CSV}.tmp" > "$FINAL_CSV"
    tail -n +2 "${PYTHON_CSV}.tmp" >> "$FINAL_CSV"
    tail -n +2 "${GO_CSV}.tmp" >> "$FINAL_CSV"

    rm "${PYTHON_CSV}.tmp" "${GO_CSV}.tmp"

    echo "Dados combinados salvos em $FINAL_CSV"
}

# Gera gráficos
generate_graphs_combined() {
    echo "Gerando gráficos de resultados combinados..."
    python3 generate_graphs.py "$LOG_DIR/results_combined.csv" "$LOG_DIR/graphs" || { echo "Erro ao gerar gráficos combinados."; exit 1; }
    echo "Gráficos salvos em $LOG_DIR/graphs/"
}

# Ordem de execução principal
cleanup_kubernetes # Limpeza inicial

# --- Execução para Python ---
build_and_push_images_for_lang "python" "$SERVER_IMAGE_PYTHON" "$CLIENT_IMAGE_PYTHON" "$SERVER_DOCKERFILE_PYTHON" "$CLIENT_DOCKERFILE_PYTHON"
run_tests_for_lang "python" "$SERVER_IMAGE_PYTHON" "$CLIENT_IMAGE_PYTHON"
process_and_generate_csv_for_lang "python"

# --- Execução para Go ---
cleanup_kubernetes # Limpeza entre as linguagens
build_and_push_images_for_lang "go" "$SERVER_IMAGE_GO" "$CLIENT_IMAGE_GO" "$SERVER_DOCKERFILE_GO" "$CLIENT_DOCKERFILE_GO"
run_tests_for_lang "go" "$SERVER_IMAGE_GO" "$CLIENT_IMAGE_GO"
process_and_generate_csv_for_lang "go"

# --- Análise e Geração de Gráficos ---
combine_csvs
generate_graphs_combined

cleanup_kubernetes # Limpeza final

echo "Todos os testes foram concluídos."
echo "Os logs estão salvos no diretório '$LOG_DIR/'."
echo "Script finalizado."
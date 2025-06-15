#!/bin/bash

# Define seu usuário do Docker Hub
DOCKER_USER="kapelinsky" # Default, can be overridden by argument

# Imagens Docker
SERVER_IMAGE="$DOCKER_USER/tcp-server:latest"
CLIENT_IMAGE="$DOCKER_USER/tcp-client:latest"

# Diretório para salvar os logs
LOG_DIR="logs"
RAW_LOG_DIR="$LOG_DIR/raw_client_logs" # Directory for raw client logs

# Configurações de teste padrão
SERVER_REPLICAS_ARRAY=(2 4 6 8 10)
CLIENT_CONCURRENCY_ARRAY=(10 20 30 40 50 60 70 80 90 100)
MESSAGES_PER_CLIENT_ARRAY=(1 10 100)

# Função para exibir uso
usage() {
    echo "Uso: $0 [-u <docker_user>] [-s <server_replicas>] [-c <client_concurrency>] [-m <messages_per_client>]"
    echo "  -u <docker_user>: Usuário do Docker Hub (padrão: $DOCKER_USER)"
    echo "  -s <server_replicas>: Lista de réplicas de servidor separadas por vírgula (padrão: ${SERVER_REPLICAS_ARRAY[*]//$'\n'/,})"
    echo "  -c <client_concurrency>: Lista de clientes concorrentes por pod separados por vírgula (padrão: ${CLIENT_CONCURRENCY_ARRAY[*]//$'\n'/,})"
    echo "  -m <messages_per_client>: Lista de mensagens por cliente separado por vírgula (padrão: ${MESSAGES_PER_CLIENT_ARRAY[*]//$'\n'/,})"
    exit 1
}

# Parse argumentos da linha de comando
while getopts "u:s:c:m:" opt; do
    case "$opt" in
        u) DOCKER_USER="$OPTARG"
           SERVER_IMAGE="$DOCKER_USER/tcp-server:latest"
           CLIENT_IMAGE="$DOCKER_USER/tcp-client:latest"
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

# Constrói e envia as imagens Docker
build_and_push_images() {
    echo "Construindo imagem do servidor..."
    docker build -t "$SERVER_IMAGE" -f Dockerfile.server .
    docker push "$SERVER_IMAGE" || { echo "Erro ao enviar imagem do servidor para o Docker Hub. Verifique seu login e permissões."; exit 1; }

    echo "Construindo imagem do cliente..."
    docker build -t "$CLIENT_IMAGE" -f Dockerfile.client .
    docker push "$CLIENT_IMAGE" || { echo "Erro ao enviar imagem do cliente para o Docker Hub. Verifique seu login e permissões."; exit 1; }
    echo "Imagens construídas e enviadas para o Docker Hub."
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

# Executa os testes
run_tests() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$RAW_LOG_DIR"

    # Aplica o deployment inicial do servidor (que já inclui o Service)
    echo "Aplicando deployment e serviço iniciais do servidor..."
    kubectl apply -f server-deployment.yaml
    wait_for_deployment server-deployment

    # Testes
    for num_servers in "${SERVER_REPLICAS_ARRAY[@]}"; do
        echo "--- Testando com $num_servers instâncias de servidor ---"
        
        # Atualiza o número de réplicas do servidor e aplica o deployment
        sed "s/replicas: [0-9]*/replicas: $num_servers/" server-deployment.yaml > server-deployment-temp.yaml
        kubectl apply -f server-deployment-temp.yaml
        rm server-deployment-temp.yaml

        wait_for_deployment server-deployment

        echo "Salvando status dos pods do servidor ($num_servers) em $LOG_DIR/server_pods_${num_servers}.log"
        kubectl get pods -l app=server > "$LOG_DIR/server_pods_${num_servers}.log"
        kubectl describe deployment server-deployment >> "$LOG_DIR/server_pods_${num_servers}.log"
        
        # Testes de cliente
        for num_concurrent_clients in "${CLIENT_CONCURRENCY_ARRAY[@]}"; do
            for num_messages_per_client in "${MESSAGES_PER_CLIENT_ARRAY[@]}"; do
                echo "--- Testando com $num_concurrent_clients clientes (concorrentes) e $num_messages_per_client mensagens (com $num_servers servidores) ---"
                
                # Limpa Jobs de cliente anteriores
                kubectl delete jobs -l app=client --ignore-not-found --wait=false
                sleep 5 # Garante que os jobs foram removidos

                CLIENT_JOB_NAME="client-job-${num_servers}s-${num_concurrent_clients}c-${num_messages_per_client}m"
                RAW_LOG_FILE="$RAW_LOG_DIR/client_raw_log_${num_servers}s_${num_concurrent_clients}c_${num_messages_per_client}m.log"

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
        image: $CLIENT_IMAGE
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
                # Assumindo ~100ms de latência por mensagem e um buffer para a inicialização
                estimated_time_per_message_ms=100 
                # Total de interações de mensagem para um único cliente concorrente
                total_message_interactions=$((num_concurrent_clients * num_messages_per_client))
                timeout_seconds=$((total_message_interactions / 10 + 60)) # Base 100ms/message, plus 60s buffer
                if [ $timeout_seconds -lt 120 ]; then timeout_seconds=120; fi # Minimum 2 minutes

                kubectl wait --for=condition=complete job/"$CLIENT_JOB_NAME" --timeout=${timeout_seconds}s
                if [ $? -ne 0 ]; then
                    echo "Erro: O Job '$CLIENT_JOB_NAME' não foi concluído a tempo ou falhou."
                    # Captura logs mesmo se falhar para depuração
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
                    # Assume que o job gerou apenas um pod, ou pega o primeiro que completou
                    client_pod_name=$(kubectl get pods -l job-name="$CLIENT_JOB_NAME" --field-selector=status.phase=Succeeded -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                    if [ -n "$client_pod_name" ]; then
                        kubectl logs "$client_pod_name" > "$RAW_LOG_FILE"
                    else
                        echo "Nenhum pod concluído encontrado para o job $CLIENT_JOB_NAME." > "$RAW_LOG_FILE"
                    fi
                fi
                
                # Opcional: Salvar status do job e pod, mas os logs brutos são mais importantes agora
                # kubectl get jobs "$CLIENT_JOB_NAME" > "$LOG_DIR/client_job_status_${num_servers}s_${num_concurrent_clients}c_${num_messages_per_client}m.log"
                # kubectl get pods -l job-name="$CLIENT_JOB_NAME" > "$LOG_DIR/client_pod_status_${num_servers}s_${num_concurrent_clients}c_${num_messages_per_client}m.log"

            done # num_messages_per_client
        done # num_concurrent_clients
    done # num_servers
}

# Processa logs e gera CSV
process_and_generate_csv() {
    echo "Processando logs brutos e gerando CSV..."
    python3 process_logs.py "$RAW_LOG_DIR" "$LOG_DIR/results.csv" || { echo "Erro ao processar logs e gerar CSV."; exit 1; }
    echo "Dados de teste salvos em $LOG_DIR/results.csv"
}

# Gera gráficos
generate_graphs() {
    echo "Gerando gráficos de resultados..."
    python3 generate_graphs.py "$LOG_DIR/results.csv" "$LOG_DIR/graphs" || { echo "Erro ao gerar gráficos."; exit 1; }
    echo "Gráficos salvos em $LOG_DIR/graphs/"
}

# Ordem de execução
cleanup_kubernetes
build_and_push_images
run_tests
process_and_generate_csv
generate_graphs
cleanup_kubernetes # Limpeza final

echo "Todos os testes foram concluídos."
echo "Os logs estão salvos no diretório '$LOG_DIR/'."
echo "Script finalizado."
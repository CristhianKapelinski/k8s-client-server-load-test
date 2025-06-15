#!/bin/bash

# Define seu usuário do Docker Hub
DOCKER_USER="kapelinsky"

# Imagens Docker
SERVER_IMAGE="$DOCKER_USER/tcp-server:latest"
CLIENT_IMAGE="$DOCKER_USER/tcp-client:latest"

# Diretório para salvar os logs
LOG_DIR="logs"

# Limpa qualquer resquício de execuções anteriores no Kubernetes
cleanup_kubernetes() {
    echo "Limpando recursos Kubernetes..."
    kubectl delete deployment server-deployment --ignore-not-found --wait=false # Não espera a exclusão para agilizar
    kubectl delete service server-service --ignore-not-found --wait=false
    kubectl delete jobs -l app=client --ignore-not-found --wait=false
    sleep 5 # Dê um tempo para o Kubernetes processar as deleções
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

    # Testes de servidor (2 a 10 instâncias, aumentando de 2 em 2)
    for num_servers in 2 4 6 8 10; do
        echo "--- Testando com $num_servers instâncias de servidor ---"
        
        # Atualiza o número de réplicas do servidor e aplica o deployment
        sed "s/replicas: [0-9]*/replicas: $num_servers/" server-deployment.yaml > server-deployment-temp.yaml
        kubectl apply -f server-deployment-temp.yaml
        rm server-deployment-temp.yaml

        wait_for_deployment server-deployment

        echo "Salvando status dos pods do servidor ($num_servers) em $LOG_DIR/server_pods_${num_servers}.log"
        kubectl get pods -l app=server > "$LOG_DIR/server_pods_${num_servers}.log"
        kubectl describe deployment server-deployment >> "$LOG_DIR/server_pods_${num_servers}.log"
        
        # Testes de cliente (APENAS 10, 50, 100 clientes)
        for num_clients in 10 50 100; do # <-- AQUI ESTÁ A MUDANÇA
            echo "--- Testando com $num_clients clientes (com $num_servers servidores) ---"
            
            # Limpa Jobs de cliente anteriores
            kubectl delete jobs -l app=client --ignore-not-found --wait=false
            sleep 5 # Aumentado para garantir que a deleção seja processada antes de criar novos

            # Cria Jobs de cliente
            for i in $(seq 1 $num_clients); do
                CLIENT_JOB_NAME="client-job-${num_servers}s-${i}c"
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
          value: "$CLIENT_JOB_NAME-$(date +%s%N)"
EOF
            done

            echo "Aguardando a conclusão dos Jobs do cliente (pode levar um tempo)..."
            # Loop mais inteligente para aguardar todos os jobs concluírem
            start_time=$(date +%s)
            timeout_seconds=$((num_clients * 2 + 60)) # Aumenta timeout com mais clientes, mínimo de 60s
            jobs_completed=0
            while [ $jobs_completed -lt $num_clients ]; do
                current_time=$(date +%s)
                if (( current_time - start_time > timeout_seconds )); then
                    echo "Erro: Tempo limite de espera para os jobs do cliente excedido ($timeout_seconds segundos)."
                    break
                fi
                jobs_completed=$(kubectl get jobs -l app=client -o jsonpath='{.items[*].status.succeeded}' 2>/dev/null | tr -s ' ' '\n' | grep -c 1 || echo 0)
                echo "Jobs concluídos: $jobs_completed/$num_clients"
                sleep 10 # Verifica a cada 10 segundos
            done
            
            echo "Salvando status dos Jobs do cliente em $LOG_DIR/client_jobs_${num_servers}s_${num_clients}c.log"
            kubectl get jobs -l app=client > "$LOG_DIR/client_jobs_${num_servers}s_${num_clients}c.log"

            echo "Salvando status dos Pods do cliente em $LOG_DIR/client_pods_${num_servers}s_${num_clients}c.log"
            kubectl get pods -l app=client > "$LOG_DIR/client_pods_${num_servers}s_${num_clients}c.log"

            echo "Salvando logs de um cliente de exemplo em $LOG_DIR/client_logs_example_${num_servers}s_${num_clients}c.log"
            first_client_pod=$(kubectl get pods -l app=client --field-selector=status.phase=Succeeded -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [ -n "$first_client_pod" ]; then
                kubectl logs "$first_client_pod" > "$LOG_DIR/client_logs_example_${num_servers}s_${num_clients}c.log"
            else
                echo "Nenhum pod de cliente concluído encontrado para exibir logs." > "$LOG_DIR/client_logs_example_${num_servers}s_${num_clients}c.log"
            fi
        done
    done
}

# Ordem de execução
cleanup_kubernetes
build_and_push_images

# Aplica o deployment inicial do servidor (que já inclui o Service)
echo "Aplicando deployment e serviço iniciais do servidor..."
kubectl apply -f server-deployment.yaml
wait_for_deployment server-deployment

run_tests

echo "Todos os testes foram concluídos."
echo "Os logs estão salvos no diretório '$LOG_DIR/'."
echo "Limpando recursos finais do Kubernetes..."
cleanup_kubernetes

echo "Script finalizado."
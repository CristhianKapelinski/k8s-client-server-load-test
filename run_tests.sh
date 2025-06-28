#!/bin/bash

set -e # Encerra o script se qualquer comando falhar

# --- CONFIGURAÇÃO ---

# Defina seu usuário do Docker Hub
DOCKER_USER="kapelinsky" # Default, pode ser substituído pelo argumento -u

# Número total de vezes que o conjunto de testes completo será executado
TOTAL_RUNS=10

# Imagens Docker Go
SERVER_IMAGE_GO="$DOCKER_USER/tcp-server-go:latest"
CLIENT_IMAGE_GO="$DOCKER_USER/tcp-client-go:latest"

# Imagens Docker C++
SERVER_IMAGE_CPP="$DOCKER_USER/tcp-server-cpp:latest"
CLIENT_IMAGE_CPP="$DOCKER_USER/tcp-client-cpp:latest"

# Dockerfiles correspondentes
SERVER_DOCKERFILE_GO="Dockerfile.server.go"
CLIENT_DOCKERFILE_GO="Dockerfile.client.go"
SERVER_DOCKERFILE_CPP="Dockerfile.server.cpp"
CLIENT_DOCKERFILE_CPP="Dockerfile.client.cpp"

# Diretório base para salvar todos os logs
BASE_LOG_DIR="logs"

# Configurações de teste padrão (editáveis via linha de comando)
SERVER_REPLICAS_ARRAY=(2 4 6 8 10)
CLIENT_CONCURRENCY_ARRAY=(10 20 30 40 50 60 70 80 90 100)  
MESSAGES_PER_CLIENT_ARRAY=(1 10 100 500 1000 10000)

# --- FUNÇÕES AUXILIARES ---

# Função para exibir uso
usage() {
    echo "Uso: $0 [-u <docker_user>] [-s <server_replicas>] [-c <client_concurrency>] [-m <messages_per_client>]"
    echo "  -u <docker_user>: Usuário do Docker Hub (padrão: $DOCKER_USER)"
    echo "  -s <server_replicas>: Lista de réplicas de servidor separadas por vírgula (padrão: ${SERVER_REPLICAS_ARRAY[*]})"
    echo "  -c <client_concurrency>: Lista de clientes concorrentes separados por vírgula (padrão: ${CLIENT_CONCURRENCY_ARRAY[*]})"
    echo "  -m <messages_per_client>: Lista de mensagens por cliente separado por vírgula (padrão: ${MESSAGES_PER_CLIENT_ARRAY[*]})"
    echo "Este script executa os testes para as implementações Go e C++ por $TOTAL_RUNS vezes."
    exit 1
}

# Parse de argumentos da linha de comando
while getopts "u:s:c:m:" opt; do
    case "$opt" in
        u) DOCKER_USER="$OPTARG" ;;
        s) IFS=',' read -r -a SERVER_REPLICAS_ARRAY <<< "$OPTARG" ;;
        c) IFS=',' read -r -a CLIENT_CONCURRENCY_ARRAY <<< "$OPTARG" ;;
        m) IFS=',' read -r -a MESSAGES_PER_CLIENT_ARRAY <<< "$OPTARG" ;;
        \?) usage ;;
    esac
done
shift $((OPTIND-1))

# Limpeza completa do ambiente Kubernetes
cleanup_kubernetes() {
    echo "Limpando recursos Kubernetes..."
    kubectl delete deployment server-deployment --ignore-not-found --wait=false
    kubectl delete service server-service --ignore-not-found --wait=false
    kubectl delete jobs -l app=client --ignore-not-found --wait=false
    echo "Aguardando a remoção dos recursos..."
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

    echo "--- Construindo e enviando imagens para: ${lang_name^^} ---"
    
    echo "Construindo imagem do servidor $lang_name ($server_image)..."
    docker build -t "$server_image" -f "$server_dockerfile" .
    docker push "$server_image" || { echo "ERRO: Falha ao enviar imagem do servidor $lang_name. Verifique o login do Docker."; exit 1; }

    echo "Construindo imagem do cliente $lang_name ($client_image)..."
    docker build -t "$client_image" -f "$client_dockerfile" .
    docker push "$client_image" || { echo "ERRO: Falha ao enviar imagem do cliente $lang_name. Verifique o login do Docker."; exit 1; }
    
    echo "Imagens $lang_name enviadas para o Docker Hub."
}

# Aguarda o deployment do servidor ficar pronto
wait_for_deployment() {
    local deployment_name=$1
    echo "Aguardando o deployment '$deployment_name' estar pronto..."
    if ! kubectl wait --for=condition=Available deployment/"$deployment_name" --timeout=300s; then
        echo "ERRO: O deployment '$deployment_name' não ficou pronto a tempo."
        kubectl describe deployment "$deployment_name"
        kubectl get pods -l app=server
        exit 1
    fi
    echo "Deployment '$deployment_name' pronto."
}

# Executa os testes para uma dada linguagem em uma execução específica
run_tests_for_lang() {
    local lang_name=$1
    local server_image=$2
    local client_image=$3
    local run_number=$4
    local current_run_log_dir="$BASE_LOG_DIR/run_${run_number}"
    local raw_log_subdir="$current_run_log_dir/raw_client_logs/$lang_name"

    mkdir -p "$raw_log_subdir"
    echo "--- Iniciando testes para a linguagem: $lang_name (Execução: $run_number) ---"

    # Aplica o deployment do servidor e o service
    # O service é criado uma vez e aponta para os pods do servidor
    kubectl apply -f server-deployment.yaml
    
    for num_servers in "${SERVER_REPLICAS_ARRAY[@]}"; do
        echo "--- Testando com $num_servers servidor(es) ($lang_name) ---"
        
        # Atualiza a imagem e o número de réplicas do deployment
        kubectl set image deployment/server-deployment server="$server_image"
        kubectl scale deployment/server-deployment --replicas="$num_servers"
        wait_for_deployment server-deployment

        # Salva o status dos pods do servidor
        local server_status_log="$current_run_log_dir/server_status_${lang_name}_${num_servers}s.log"
        echo "Salvando status do servidor em $server_status_log"
        {
            echo "--- STATUS EM $(date) ---"
            kubectl get pods -l app=server -o wide
            echo ""
            kubectl describe deployment server-deployment
        } > "$server_status_log"
        
        for num_concurrent_clients in "${CLIENT_CONCURRENCY_ARRAY[@]}"; do
            for num_messages_per_client in "${MESSAGES_PER_CLIENT_ARRAY[@]}"; do
                local scenario_desc="${lang_name}-${num_servers}s-${num_concurrent_clients}c-${num_messages_per_client}m"
                echo "--- Cenário: $num_concurrent_clients clientes, $num_messages_per_client mensagens ---"
                
                # Limpa Jobs de cliente anteriores para evitar conflitos de nome
                kubectl delete job -l scenario="$scenario_desc" --ignore-not-found --wait=false
                
                local client_job_name="client-job-${scenario_desc}-${run_number}"
                local raw_log_file="$raw_log_subdir/client_raw_log_${scenario_desc}.json"

                # Cria um Job do Kubernetes para o cenário de teste atual
                # Esta é a abordagem correta para garantir testes isolados e reprodutíveis
                cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: $client_job_name
  labels:
    app: client
    scenario: "$scenario_desc"
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 300 # Limpa o Job automaticamente após 5 minutos
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: client
        image: $client_image
        env:
        - name: SERVER_IP
          value: "server-service"
        - name: SERVER_PORT
          value: "8080"
        - name: CLIENT_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: NUM_CONCURRENT_CLIENTS
          value: "$num_concurrent_clients"
        - name: NUM_MESSAGES_PER_CLIENT
          value: "$num_messages_per_client"
EOF
                echo "Aguardando conclusão do Job '$client_job_name'..."
                # Timeout dinâmico
                local timeout_seconds=$(( (num_concurrent_clients * num_messages_per_client) / 10 + 120 ))
                [ $timeout_seconds -gt 600 ] && timeout_seconds=600 # Timeout máximo de 10 min

                if ! kubectl wait --for=condition=complete job/"$client_job_name" --timeout=${timeout_seconds}s; then
                    echo "AVISO: Job '$client_job_name' falhou ou excedeu o timeout."
                    local failed_pod
                    failed_pod=$(kubectl get pods -l job-name="$client_job_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                    [ -n "$failed_pod" ] && kubectl logs "$failed_pod" > "${raw_log_file}.failed"
                else
                    echo "Job '$client_job_name' concluído. Coletando logs."
                    local succeeded_pod
                    succeeded_pod=$(kubectl get pods -l job-name="$client_job_name" -o jsonpath='{.items[?(@.status.phase=="Succeeded")].metadata.name}' 2>/dev/null)
                    [ -n "$succeeded_pod" ] && kubectl logs "$succeeded_pod" > "$raw_log_file"
                fi
            done
        done
    done
    
    # Limpa o deployment do servidor antes de passar para a próxima linguagem
    cleanup_kubernetes
}

# Processa logs brutos e gera um CSV para uma linguagem em uma execução
process_and_generate_csv() {
    local lang_name=$1
    local run_number=$2
    local current_run_log_dir="$BASE_LOG_DIR/run_${run_number}"
    local raw_log_subdir="$current_run_log_dir/raw_client_logs/$lang_name"
    local output_csv="$current_run_log_dir/results_${lang_name}.csv"

    echo "Processando logs de $lang_name para a execução $run_number..."
    python3 process_logs.py "$raw_log_subdir" "$output_csv"
    echo "CSV de $lang_name salvo em $output_csv"
}

# Combina os CSVs de Go e C++ para uma execução
combine_csvs() {
    local run_number=$1
    local current_run_log_dir="$BASE_LOG_DIR/run_${run_number}"
    echo "Combinando CSVs para a execução $run_number..."
    
    local go_csv="$current_run_log_dir/results_go.csv"
    local cpp_csv="$current_run_log_dir/results_cpp.csv"
    local final_csv="$current_run_log_dir/results_combined.csv"

    if [ ! -f "$go_csv" ] || [ ! -f "$cpp_csv" ]; then
        echo "ERRO: CSV de Go ou C++ não encontrado para a execução $run_number."
        return 1
    fi

    # Adiciona a coluna 'language' e combina os arquivos
    awk -v lang="go" 'BEGIN {FS=OFS=","} {if(NR==1) $0=$0",language"; else $0=$0","lang} 1' "$go_csv" > "${go_csv}.tmp"
    awk -v lang="cpp" 'BEGIN {FS=OFS=","} {if(NR==1) $0=$0",language"; else $0=$0","lang} 1' "$cpp_csv" > "${cpp_csv}.tmp"

    head -n 1 "${go_csv}.tmp" > "$final_csv"
    tail -n +2 "${go_csv}.tmp" >> "$final_csv"
    tail -n +2 "${cpp_csv}.tmp" >> "$final_csv"

    rm "${go_csv}.tmp" "${cpp_csv}.tmp"
    echo "Dados combinados salvos em $final_csv"
}

# Gera gráficos para uma execução
generate_graphs() {
    local run_number=$1
    local current_run_log_dir="$BASE_LOG_DIR/run_${run_number}"
    local combined_csv="$current_run_log_dir/results_combined.csv"
    local graph_dir="$current_run_log_dir/graphs"

    if [ ! -f "$combined_csv" ]; then
        echo "AVISO: CSV combinado não encontrado para a execução $run_number. Pulando geração de gráficos."
        return
    fi
    echo "Gerando gráficos para a execução $run_number..."
    python3 generate_graphs.py "$combined_csv" "$graph_dir"
    echo "Gráficos salvos em $graph_dir/"
}

# Analisa os resultados para uma execução
analyze_results() {
    local run_number=$1
    local current_run_log_dir="$BASE_LOG_DIR/run_${run_number}"
    local combined_csv="$current_run_log_dir/results_combined.csv"
    local report_file="$current_run_log_dir/analysis_report.txt"

    if [ ! -f "$combined_csv" ]; then
        echo "AVISO: CSV combinado não encontrado para a execução $run_number. Pulando análise de resultados."
        return
    fi
    echo "Gerando relatório de análise para a execução $run_number..."
    python3 analyze_results.py "$combined_csv" "$report_file"
    echo "Relatório de análise salvo em $report_file"
}

# --- EXECUÇÃO PRINCIPAL ---

# 1. Construir todas as imagens (apenas uma vez)
build_and_push_images_for_lang "go" "$SERVER_IMAGE_GO" "$CLIENT_IMAGE_GO" "$SERVER_DOCKERFILE_GO" "$CLIENT_DOCKERFILE_GO"
build_and_push_images_for_lang "cpp" "$SERVER_IMAGE_CPP" "$CLIENT_IMAGE_CPP" "$SERVER_DOCKERFILE_CPP" "$CLIENT_DOCKERFILE_CPP"

# 2. Laço principal para executar os testes N vezes
for i in $(seq 1 $TOTAL_RUNS); do
    echo ""
    echo "============================================================"
    echo "INICIANDO EXECUÇÃO DE TESTE COMPLETA: $i de $TOTAL_RUNS"
    echo "============================================================"
    
    current_run_log_dir="$BASE_LOG_DIR/run_${i}"
    mkdir -p "$current_run_log_dir"

    # Laço para executar para cada linguagem
    for lang in "go" "cpp"; do
        cleanup_kubernetes # Garante um ambiente limpo

        if [ "$lang" == "go" ]; then
            run_tests_for_lang "go" "$SERVER_IMAGE_GO" "$CLIENT_IMAGE_GO" "$i"
        elif [ "$lang" == "cpp" ]; then
            run_tests_for_lang "cpp" "$SERVER_IMAGE_CPP" "$CLIENT_IMAGE_CPP" "$i"
        fi
        
        process_and_generate_csv "$lang" "$i"
    done

    # Combina os CSVs da execução atual
    combine_csvs "$i"

    echo "--- Execução $i concluída. Resultados em: $current_run_log_dir ---"
done

# 6. Processamento Final (após todas as execuções)
echo ""
echo "============================================================"
echo "PROCESSAMENTO FINAL DE TODOS OS DADOS"
echo "============================================================"

# Passa o diretório base para os scripts de análise e geração de gráficos
final_graph_dir="$BASE_LOG_DIR/final_graphs"
final_report="$BASE_LOG_DIR/final_analysis_report.txt"
echo "Gerando gráficos agregados em $final_graph_dir..."
python3 generate_graphs.py "$BASE_LOG_DIR" "$final_graph_dir"

echo "Gerando relatório de análise agregado em $final_report..."
# Nota: o script analyze_results.py precisaria ser modificado para
# consolidar todos os 'results_combined.csv', similar ao generate_graphs.py,
# ou podemos analisar o último 'run' como exemplo. Para simplificar,
# vamos analisar os resultados combinados da última execução.
last_run_combined_csv="$BASE_LOG_DIR/run_$TOTAL_RUNS/results_combined.csv"
if [ -f "$last_run_combined_csv" ]; then
    python3 analyze_results.py "$last_run_combined_csv" "$final_report"
else
    echo "AVISO: Não foi possível encontrar o CSV combinado da última execução para análise final."
fi


# 7. Limpeza final
cleanup_kubernetes
echo ""
echo "============================================================"
echo "TODOS OS $TOTAL_RUNS CICLOS DE TESTE FORAM CONCLUÍDOS."
echo "Logs e resultados estão no diretório '$BASE_LOG_DIR/'."
echo "Script finalizado."
echo "============================================================"
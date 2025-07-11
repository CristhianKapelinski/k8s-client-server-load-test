# k8s-client-server-load-test

Este projeto automatiza testes de desempenho entre implementações de servidores e clientes TCP em Go e C++ utilizando Kubernetes. O objetivo é comparar o desempenho das duas linguagens em diferentes cenários de carga, coletando métricas, processando resultados e gerando gráficos e relatórios de análise.

## Funcionalidades

- **Build e push automático** das imagens Docker dos servidores e clientes (Go e C++).
- **Execução automatizada** de múltiplos cenários de teste, variando:
    - Número de réplicas do servidor
    - Número de clientes concorrentes
    - Número de mensagens por cliente
- **Orquestração via Kubernetes**: cada cenário é executado como um Job isolado.
- **Coleta de logs** dos clientes para análise posterior.
- **Processamento dos logs** em CSV via Python.
- **Geração de gráficos** e **relatórios de análise** automáticos.
- **Execução repetida** dos testes para maior robustez estatística.
- **Limpeza automática** dos recursos Kubernetes ao final de cada ciclo.

## Pré-requisitos

- Docker e login no Docker Hub
- Kubernetes (kubectl configurado)
- Python 3 (já com todas as dependências necessárias no repositório)
- Permissão para criar e deletar recursos no cluster Kubernetes

## Como usar

1. **Clone o repositório e acesse o diretório:**
     ```bash
     git clone https://github.com/CristhianKapelinski/k8s-client-server-load-test.git
     cd k8s-client-server-load-test/v4
     ```

2. **Edite as configurações se necessário:**
     - Usuário do Docker Hub (`DOCKER_USER`)
     - Parâmetros de teste (réplicas, concorrência, mensagens)

3. **Execute o script principal:**
     ```bash
     ./run_tests.sh [opções]
     ```

     **Parâmetros opcionais:**
     - `-u <docker_user>`: Usuário do Docker Hub
     - `-s <server_replicas>`: Lista de réplicas do servidor (ex: 2,4,6)
     - `-c <client_concurrency>`: Lista de clientes concorrentes (ex: 10,20,30)
     - `-m <messages_per_client>`: Lista de mensagens por cliente (ex: 1,10,100)

     **Exemplo:**
     ```bash
     ./run_tests.sh -u seu_usuario -s 2,4 -c 10,20 -m 1,10
     ```

## Resultados

- Logs, CSVs, gráficos e relatórios são salvos no diretório `logs/`.
- Ao final, gráficos e análises agregadas são gerados automaticamente.

## Estrutura dos Testes

Para cada linguagem (Go e C++), o script:
- Constrói e envia as imagens Docker.
- Executa múltiplos cenários variando réplicas, concorrência e mensagens.
- Coleta e processa os logs dos clientes.
- Gera CSVs, gráficos e relatórios.
- Todos os recursos Kubernetes são limpos entre execuções para garantir isolamento.

## Scripts auxiliares

Todos os scripts necessários já estão presentes no repositório:
- `process_logs.py`: Processa logs brutos dos clientes e gera CSV.
- `generate_graphs.py`: Gera gráficos a partir dos CSVs.
- `analyze_results.py`: Gera relatórios de análise dos resultados.

## Observações

- O script é robusto a falhas e faz timeout automático de jobs problemáticos.
- O ambiente é limpo ao final de cada ciclo e ao término do script.
- Os parâmetros podem ser ajustados conforme a necessidade do experimento.
- **Atenção:** Certifique-se de que seu cluster Kubernetes tem recursos suficientes para os testes e que você está logado no Docker Hub.

## Gráficos Gerados

Os principais gráficos de análise dos testes estão disponíveis abaixo:

- ![Latência vs Clientes (com outliers)](logs/final_graphs/1a_latency_vs_clients_with_outliers.png)
- ![Latência vs Clientes (sem outliers)](logs/final_graphs/1b_latency_vs_clients_no_outliers.png)
- ![Taxa de Sucesso vs Clientes](logs/final_graphs/2_success_rate_vs_clients.png)
- ![Latência vs Réplicas de Servidor (com outliers)](logs/final_graphs/3a_latency_vs_servers_with_outliers.png)
- ![Latência vs Réplicas de Servidor (sem outliers)](logs/final_graphs/3b_latency_vs_servers_no_outliers.png)
- ![Distribuição Geral de Latência](logs/final_graphs/4_overall_latency_distribution.png)
- ![Heatmap de Latência (C++)](logs/final_graphs/5_heatmap_latency_cpp.png)
- ![Heatmap de Latência (Go)](logs/final_graphs/5_heatmap_latency_go.png)
- ![Estabilidade da Latência por Execução - Cenário 1](logs/final_graphs/6a_run_stability_latency_scenario1.png)
- ![Estabilidade da Latência por Execução - Cenário 3](logs/final_graphs/6a_run_stability_latency_scenario3.png)
- ![Estabilidade da Taxa de Sucesso por Execução - Cenário 1](logs/final_graphs/6b_run_stability_success_scenario1.png)
- ![Estabilidade da Taxa de Sucesso por Execução - Cenário 3](logs/final_graphs/6b_run_stability_success_scenario3.png)

---

## Estatísticas Gerais Agrupadas por Linguagem


**Tabela 1 Estatísticas Gerais das 10 execucoes:**

| language | Média Latência (ms) | Desvio Padrão | Mediana | 95% Percentil | Máx | Taxa de Sucesso (%) | Total de Mensagens Recebidas (média) |
|----------|---------------------|---------------|---------|---------------|-----|---------------------|--------------------------------------|
| cpp      | 1.52                | 0.73          | 1.40    | 2.75          | 3.57| 100                 | 106434.17                            |
| go       | 0.95                | 0.44          | 0.97    | 1.64          | 2.32| 100                 | 106434.17                            |


**Tabela 2 Execucao número 10:**

| Linguagem | Média Latência (ms) | Desvio Padrão | Mediana | 95% Percentil | Máx | Taxa de Sucesso (%) | Total de Mensagens Recebidas (média) |
|-----------|--------------------|---------------|---------|---------------|-----|---------------------|--------------------------------------|
| C++       | 0.51               | 0.31          | 0.43    | 1.02          | 2.66| 100                 | 106434.17                            |
| Go        | 0.34               | 0.17          | 0.32    | 0.66          | 1.10| 100                 | 106434.17                            |
---

## Comparação e Interpretação das Tabelas

Ao comparar as duas tabelas, que apresentam estatísticas consolidadas por linguagem, observamos algumas tendências consistentes e algumas diferenças notáveis nos valores das métricas.

**Consistências:**

* **Total de Mensagens Recebidas (média):** Ambas as tabelas mostram que, em média, tanto a implementação C++ quanto a Go processaram o mesmo volume de mensagens: **106.434,17 mensagens**. Isso sugere que a carga de teste aplicada foi a mesma para ambas as linguagens e que o sistema conseguiu processar a carga consistentemente.
* **Hierarquia de Desempenho (C++ vs. Go):** Em ambas as tabelas, a implementação em **Go consistentemente apresenta latências menores** (Média, Mediana, 95% Percentil e Máx) e um desvio padrão menor em comparação com a implementação C++. Isso indica que Go é mais rápido e mais consistente em seu tempo de resposta do que C++.

**Diferenças e Discrepâncias:**

---

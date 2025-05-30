---

# Projeto: Cliente-Servidor TCP/IP em Kubernetes

Este projeto demonstra a **implantação e escalabilidade** de uma aplicação cliente-servidor TCP/IP. Utilizando **Docker** para contêineres e **Kubernetes** para orquestração, o objetivo é simular e analisar o desempenho da aplicação sob variadas cargas de trabalho, ajustando o número de instâncias de servidores e clientes.

---

## 🚀 Como o Projeto Funciona

O projeto é composto por elementos-chave:

* **`server.py`**: Um servidor TCP implementado em Python, responsável por ecoar (enviar de volta) as mensagens recebidas.
* **`client.py`**: Um cliente TCP em Python que se conecta ao servidor, envia uma mensagem e processa a resposta, incluindo lógica de retentativa para conexão.
* **Dockerfiles (`Dockerfile.server`, `Dockerfile.client`)**: Receitas para construir **imagens Docker leves** para o servidor e o cliente, empacotando suas dependências Python.
* **Arquivos YAML do Kubernetes (`server-deployment.yaml`, `client-job.yaml`)**:
    * **`server-deployment.yaml`** define um **Deployment** para gerenciar as réplicas do servidor e um **Service** para expô-las de forma estável, atuando como um balanceador de carga interno.
    * **`client-job.yaml`** define um **Job** para os clientes, garantindo que cada instância execute sua tarefa e finalize.
* **`run_tests.sh`**: Um script Bash que **automatiza todo o ciclo de vida** do projeto, desde a construção das imagens até a execução dos testes de carga no Kubernetes e a coleta de logs.

---

## ✨ Funcionalidades Principais

* **Escalabilidade Flexível**: Testes com 2, 4, 6, 8 e 10 instâncias de servidor.
* **Testes de Carga Automatizados**: Simulação de cargas com 10, 50 e 100 clientes por configuração de servidor.
* **Orquestração Kubernetes**: Implantação e gerenciamento automatizado de pods e serviços.
* **Coleta de Logs Automatizada**: Status de pods e logs de clientes são salvos na pasta `logs/` para análise.
* **Ambiente Contenerizado**: Cada componente opera de forma isolada em seu próprio contêiner Docker.

---

## 🛠️ Pré-requisitos de Instalação

Para executar este projeto, você precisará ter os seguintes componentes instalados:

* **Docker**: Para construção e gerenciamento de imagens de contêiner.
* **Minikube** (ou outro cluster Kubernetes local, como Kind ou Docker Desktop com Kubernetes ativado): Para simular um ambiente Kubernetes.
* **kubectl**: A ferramenta de linha de comando para interação com o cluster Kubernetes.
* **Python 3.x**: Para compatibilidade com os códigos do cliente e servidor.

---

## 🚀 Guia de Execução

1.  **Clonar o Repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <pasta_do_projeto>
    ```

2.  **Configurar Usuário do Docker Hub:**
    Edite o arquivo `run_tests.sh` e defina a variável `DOCKER_USER` com seu nome de usuário do Docker Hub:
    ```bash
    DOCKER_USER="seu_usuario_dockerhub"
    ```

3.  **Realizar Login no Docker Hub:**
    ```bash
    docker login
    ```

4.  **Iniciar o Cluster Kubernetes (Ex: Minikube):**
    ```bash
    minikube start --driver=docker
    ```
    Aguarde a completa inicialização do Minikube.

5.  **Conceder Permissão de Execução ao Script:**
    ```bash
    chmod +x run_tests.sh
    ```

6.  **Executar o Script de Testes:**
    ```bash
    ./run_tests.sh
    ```
    O script automatizará todas as etapas: limpeza de recursos, construção e envio de imagens Docker, implantação de servidores no Kubernetes e execução das cargas de clientes, com os logs salvos na pasta `logs/`.

---

## 📁 Estrutura do Projeto

```
.
├── client.py
├── client-job.yaml
├── Dockerfile.client
├── Dockerfile.server
├── logs/                 # Gerado após a execução do script
├── run_tests.sh
├── server.py
└── server-deployment.yaml
```

---

## 💡 Análise de Capacidade e Escalabilidade

* **Capacidade Observada**: Durante os testes, o servidor atual (implementado com threads) demonstrou ser capaz de suportar efetivamente **pelo menos 100 clientes simultâneos** por ciclo de teste no cluster, com todas as mensagens sendo processadas com sucesso.
* **Próximos Passos para Alta Escala**: Para lidar com volumes substancialmente maiores de clientes (na ordem de centenas ou milhares), será necessário migrar a arquitetura do servidor de sua base em threads para um **modelo de I/O assíncrono e não bloqueante** (e.g., utilizando a biblioteca `asyncio` em Python). Essa alteração é crucial para otimizar o uso de recursos e permitir que o servidor gerencie um número significativamente maior de conexões concorrentes de forma eficiente.

---

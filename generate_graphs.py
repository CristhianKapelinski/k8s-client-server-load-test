# generate_graphs.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

def generate_graphs(input_csv_path, output_dir):
    if not os.path.exists(input_csv_path):
        print(f"Erro: Arquivo CSV não encontrado em {input_csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(input_csv_path)

    if df.empty:
        print("O DataFrame está vazio. Não há dados para gerar gráficos.", file=sys.stderr)
        return

    os.makedirs(output_dir, exist_ok=True)

    # Convert numeric columns to appropriate types in case they were read as objects
    numeric_cols = [
        'server_replicas', 
        'num_concurrent_clients_scenario', 
        'num_messages_per_client_scenario',
        'total_connections_attempted', 
        'successful_connections', 
        'total_messages_sent',
        'total_messages_received', 
        'average_latency_ms', 
        'max_latency_ms',
        'min_latency_ms', 
        'total_errors', 
        'scenario_success_rate'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.dropna(subset=numeric_cols, inplace=True) # Drop rows where essential numeric data is missing

    if df.empty:
        print("O DataFrame está vazio após a limpeza de dados. Não há dados válidos para gerar gráficos.", file=sys.stderr)
        return

    print(f"DataFrame carregado com {len(df)} linhas para geração de gráficos.")
    print("Colunas do DataFrame:", df.columns.tolist())

    # --- Gráfico 1: Latência Média vs. Clientes Concorrentes (por número de servidores e mensagens) ---
    plt.figure(figsize=(15, 8))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='average_latency_ms', 
                 hue='server_replicas', 
                 style='num_messages_per_client_scenario', 
                 marker='o',
                 palette='viridis')
    plt.title('Latência Média por Mensagem vs. Clientes Concorrentes')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Latência Média por Mensagem (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Configuração', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'average_latency_vs_concurrent_clients.png'))
    plt.close()
    print("Gráfico 'average_latency_vs_concurrent_clients.png' gerado.")

    # --- Gráfico 2: Taxa de Sucesso do Cenário vs. Clientes Concorrentes (por número de servidores e mensagens) ---
    plt.figure(figsize=(15, 8))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='scenario_success_rate', 
                 hue='server_replicas', 
                 style='num_messages_per_client_scenario', 
                 marker='o',
                 palette='plasma')
    plt.title('Taxa de Sucesso do Cenário vs. Clientes Concorrentes')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Taxa de Sucesso do Cenário (Mensagens Recebidas / Mensagens Enviadas)')
    plt.ylim(0, 1.05) # Ensure y-axis is between 0 and 1
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Configuração', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'success_rate_vs_concurrent_clients.png'))
    plt.close()
    print("Gráfico 'success_rate_vs_concurrent_clients.png' gerado.")

    # --- Gráfico 3: Total de Mensagens Processadas vs. Clientes Concorrentes (por número de servidores e mensagens) ---
    plt.figure(figsize=(15, 8))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='total_messages_received', 
                 hue='server_replicas', 
                 style='num_messages_per_client_scenario', 
                 marker='o',
                 palette='cividis')
    plt.title('Total de Mensagens Recebidas vs. Clientes Concorrentes')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Total de Mensagens Recebidas')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Configuração', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'total_messages_received_vs_concurrent_clients.png'))
    plt.close()
    print("Gráfico 'total_messages_received_vs_concurrent_clients.png' gerado.")

    # --- Gráfico 4: Latência Média por Servidor (comparando diferentes nº de servidores) ---
    plt.figure(figsize=(15, 8))
    sns.barplot(data=df, 
                x='server_replicas', 
                y='average_latency_ms', 
                hue='num_concurrent_clients_scenario', 
                palette='viridis',
                errorbar='sd') # Show standard deviation
    plt.title('Latência Média por Mensagem vs. Número de Réplicas do Servidor')
    plt.xlabel('Número de Réplicas do Servidor')
    plt.ylabel('Latência Média por Mensagem (ms)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Clientes Concorrentes', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'average_latency_vs_server_replicas.png'))
    plt.close()
    print("Gráfico 'average_latency_vs_server_replicas.png' gerado.")
    
    # --- Gráfico 5: Taxa de Sucesso por Servidor (comparando diferentes nº de servidores) ---
    plt.figure(figsize=(15, 8))
    sns.barplot(data=df, 
                x='server_replicas', 
                y='scenario_success_rate', 
                hue='num_concurrent_clients_scenario', 
                palette='plasma',
                errorbar='sd')
    plt.title('Taxa de Sucesso do Cenário vs. Número de Réplicas do Servidor')
    plt.xlabel('Número de Réplicas do Servidor')
    plt.ylabel('Taxa de Sucesso do Cenário')
    plt.ylim(0, 1.05)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Clientes Concorrentes', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'success_rate_vs_server_replicas.png'))
    plt.close()
    print("Gráfico 'success_rate_vs_server_replicas.png' gerado.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 generate_graphs.py <input_csv_path> <output_graphs_dir>")
        sys.exit(1)
    
    input_csv_path = sys.argv[1]
    output_graphs_dir = sys.argv[2]
    
    generate_graphs(input_csv_path, output_graphs_dir)
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

    # --- Gráfico 1: Latência Média vs. Clientes Concorrentes (por número de servidores, mensagens e LINGUAGEM) ---
    plt.figure(figsize=(18, 9))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='average_latency_ms', 
                 hue='language', # Adiciona a comparação por linguagem
                 style='server_replicas', 
                 markers=True,
                 palette='tab10') # Usar uma paleta que diferencia bem
    plt.title('Latência Média por Mensagem vs. Clientes Concorrentes (Comparação Python vs Go)')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Latência Média por Mensagem (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem | Servidores', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'average_latency_vs_concurrent_clients_language_comparison.png'))
    plt.close()
    print("Gráfico 'average_latency_vs_concurrent_clients_language_comparison.png' gerado.")

    # --- Gráfico 2: Taxa de Sucesso do Cenário vs. Clientes Concorrentes (por número de servidores, mensagens e LINGUAGEM) ---
    plt.figure(figsize=(18, 9))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='scenario_success_rate', 
                 hue='language', # Adiciona a comparação por linguagem
                 style='server_replicas', 
                 markers=True,
                 palette='Dark2')
    plt.title('Taxa de Sucesso do Cenário vs. Clientes Concorrentes (Comparação Python vs Go)')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Taxa de Sucesso do Cenário (Mensagens Recebidas / Mensagens Enviadas)')
    plt.ylim(0, 1.05) # Ensure y-axis is between 0 and 1
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem | Servidores', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'success_rate_vs_concurrent_clients_language_comparison.png'))
    plt.close()
    print("Gráfico 'success_rate_vs_concurrent_clients_language_comparison.png' gerado.")

    # --- Gráfico 3: Total de Mensagens Processadas vs. Clientes Concorrentes (por número de servidores, mensagens e LINGUAGEM) ---
    plt.figure(figsize=(18, 9))
    sns.lineplot(data=df, 
                 x='num_concurrent_clients_scenario', 
                 y='total_messages_received', 
                 hue='language', # Adiciona a comparação por linguagem
                 style='server_replicas', 
                 markers=True,
                 palette='Spectral')
    plt.title('Total de Mensagens Recebidas vs. Clientes Concorrentes (Comparação Python vs Go)')
    plt.xlabel('Número de Clientes Concorrentes por Pod')
    plt.ylabel('Total de Mensagens Recebidas')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem | Servidores', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'total_messages_received_vs_concurrent_clients_language_comparison.png'))
    plt.close()
    print("Gráfico 'total_messages_received_vs_concurrent_clients_language_comparison.png' gerado.")

    # --- Gráfico 4: Latência Média por Servidor (comparando diferentes nº de servidores e LINGUAGEM) ---
    plt.figure(figsize=(18, 9))
    sns.barplot(data=df, 
                x='server_replicas', 
                y='average_latency_ms', 
                hue='language', # Adiciona a comparação por linguagem
                palette='viridis',
                errorbar='sd') # Show standard deviation
    plt.title('Latência Média por Mensagem vs. Número de Réplicas do Servidor (Comparação Python vs Go)')
    plt.xlabel('Número de Réplicas do Servidor')
    plt.ylabel('Latência Média por Mensagem (ms)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'average_latency_vs_server_replicas_language_comparison.png'))
    plt.close()
    print("Gráfico 'average_latency_vs_server_replicas_language_comparison.png' gerado.")
    
    # --- Gráfico 5: Taxa de Sucesso por Servidor (comparando diferentes nº de servidores e LINGUAGEM) ---
    plt.figure(figsize=(18, 9))
    sns.barplot(data=df, 
                x='server_replicas', 
                y='scenario_success_rate', 
                hue='language', # Adiciona a comparação por linguagem
                palette='plasma',
                errorbar='sd')
    plt.title('Taxa de Sucesso do Cenário vs. Número de Réplicas do Servidor (Comparação Python vs Go)')
    plt.xlabel('Número de Réplicas do Servidor')
    plt.ylabel('Taxa de Sucesso do Cenário')
    plt.ylim(0, 1.05)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'success_rate_vs_server_replicas_language_comparison.png'))
    plt.close()
    print("Gráfico 'success_rate_vs_server_replicas_language_comparison.png' gerado.")

    # Adicionar gráficos específicos para latência (min/max/avg) com base na linguagem, agrupando por cenário
    # Isso pode ser feito adicionando mais gráficos ou ajustando os existentes.
    # Exemplo de gráfico de dispersão para Latência Média por Linguagem, por cenário completo
    plt.figure(figsize=(18, 9))
    sns.scatterplot(data=df, 
                    x='total_messages_received', 
                    y='average_latency_ms', 
                    hue='language', 
                    size='num_concurrent_clients_scenario', 
                    sizes=(50, 500), 
                    alpha=0.7,
                    palette='coolwarm')
    plt.title('Latência Média vs. Mensagens Recebidas (por Cenário e Linguagem)')
    plt.xlabel('Total de Mensagens Recebidas')
    plt.ylabel('Latência Média por Mensagem (ms)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem | Clientes Concorrentes', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'latency_vs_messages_language_scatter.png'))
    plt.close()
    print("Gráfico 'latency_vs_messages_language_scatter.png' gerado.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 generate_graphs.py <input_csv_path> <output_graphs_dir>")
        sys.exit(1)
    
    input_csv_path = sys.argv[1]
    output_graphs_dir = sys.argv[2]
    
    generate_graphs(input_csv_path, output_graphs_dir)
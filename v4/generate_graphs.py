# generate_graphs.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from glob import glob
import numpy as np

def load_all_data(base_dir):
    """
    Carrega e concatena todos os arquivos 'results_combined.csv' de todos os subdiretórios 'run_*'.
    """
    all_csv_files = glob(os.path.join(base_dir, 'run_*', 'results_combined.csv'))
    if not all_csv_files:
        print(f"Erro: Nenhum arquivo 'results_combined.csv' encontrado em subdiretórios 'run_*' de '{base_dir}'", file=sys.stderr)
        sys.exit(1)
    
    print(f"Encontrados {len(all_csv_files)} arquivos de resultado. Carregando...")
    df_list = [pd.read_csv(f) for f in all_csv_files]
    full_df = pd.concat(df_list, ignore_index=True)
    
    numeric_cols = ['run_number', 'server_replicas', 'num_concurrent_clients_scenario', 'average_latency_ms', 'scenario_success_rate', 'total_messages_received']
    for col in numeric_cols:
        if col in full_df.columns:
            full_df[col] = pd.to_numeric(full_df[col], errors='coerce')
    full_df.dropna(subset=numeric_cols, inplace=True)
    
    print(f"Dados carregados com sucesso. Total de {len(full_df)} cenários analisados (contando todas as execuções).")
    return full_df

def remove_outliers(df, metric_col, group_cols):
    """
    Remove outliers de uma coluna de métrica com base no método IQR (Interquartile Range).
    """
    q1 = df.groupby(group_cols)[metric_col].transform('quantile', 0.25)
    q3 = df.groupby(group_cols)[metric_col].transform('quantile', 0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    return df[(df[metric_col] >= lower_bound) & (df[metric_col] <= upper_bound)]

def generate_all_graphs(df, output_dir):
    """
    Gera um conjunto abrangente de gráficos a partir do DataFrame consolidado.
    """
    os.makedirs(output_dir, exist_ok=True)
    lang_palette = {"go": "#00ADD8", "cpp": "#f34b7d"}

    # --- 1. Análise de Latência vs. Carga de Clientes (Distribuição) ---
    print("Gerando gráficos (1/6): Latência vs. Carga de Clientes...")
    df_no_outliers_latency = remove_outliers(df, 'average_latency_ms', ['num_concurrent_clients_scenario', 'language'])
    
    # Com Outliers
    plt.figure(figsize=(20, 10))
    sns.boxplot(data=df, x='num_concurrent_clients_scenario', y='average_latency_ms', hue='language', palette=lang_palette)
    plt.title('Distribuição da Latência Média vs. Clientes Concorrentes (Com Outliers)', fontsize=16)
    plt.xlabel('Número de Clientes Concorrentes', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.yscale('log')
    plt.legend(title='Linguagem'); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '1a_latency_vs_clients_with_outliers.png')); plt.close()

    # Sem Outliers
    plt.figure(figsize=(20, 10))
    sns.boxplot(data=df_no_outliers_latency, x='num_concurrent_clients_scenario', y='average_latency_ms', hue='language', palette=lang_palette)
    plt.title('Distribuição da Latência Média vs. Clientes Concorrentes (Sem Outliers)', fontsize=16)
    plt.xlabel('Número de Clientes Concorrentes', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '1b_latency_vs_clients_no_outliers.png')); plt.close()

    # --- 2. Análise da Taxa de Sucesso vs. Carga de Clientes ---
    print("Gerando gráficos (2/6): Taxa de Sucesso vs. Carga de Clientes...")
    plt.figure(figsize=(20, 10))
    sns.boxplot(data=df, x='num_concurrent_clients_scenario', y='scenario_success_rate', hue='language', palette=lang_palette)
    plt.title('Distribuição da Taxa de Sucesso vs. Clientes Concorrentes', fontsize=16)
    plt.xlabel('Número de Clientes Concorrentes', fontsize=12); plt.ylabel('Taxa de Sucesso (%)', fontsize=12)
    plt.ylim(bottom=-5); plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Linguagem'); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '2_success_rate_vs_clients.png')); plt.close()

    # --- 3. Análise de Desempenho vs. Escalabilidade do Servidor ---
    print("Gerando gráficos (3/6): Desempenho vs. Réplicas do Servidor...")
    df_no_outliers_servers = remove_outliers(df, 'average_latency_ms', ['server_replicas', 'language'])
    
    # Com Outliers
    plt.figure(figsize=(20, 10))
    sns.boxplot(data=df, x='server_replicas', y='average_latency_ms', hue='language', palette=lang_palette)
    plt.title('Distribuição da Latência Média vs. Réplicas do Servidor (Com Outliers)', fontsize=16)
    plt.xlabel('Número de Réplicas do Servidor', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.yscale('log')
    plt.legend(title='Linguagem'); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '3a_latency_vs_servers_with_outliers.png')); plt.close()

    # Sem Outliers
    plt.figure(figsize=(20, 10))
    sns.boxplot(data=df_no_outliers_servers, x='server_replicas', y='average_latency_ms', hue='language', palette=lang_palette)
    plt.title('Distribuição da Latência Média vs. Réplicas do Servidor (Sem Outliers)', fontsize=16)
    plt.xlabel('Número de Réplicas do Servidor', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '3b_latency_vs_servers_no_outliers.png')); plt.close()
    
    # --- 4. Comparação Geral de Performance (Go vs. C++) ---
    print("Gerando gráficos (4/6): Comparação Geral de Performance...")
    plt.figure(figsize=(12, 8))
    sns.violinplot(data=df_no_outliers_latency, x='language', y='average_latency_ms', palette=lang_palette)
    plt.title('Distribuição Geral da Latência por Linguagem (Sem Outliers)', fontsize=16)
    plt.xlabel('Linguagem', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '4_overall_latency_distribution.png')); plt.close()

    # --- 5. Heatmaps de Performance ---
    print("Gerando gráficos (5/6): Heatmaps de Performance...")
    for lang in df['language'].unique():
        plt.figure(figsize=(14, 10))
        heatmap_data = df[df['language'] == lang].pivot_table(index='server_replicas', columns='num_concurrent_clients_scenario', values='average_latency_ms', aggfunc='mean')
        sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="viridis_r", linewidths=.5)
        plt.title(f'Heatmap de Latência Média (ms) para {lang.upper()}', fontsize=16)
        plt.xlabel('Número de Clientes Concorrentes', fontsize=12); plt.ylabel('Número de Réplicas do Servidor', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'5_heatmap_latency_{lang}.png')); plt.close()
        
    # --- 6. NOVO: Análise de Estabilidade Execução-a-Execução ---
    print("Gerando gráficos (6/6): Análise de Estabilidade Execução-a-Execução...")

    # Selecione alguns cenários chave para essa análise detalhada. Pode customizar esta lista.
    key_scenarios = [
        {'server_replicas': 4, 'num_concurrent_clients_scenario': 100, 'num_messages_per_client_scenario': 100},
        {'server_replicas': 8, 'num_concurrent_clients_scenario': 1000, 'num_messages_per_client_scenario': 10},
        {'server_replicas': 10, 'num_concurrent_clients_scenario': 50, 'num_messages_per_client_scenario': 1000}
    ]

    for i, scenario in enumerate(key_scenarios):
        scenario_df = df[
            (df['server_replicas'] == scenario['server_replicas']) &
            (df['num_concurrent_clients_scenario'] == scenario['num_concurrent_clients_scenario']) &
            (df['num_messages_per_client_scenario'] == scenario['num_messages_per_client_scenario'])
        ].copy()

        if scenario_df.empty:
            print(f"Aviso: Nenhum dado encontrado para o cenário chave: {scenario}. Pulando gráfico.")
            continue
        
        # Garante que 'run_number' é tratado como categoria para o plot não tentar interpolar
        scenario_df['run_number'] = scenario_df['run_number'].astype('category')
        
        # Gráfico para Latência
        plt.figure(figsize=(16, 8))
        sns.pointplot(data=scenario_df, x='run_number', y='average_latency_ms', hue='language', palette=lang_palette, markers='o', linestyles='-')
        title_str = (f"Latência Execução-a-Execução (Cenário Chave {i+1})\n"
                     f"({scenario['server_replicas']} Servidores, {scenario['num_concurrent_clients_scenario']} Clientes, "
                     f"{scenario['num_messages_per_client_scenario']} Mensagens)")
        plt.title(title_str, fontsize=16)
        plt.xlabel('Número da Execução (Run)', fontsize=12); plt.ylabel('Latência Média (ms)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        filename = f"6a_run_stability_latency_scenario{i+1}.png"
        plt.savefig(os.path.join(output_dir, filename)); plt.close()
        
        # Gráfico para Taxa de Sucesso
        plt.figure(figsize=(16, 8))
        sns.pointplot(data=scenario_df, x='run_number', y='scenario_success_rate', hue='language', palette=lang_palette, markers='X', linestyles='--')
        title_str = (f"Taxa de Sucesso Execução-a-Execução (Cenário Chave {i+1})\n"
                     f"({scenario['server_replicas']} Servidores, {scenario['num_concurrent_clients_scenario']} Clientes, "
                     f"{scenario['num_messages_per_client_scenario']} Mensagens)")
        plt.title(title_str, fontsize=16)
        plt.xlabel('Número da Execução (Run)', fontsize=12); plt.ylabel('Taxa de Sucesso (%)', fontsize=12)
        plt.ylim(50, 105) # Foco na faixa de sucesso alta
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        filename = f"6b_run_stability_success_scenario{i+1}.png"
        plt.savefig(os.path.join(output_dir, filename)); plt.close()

    print("\n--- Geração de gráficos concluída! ---")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 generate_graphs.py <base_logs_dir> <output_graphs_dir>", file=sys.stderr)
        print("Ex: python3 generate_graphs.py logs logs/final_graphs", file=sys.stderr)
        sys.exit(1)
    
    base_logs_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    full_dataframe = load_all_data(base_logs_dir)
    if not full_dataframe.empty:
        generate_all_graphs(full_dataframe, output_dir)
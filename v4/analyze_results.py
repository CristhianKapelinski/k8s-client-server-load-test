# analyze_results.py
import pandas as pd
import sys
import os
import re

def generate_statistics(input_csv_path, output_report_path=None):
    if not os.path.exists(input_csv_path):
        print(f"Erro: Arquivo CSV não encontrado em {input_csv_path}", file=sys.stderr)
        sys.exit(1)
    
    # Extrai o número da execução do caminho do arquivo para usar no título
    run_number = 0
    run_match = re.search(r'run_(\d+)', input_csv_path)
    if run_match:
        run_number = int(run_match.group(1))

    try:
        df = pd.read_csv(input_csv_path)
    except pd.errors.EmptyDataError:
        print(f"Aviso: O arquivo {input_csv_path} está vazio. Nenhuma estatística para gerar.", file=sys.stderr)
        return
    
    if df.empty:
        print("O DataFrame está vazio. Nenhuma estatística para gerar.", file=sys.stderr)
        return

    # Garante que as colunas numéricas estão com o tipo correto
    numeric_cols = [
        'server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario',
        'total_connections_attempted', 'successful_connections', 'total_messages_sent',
        'total_messages_received', 'average_latency_ms', 'max_latency_ms', 'min_latency_ms',
        'total_errors', 'scenario_success_rate'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=numeric_cols, inplace=True)

    if df.empty:
        print("O DataFrame está vazio após a limpeza. Nenhuma estatística para gerar.", file=sys.stderr)
        return

    report_lines = []
    report_lines.append(f"--- Relatório de Estatísticas da Execução: {run_number} ---")
    report_lines.append(f"Dados analisados de: {os.path.basename(input_csv_path)}\n")

    group_cols = ['language', 'server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']
    metrics_of_interest = ['average_latency_ms', 'scenario_success_rate', 'total_messages_received']
    
    # Filtra apenas as métricas que realmente existem no DataFrame
    metrics_of_interest = [m for m in metrics_of_interest if m in df.columns]

    if not metrics_of_interest:
        print("Erro: Nenhuma das métricas de interesse encontradas no CSV.", file=sys.stderr)
        return

    # Estatísticas por cenário detalhado
    grouped_stats = df.groupby(group_cols)[metrics_of_interest].describe(percentiles=[.50, .95]).round(2)
    report_lines.append("Estatísticas por Cenário (Linguagem, Servidores, Clientes, Mensagens):\n")
    report_lines.append(grouped_stats.to_string())
    report_lines.append("\n" + "="*80 + "\n")

    # Estatísticas gerais por linguagem
    if 'language' in df.columns and df['language'].nunique() > 1:
        report_lines.append("\nEstatísticas Gerais Agrupadas por Linguagem:\n")
        lang_stats = df.groupby('language')[metrics_of_interest].describe(percentiles=[.50, .95]).round(2)
        report_lines.append(lang_stats.to_string())
        report_lines.append("\n" + "="*80 + "\n")

    # Salva ou imprime o relatório
    report_content = "\n".join(report_lines)
    if output_report_path:
        with open(output_report_path, 'w') as f:
            f.write(report_content)
        print(f"Relatório da execução {run_number} salvo em: {output_report_path}")
    else:
        print(report_content)

if __name__ == "__main__":
    if len(sys.argv) not in [2, 3]:
        print("Uso: python3 analyze_results.py <input_combined_csv_path> [output_report_path]", file=sys.stderr)
        sys.exit(1)
    
    generate_statistics(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
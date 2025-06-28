# analyze_results.py
import pandas as pd
import sys
import os

def generate_statistics(input_csv_path, output_report_path=None):
    """
    Gera estatísticas descritivas a partir do CSV combinado dos resultados dos testes.

    Args:
        input_csv_path (str): Caminho para o arquivo CSV combinado (ex: logs/results_combined.csv).
        output_report_path (str, optional): Caminho para salvar o relatório de estatísticas. 
                                            Se None, imprime no console.
    """
    if not os.path.exists(input_csv_path):
        print(f"Erro: Arquivo CSV não encontrado em {input_csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(input_csv_path)
    except pd.errors.EmptyDataError:
        print(f"Aviso: O arquivo {input_csv_path} está vazio. Nenhuma estatística para gerar.", file=sys.stderr)
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV {input_csv_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if df.empty:
        print("O DataFrame está vazio após a leitura. Nenhuma estatística para gerar.", file=sys.stderr)
        return

    # Garantir que as colunas numéricas estão com o tipo correto
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
    
    # Remover linhas com valores NaN que podem ter surgido na conversão
    df.dropna(subset=numeric_cols, inplace=True)

    if df.empty:
        print("O DataFrame está vazio após a limpeza de dados. Nenhuma estatística válida para gerar.", file=sys.stderr)
        return

    report_lines = []
    report_lines.append("--- Relatório de Estatísticas Descritivas dos Testes ---")
    report_lines.append(f"Dados analisados de: {input_csv_path}\n")

    # Agrupar por linguagem, réplicas do servidor, clientes concorrentes e mensagens por cliente
    group_cols = ['language', 'server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']
    
    # Verificar se a coluna 'language' existe antes de agrupar por ela
    if 'language' not in df.columns:
        print("Aviso: Coluna 'language' não encontrada no CSV. As estatísticas não serão agrupadas por linguagem.", file=sys.stderr)
        group_cols = ['server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']
    elif 'language' in df.columns and df['language'].nunique() <= 1:
        print(f"Aviso: Coluna 'language' encontrada, mas contém apenas {df['language'].nunique()} valor(es) único(s). Agrupando sem distinção de linguagem.", file=sys.stderr)
        group_cols = ['server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']

    # Métricas para as quais queremos estatísticas
    metrics_of_interest = [
        'average_latency_ms',
        'scenario_success_rate',
        'total_messages_received',
        'total_connections_attempted'
    ]
    
    # Filtrar apenas as métricas que realmente existem no DataFrame
    metrics_of_interest = [m for m in metrics_of_interest if m in df.columns]

    if not metrics_of_interest:
        print("Erro: Nenhuma das métricas de interesse encontradas no CSV para análise.", file=sys.stderr)
        return

    grouped_stats = df.groupby(group_cols)[metrics_of_interest].describe(percentiles=[.50]).round(2)

    report_lines.append("Estatísticas por Cenário (Linguagem, Servidores, Clientes Concorrentes, Mensagens por Cliente):\n")
    report_lines.append(grouped_stats.to_string())
    report_lines.append("\n" + "="*80 + "\n")

    # Estatísticas gerais por linguagem (se aplicável)
    if 'language' in df.columns and df['language'].nunique() > 1:
        report_lines.append("\nEstatísticas Gerais Agrupadas por Linguagem:\n")
        general_lang_stats = df.groupby('language')[metrics_of_interest].describe(percentiles=[.50]).round(2)
        report_lines.append(general_lang_stats.to_string())
        report_lines.append("\n" + "="*80 + "\n")

    # Estatísticas gerais consolidadas
    report_lines.append("\nEstatísticas Gerais Consolidadas (Todos os Cenários):\n")
    overall_stats = df[metrics_of_interest].describe(percentiles=[.50]).round(2)
    report_lines.append(overall_stats.to_string())
    report_lines.append("\n" + "="*80 + "\n")

    # Salvar ou imprimir
    if output_report_path:
        with open(output_report_path, 'w') as f:
            f.write("\n".join(report_lines))
        print(f"Relatório de estatísticas salvo em: {output_report_path}")
    else:
        print("\n".join(report_lines))

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Uso: python3 analyze_results.py <input_combined_csv_path> [output_report_path]", file=sys.stderr)
        print("Ex: python3 analyze_results.py logs/results_combined.csv", file=sys.stderr)
        print("Ex: python3 analyze_results.py logs/results_combined.csv logs/analysis_report.txt", file=sys.stderr)
        sys.exit(1)

    input_csv = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) == 3 else None
    
    generate_statistics(input_csv, output_file)
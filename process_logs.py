# process_logs.py (Versão Robusta com Regex)
import os
import sys
import json
import pandas as pd
import re

def process_raw_logs(input_dir, output_csv_path):
    all_data = []
    run_match = re.search(r'run_(\d+)', input_dir)
    run_number = int(run_match.group(1)) if run_match else 0
    
    if not os.path.isdir(input_dir):
        print(f"Aviso: Diretório de logs brutos não encontrado: {input_dir}", file=sys.stderr)
        pd.DataFrame().to_csv(output_csv_path, index=False)
        return

    # Regex para extrair parâmetros do nome do arquivo de forma robusta
    # Ex: client_raw_log_go-2s-10c-100m.json
    log_file_pattern = re.compile(
        r"client_raw_log_"
        r"(?P<lang>[a-z]+)-"
        r"(?P<servers>\d+)s-"
        r"(?P<clients>\d+)c-"
        r"(?P<messages>\d+)m"
        r"\.json$"
    )

    for filename in os.listdir(input_dir):
        match = log_file_pattern.match(filename)
        # Se o nome do arquivo não corresponder ao padrão, pula para o próximo
        if not match:
            if filename.endswith(".json"): # Informa apenas sobre arquivos que poderiam ser logs
                 print(f"Aviso: Pulando arquivo com nome fora do padrão esperado: {filename}", file=sys.stderr)
            continue
        
        params = match.groupdict()
        filepath = os.path.join(input_dir, filename)
        
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    if not line.strip().startswith('{'): continue
                    
                    log_entry = json.loads(line.strip())
                    
                    log_entry["run_number"] = run_number
                    log_entry["server_replicas"] = int(params['servers'])
                    log_entry["num_concurrent_clients_scenario"] = int(params['clients'])
                    log_entry["num_messages_per_client_scenario"] = int(params['messages'])
                    
                    all_data.append(log_entry)
                except json.JSONDecodeError:
                    # Este aviso é útil para saber se um arquivo de log está corrompido
                    print(f"Aviso: Pulando linha com JSON mal formatado em {filename}", file=sys.stderr)
    
    if not all_data:
        print(f"Aviso: Nenhum dado de log válido encontrado em {input_dir}", file=sys.stderr)
        pd.DataFrame().to_csv(output_csv_path, index=False)
        return

    df = pd.DataFrame(all_data)
    group_cols = ['run_number', 'language', 'server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']
    
    # Adiciona a coluna 'language' ao DataFrame para agrupamento correto
    df['language'] = df['client_full_id'].apply(lambda x: x.split('-')[2] if len(x.split('-')) > 2 else 'unknown')

    aggregated_df = df.groupby(group_cols).agg(
        total_connections_attempted=('client_full_id', 'count'),
        successful_connections=('connection_success', lambda x: x.astype(bool).sum()),
        total_messages_sent=('messages_sent', 'sum'),
        total_messages_received=('messages_received', 'sum'),
        average_latency_ms=('average_latency_ms', 'mean'),
        max_latency_ms=('average_latency_ms', 'max'),
        min_latency_ms=('average_latency_ms', 'min'),
        total_errors=('errors', lambda x: sum(len(e) for e in x if isinstance(e, list))),
        total_latency_sum_ms=('total_latency_ms', 'sum')
    ).reset_index()

    aggregated_df['scenario_success_rate'] = aggregated_df.apply(
        lambda row: (row['total_messages_received'] / row['total_messages_sent']) * 100 if row['total_messages_sent'] > 0 else 0,
        axis=1
    )
    
    aggregated_df.to_csv(output_csv_path, index=False)
    print(f"Dados processados da execução {run_number} salvos em {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 process_logs.py <input_raw_log_dir> <output_csv_path>", file=sys.stderr)
        sys.exit(1)
    
    process_raw_logs(sys.argv[1], sys.argv[2])
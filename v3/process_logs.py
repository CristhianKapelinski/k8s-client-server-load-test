# process_logs.py
import os
import sys
import json
import pandas as pd

def process_raw_logs(input_dir, output_csv_path):
    all_data = []
    # Verifica se o diretório de entrada existe
    if not os.path.exists(input_dir):
        print(f"Erro: Diretório de logs brutos não encontrado em {input_dir}", file=sys.stderr)
        # Cria um DataFrame vazio para evitar erro na próxima etapa
        pd.DataFrame().to_csv(output_csv_path, index=False)
        return

    for filename in os.listdir(input_dir):
        if filename.startswith("client_raw_log_") and filename.endswith(".log"):
            filepath = os.path.join(input_dir, filename)
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # Extract parameters from filename if not directly in log (for scenario identification)
                        # Example filename: client_raw_log_2s_10c_1m.log
                        parts = filename.replace(".log", "").split('_')
                        server_replicas = int(parts[3].replace('s', ''))
                        num_concurrent_clients = int(parts[4].replace('c', ''))
                        num_messages_per_client = int(parts[5].replace('m', ''))

                        log_entry["server_replicas"] = server_replicas
                        log_entry["num_concurrent_clients_scenario"] = num_concurrent_clients # The value from the scenario
                        log_entry["num_messages_per_client_scenario"] = num_messages_per_client # The value from the scenario
                        
                        all_data.append(log_entry)
                    except json.JSONDecodeError:
                        print(f"Skipping malformed JSON line in {filename}: {line.strip()}", file=sys.stderr)
                    except IndexError:
                        print(f"Skipping log file with unexpected name format: {filename}", file=sys.stderr)
    
    if not all_data:
        print(f"No valid log data found to process in {input_dir}. Creating empty CSV.", file=sys.stderr)
        # Cria um DataFrame vazio e salva para evitar erros downstream
        pd.DataFrame(columns=['server_replicas', 'num_concurrent_clients_scenario', 
                              'num_messages_per_client_scenario', 'total_connections_attempted', 
                              'successful_connections', 'total_messages_sent', 'total_messages_received', 
                              'average_latency_ms', 'max_latency_ms', 'min_latency_ms', 'total_errors', 
                              'total_latency_sum_ms', 'scenario_success_rate']).to_csv(output_csv_path, index=False)
        return

    df = pd.DataFrame(all_data)
    
    # Calculate success rate for each client instance
    df['success_rate_per_instance'] = df['messages_received'] / df['messages_sent']
    
    # Calculate overall average latency only for successful messages (if needed, but aggregated mean is used below)
    # df_successful_messages = df[df['messages_received'] > 0]
    
    # Aggregate data by scenario (server_replicas, num_concurrent_clients_scenario, num_messages_per_client_scenario)
    # This aggregates the performance of all individual client instances within a scenario
    aggregated_df = df.groupby(['server_replicas', 'num_concurrent_clients_scenario', 'num_messages_per_client_scenario']).agg(
        total_connections_attempted=('client_full_id', 'count'),
        successful_connections=('connection_success', lambda x: x.sum()),
        total_messages_sent=('messages_sent', 'sum'),
        total_messages_received=('messages_received', 'sum'),
        average_latency_ms=('average_latency_ms', 'mean'), # Average of averages
        max_latency_ms=('average_latency_ms', 'max'),
        min_latency_ms=('average_latency_ms', 'min'),
        total_errors=('errors', lambda x: sum(len(err_list) for err_list in x)),
        total_latency_sum_ms=('total_latency_ms', 'sum') # Sum of total latencies
    ).reset_index()

    # Calculate overall success rate for the scenario
    # Handle division by zero if total_messages_sent is 0
    aggregated_df['scenario_success_rate'] = aggregated_df.apply(
        lambda row: row['total_messages_received'] / row['total_messages_sent'] if row['total_messages_sent'] > 0 else 0,
        axis=1
    )
    
    aggregated_df.to_csv(output_csv_path, index=False)
    print(f"Processed data saved to {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 process_logs.py <input_raw_log_dir> <output_csv_path>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_csv_path = sys.argv[2]
    
    process_raw_logs(input_dir, output_csv_path)
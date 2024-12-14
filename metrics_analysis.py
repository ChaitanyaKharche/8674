import pandas as pd
import json

def blocking_metric(course):
    # Correct column name to 'Credit Hours'
    return len(course['Prerequisites'].split(',')) * 2 + int(course['Credit Hours'])

def calculate_metrics(input_json="processed_degree_map.json", output_json="analyzed_degree_map.json"):
    degree_map_df = pd.read_json(input_json)

    # Debugging: print column names
    print("Columns in JSON:", degree_map_df.columns)

    # Calculate blocking and delay metrics
    degree_map_df['Blocking'] = degree_map_df.apply(blocking_metric, axis=1)
    degree_map_df['Delay'] = degree_map_df['Complexity_Metric'] * 0.5  # Simplified delay metric

    degree_map_df.to_json(output_json, orient='records')

if __name__ == "__main__":
    calculate_metrics()

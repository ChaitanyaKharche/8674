import pandas as pd
import json

def complexity_calculator(course):
    # Calculate complexity based on prerequisites and credits
    complexity = int(course['Credit Hours']) + len(str(course['Prerequisites']).split(';')) * 2
    return complexity

def process_degree_map(csv_path, output_json="processed_degree_map.json"):
    # Manually set column names to ensure alignment
    column_names = [
        "Course ID", "Course Name", "Number", "Prefix", "Prerequisites",
        "Corequisites", "Strict-Corequisites", "Credit Hours", "Institution", "Canonical Name"
    ]
    degree_map_df = pd.read_csv(csv_path, skiprows=5, names=column_names)

    # Print column names for debugging
    print("Columns in CSV:", degree_map_df.columns)

    # Convert 'Credit Hours' to numeric, replacing invalid values with 0
    degree_map_df['Credit Hours'] = pd.to_numeric(degree_map_df['Credit Hours'], errors='coerce').fillna(0).astype(int)

    # Ensure other columns match and fill missing values
    degree_map_df['Prerequisites'] = degree_map_df['Prerequisites'].fillna('')
    degree_map_df['Corequisites'] = degree_map_df['Corequisites'].fillna('')

    # Calculate complexity metric
    degree_map_df['Complexity_Metric'] = degree_map_df.apply(complexity_calculator, axis=1)

    # Save to JSON format
    degree_map_df.to_json(output_json, orient='records')

if __name__ == "__main__":
    process_degree_map('NEU Computer Science.csv')

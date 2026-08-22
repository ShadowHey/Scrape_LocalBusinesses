import os
import glob
import pandas as pd
from pathlib import Path

def aggregate_temp_csvs():
    input_dir = Path("temp_csvs")
    output_dir = Path("final_results")
    
    if not input_dir.exists():
        print(f"Directory {input_dir} does not exist. Nothing to aggregate.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    final_output_file = output_dir / "aggregated_leads.csv"
    
    all_dataframes = []
    csv_files = list(input_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {input_dir}.")
        return

    print(f"Found {len(csv_files)} CSV files. Aggregating...")

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # The filename format is expected to be: Term_zipcode.csv
            # E.g., Travel_Agency_30002.csv
            filename_parts = csv_file.stem.split('_')
            zip_code = filename_parts[-1] if filename_parts else "Unknown"
            
            # Create a dynamic mapping for column headers 
            # (Instant Data Scraper relies on CSS classes as headers)
            rename_map = {}
            for col in df.columns:
                c_lower = str(col).lower().strip()
                if c_lower == 'hfpxzc href':
                    rename_map[col] = 'link'
                elif c_lower == 'qbf1pd':
                    rename_map[col] = 'name'
                elif c_lower == 'w4efsd':
                    rename_map[col] = 'rating_or_category'
                elif 'address' in c_lower:
                    rename_map[col] = 'address'
                elif c_lower == 'lcr4fd href':
                    rename_map[col] = 'website'
                elif 'website' in c_lower or 'url' in c_lower:
                    if 'website' not in rename_map.values():
                        rename_map[col] = 'website'
            
            # Apply the mapping
            df.rename(columns=rename_map, inplace=True)
            
            # Discard any rows that don't have a valid link, as they aren't useful leads
            if 'link' not in df.columns:
                continue
                
            if 'name' not in df.columns:
                df['name'] = "Unknown"
                
            # Add metadata columns
            df['source_zip'] = zip_code
            df['tag'] = 'extension_scrape'
            df['source_file'] = csv_file.name
            
            all_dataframes.append(df)
            
        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")

    if not all_dataframes:
        print("No valid data could be extracted from the CSV files.")
        return

    # Combine everything into one giant dataframe
    master_df = pd.concat(all_dataframes, ignore_index=True)
    
    initial_count = len(master_df)
    
    # Remove duplicates based on the listing link
    master_df.drop_duplicates(subset=['link'], inplace=True)
    final_count = len(master_df)
    

    # Save the aggregated output
    master_df.to_csv(final_output_file, index=False)
    
    # --- Update history.json ---
    try:
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'current_task_config.json')
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'history.json')
        with open(config_path, 'r') as f:
            task_id = json.load(f).get('id')
        if task_id and os.path.exists(history_path):
            with open(history_path, 'r') as f:
                hist = json.load(f)
            if task_id in hist:
                hist[task_id]['metrics']['total_leads_found_in_maps'] = final_count
                with open(history_path, 'w') as f:
                    json.dump(hist, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not update history metrics: {e}")
    # ---------------------------

    
    print(f"\n✅ Aggregation Complete!")
    print(f"Total rows parsed: {initial_count}")
    print(f"Total unique leads: {final_count}")
    print(f"Saved to: {final_output_file}")

if __name__ == "__main__":
    aggregate_temp_csvs()

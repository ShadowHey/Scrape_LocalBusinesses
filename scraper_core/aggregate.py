import os
import sqlite3
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
    
    csv_files = list(input_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {input_dir}.")
        return

    print(f"Found {len(csv_files)} CSV files. Aggregating via SQLite...")

    db_path = output_dir / "pipeline_cache.db"
    if db_path.exists():
        try: db_path.unlink()
        except: pass # Ignore if locked

    conn = sqlite3.connect(str(db_path))
    
    initial_count = 0
    valid_files = 0
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            filename_parts = csv_file.stem.split('_')
            zip_code = filename_parts[-1] if filename_parts else "Unknown"
            
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
            
            df.rename(columns=rename_map, inplace=True)
            
            if 'link' not in df.columns:
                continue
                
            if 'name' not in df.columns:
                df['name'] = "Unknown"
                
            df['source_zip'] = zip_code
            df['tag'] = 'extension_scrape'
            df['source_file'] = csv_file.name
            
            initial_count += len(df)
            valid_files += 1
            
            core_columns = ['link', 'name', 'rating_or_category', 'address', 'website', 'source_zip', 'tag', 'source_file']
            for c in core_columns:
                if c not in df.columns:
                    df[c] = None
            df = df[core_columns]

            
            # Push to SQLite directly
            df.to_sql("raw_leads", conn, if_exists="append", index=False)
            
        except Exception as e:
            print(f"Error processing {csv_file.name}: {e}")

    if valid_files == 0:
        print("No valid data could be extracted from the CSV files.")
        conn.close()
        return

    # Deduplicate via SQL
    print("Deduplicating leads...")
    cursor = conn.cursor()
    # By using GROUP BY link, we keep the first inserted row per link
    cursor.execute("""
        CREATE TABLE final_leads AS
        SELECT * FROM raw_leads
        GROUP BY link
    """)
    conn.commit()

    # Get final count
    cursor.execute("SELECT COUNT(*) FROM final_leads")
    final_count = cursor.fetchone()[0]

    # Export to CSV in chunks
    print("Exporting to aggregated_leads.csv in chunks...")
    if final_output_file.exists():
        try: final_output_file.unlink()
        except: pass
        
    for chunk in pd.read_sql_query("SELECT * FROM final_leads", conn, chunksize=10000):
        chunk.to_csv(final_output_file, mode='a', index=False, header=not final_output_file.exists())
        
    conn.close()
    
    # Cleanup DB
    if db_path.exists():
        try: db_path.unlink()
        except: pass
    
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

    print(f"\n[+] Aggregation Complete!")
    print(f"Total rows parsed: {initial_count}")
    print(f"Total unique leads: {final_count}")
    print(f"Saved to: {final_output_file}")

if __name__ == "__main__":
    aggregate_temp_csvs()

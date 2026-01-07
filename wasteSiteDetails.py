import pandas as pd
import os

# 1. Configuration
INPUT_FILE = '2023 Waste Data Interrogator - Wastes Received (Excel) - Version 2.xlsb'
SHEET_NAME = '2023 Waste Received' 
OUTPUT_FILE = 'SouthWest_Clinical_Received_2023.csv'

TARGET_REGION = 'South West'
WASTE_PREFIX = '18 01'

def extract_waste_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File not found - {INPUT_FILE}")
        return

    try:
        df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, engine='pyxlsb')
        df.columns = df.columns.str.strip()
        
    except ValueError as ve:
        print(f"Error: {ve}")
        try:
            xl = pd.ExcelFile(INPUT_FILE, engine='pyxlsb')
            print(f"Available Sheets: {xl.sheet_names}")
        except:
            pass
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"   Loaded {len(df)} records. Filtering...")

    # 2. Filter
    mask = (
        (df['Facility RPA'] == TARGET_REGION) & 
        (df['Waste Code'].astype(str).str.startswith(WASTE_PREFIX))
    )
    filtered_df = df[mask].copy()
    
    # 3. Save to CSV
    if filtered_df.empty:
        print("No records found matching your criteria.")
    else:
        print(f"   Found {len(filtered_df)} matching records.")
        filtered_df.to_csv(OUTPUT_FILE, index=False)
        print(f"3. Success! Data saved to: {OUTPUT_FILE}")
        
        print("\n--- Summary of Extracted Data ---")
        print(filtered_df['Waste Code'].value_counts().head())
        print(f"Unique Facilities: {filtered_df['Site Name'].nunique()}")

if __name__ == "__main__":
    extract_waste_data()
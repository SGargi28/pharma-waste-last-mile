import pandas as pd

# 1. Configurations
INPUT_FILE = '2023 Waste Data Interrogator - Wastes Received (Excel) - Version 2.xlsb'
SHEET_NAME = '2023 Waste Received'
OUTPUT_FILE = 'SouthWest_Compliance_Analysis.csv'

def check_compliance(row):
    """
    Evaluates if the waste fate matches the legal requirement for the code.
    Returns: 'COMPLIANT' or 'NON-COMPLIANT'
    """
    code = str(row['Waste Code']).strip()
    fate = str(row['Fate']).lower()
    r_code = str(row['R and D code']).upper().strip()
    
    # Rule 1: CYTOTOXIC (18 01 08*) -> Must be Incinerated (D10 / R01)
    if code == '18 01 08*':
        if 'landfill' in fate:
            return 'NON-COMPLIANT'
        # Recycling (R05) is strictly forbidden for Cytotoxics
        if r_code.startswith('R05'):
            return 'NON-COMPLIANT'

    # Rule 2: INFECTIOUS (18 01 03*) -> No Recycling / No Landfill
    if code == '18 01 03*':
        if 'landfill' in fate:
            return 'NON-COMPLIANT'
        if r_code.startswith('R05'):
            return 'NON-COMPLIANT'

    # Rule 3: MEDICINES (18 01 09) -> No Landfill
    if code == '18 01 09':
        if 'landfill' in fate:
            return 'NON-COMPLIANT'

    # Rule 4: AMALGAM (18 01 10*) -> No Incineration
    if code == '18 01 10*':
        if 'incineration' in fate:
            return 'NON-COMPLIANT'

    return 'COMPLIANT'

try:
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, engine='pyxlsb')
except ImportError:
    print("Error: Library 'pyxlsb' missing. Run: pip install pyxlsb")
    exit()

# 2. Filtering
df_sw = df[
    (df['Facility RPA'] == 'South West') &
    (df['Waste Code'].astype(str).str.startswith('18 01'))
].copy()

# 3. Analysis
df_sw['Compliance Status'] = df_sw.apply(check_compliance, axis=1)

# 4. Output Preparation
output_columns = [
    'Facility RPA',      
    'Site Name',         
    'Facility WPA',      
    'Waste Code',        
    'Fate',              
    'Tonnes Received',   
    'R and D code',      
    'Compliance Status'  
]

final_df = df_sw[output_columns]

# 5. Export
final_df.to_csv(OUTPUT_FILE, index=False)
print(f"DONE. Analysis saved to: {OUTPUT_FILE}")
print(final_df.head())

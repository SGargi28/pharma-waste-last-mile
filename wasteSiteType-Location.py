import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 1. Configuration
FILE_PATH = '2023 Waste Data Interrogator - Wastes Received (Excel) - Version 2.xlsb'
SHEET_NAME = '2023 Waste Received'
TARGET_REGION = 'South West'
WASTE_PREFIX = '18 01'

def run_visual_analysis():
    try:
        df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME, engine='pyxlsb')
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"Error: {e}")
        return
    # 2. Filter
    mask = (
        (df['Facility RPA'] == TARGET_REGION) & 
        (df['Waste Code'].astype(str).str.startswith(WASTE_PREFIX))
    )
    df_sw = df[mask].copy()
    
    # 3. Heatmap (Region vs. Category Intensity)
    pivot_tonnage = df_sw.groupby(['Site Category', 'Facility Sub Region'])['Tonnes Received'].sum().unstack(fill_value=0)
    
    plt.figure(figsize=(12, 8))
    
    data = pivot_tonnage.values
    plt.imshow(data, cmap='YlOrRd', aspect='auto')
    plt.colorbar(label='Tonnes Received')
    
    plt.xticks(range(len(pivot_tonnage.columns)), pivot_tonnage.columns, rotation=45, ha="right")
    plt.yticks(range(len(pivot_tonnage.index)), pivot_tonnage.index)
    
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            text_color = "white" if val > data.max() * 0.5 else "black"
            plt.text(j, i, f'{val:.0f}', ha="center", va="center", color=text_color)

    plt.title(f'Intensity Heatmap: Clinical Waste Tonnage ({TARGET_REGION})\nWhere is the waste going?', fontsize=14)
    plt.ylabel('Facility Type')
    plt.xlabel('Sub Region')
    plt.tight_layout()
    plt.savefig('SouthWest_Waste_Heatmap.png')
    print("Saved 'SouthWest_Waste_Heatmap.png'")

if __name__ == "__main__":
    run_visual_analysis()
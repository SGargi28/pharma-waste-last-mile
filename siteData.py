import pandas as pd

df = pd.read_csv('ERIC - 2024_25 - Site data.csv', encoding='latin1')

# 1. List of columns to extract
columns_to_extract = [
    'Trust Code',
    'Trust Name',
    'Commissioning Region',
    'Trust Type',
    'Site Code',
    'Site Name',
    'Post Code',
    'Integrated Care Board',
    'Local Authority',
    'Site Type',
    'Incineration (clinical waste) cost (£)',
    'Incineration (clinical waste) weight (Tonnes)',
    'Alternative Treatment (clinical waste) cost (£)',
    'Alternative Treatment (clinical waste) weight (Tonnes)',
    'Offensive waste cost (£)',
    'Offensive waste weight (Tonnes)',
    'Clinical waste (excluding incineration) processed on site cost (£)',
    'Clinical waste (excluding incineration) processed on site weight (Tonnes)',
    'Clinical waste processed at municipal waste plants cost (£)',
    'Clinical waste processed at municipal waste plants weight (Tonnes)'
]

# 2. List of target ICBs
target_icbs = [
    'NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE ICB',
    'NHS BRISTOL, NORTH SOMERSET AND SOUTH GLOUCESTERSHIRE ICB',
    'NHS CORNWALL AND THE ISLES OF SCILLY ICB',
    'NHS DEVON ICB',
    'NHS DORSET ICB',
    'NHS GLOUCESTERSHIRE ICB',
    'NHS SOMERSET ICB'
]

# 3. Save to CSV
filtered_df = df[df['Integrated Care Board'].isin(target_icbs)]
result_df = filtered_df[columns_to_extract]

output_filename = 'South_West_ICBs_Site_Data.csv'
result_df.to_csv(output_filename, index=False)

print(f"Filtered data saved to {output_filename}")
print(f"Found {len(result_df)} records across {filtered_df['Integrated Care Board'].nunique()} ICBs.")
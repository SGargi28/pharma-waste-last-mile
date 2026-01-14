import pandas as pd
import requests
import time

# Configurations
INPUT_FILE = 'ERIC - 2024_25 - Site data.csv'
OUTPUT_FILE = 'SouthWest_ClinicalFacility_GeoCoded.csv'

# 1. List of target ICBs (South West)
TARGET_ICBS = [
    'NHS BATH AND NORTH EAST SOMERSET, SWINDON AND WILTSHIRE ICB',
    'NHS BRISTOL, NORTH SOMERSET AND SOUTH GLOUCESTERSHIRE ICB',
    'NHS CORNWALL AND THE ISLES OF SCILLY ICB',
    'NHS DEVON ICB',
    'NHS DORSET ICB',
    'NHS GLOUCESTERSHIRE ICB',
    'NHS SOMERSET ICB'
]

# 2. List of columns to extract
COLUMNS_TO_EXTRACT = [
    'Trust Code', 'Trust Name', 'Commissioning Region', 'Trust Type',
    'Site Code', 'Site Name', 'Post Code', 
    'Integrated Care Board', 'Local Authority', 'Site Type',
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

# Helper function : Bulk Geocoding
def get_lat_long_bulk(postcodes_list):
    """
    Takes a list of postcodes and returns a dictionary {postcode: (lat, long)}
    using the postcodes.io bulk API (much faster than loop).
    """
    url = "https://api.postcodes.io/postcodes"
    results = {}
    
    # The API accepts max 100 postcodes per batch
    BATCH_SIZE = 100
    
    print(f"Geocoding {len(postcodes_list)} unique postcodes...")
    
    for i in range(0, len(postcodes_list), BATCH_SIZE):
        batch = postcodes_list[i : i + BATCH_SIZE]
        
        try:
            response = requests.post(url, json={"postcodes": batch})
            if response.status_code == 200:
                data = response.json()['result']
                for item in data:
                    p_code = item['query']
                    res = item['result']
                    
                    if res:
                        results[p_code] = (res['latitude'], res['longitude'])
                    else:
                        results[p_code] = (None, None) # Postcode not found
            else:
                print(f"Error batch {i}: Status {response.status_code}")
                
        except Exception as e:
            print(f"Failed batch {i}: {e}")
            
        time.sleep(0.1) # Be polite to the API
        
    return results

# Main Execution

df = pd.read_csv(INPUT_FILE, encoding='latin1')
filtered_df = df[df['Integrated Care Board'].isin(TARGET_ICBS)].copy()
result_df = filtered_df[COLUMNS_TO_EXTRACT].copy()

# 1. Geocoding
# Get unique postcodes to minimize API calls (remove NaNs)
unique_postcodes = result_df['Post Code'].dropna().unique().tolist()

# 2. Get coordinates
coords_map = get_lat_long_bulk(unique_postcodes)

# 3. Map back to the dataframe
result_df['Latitude'] = result_df['Post Code'].map(lambda x: coords_map.get(x, (None, None))[0])
result_df['Longitude'] = result_df['Post Code'].map(lambda x: coords_map.get(x, (None, None))[1])

# 4. Export
result_df.to_csv(OUTPUT_FILE, index=False)
print(f"Geocoded data saved to {OUTPUT_FILE}")
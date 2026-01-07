import pandas as pd
import googlemaps
import time

# 1. Configuration
API_KEY = 'AIzaSyCiIW4AE2O8E9dIr9A1wBdCpRNcyAljL7g'
# Factor for Average Laden Rigid HGV (2023 Defra): ~0.23015 kg CO2e per tkm
EMISSION_FACTOR = 0.23015 

# 2. Filter
TARGET_REGION = 'South West'
TARGET_CODES = ['18 01 03*', '18 01 06*', '18 01 08*', '18 01 10*']

# 3. Initialize Google Maps
gmaps = googlemaps.Client(key=API_KEY)

def get_road_distance(origin, destination):
    
    try:
        # Same district = nominal 10km distance
        if origin == destination:
            return 10.0
            
        result = gmaps.distance_matrix(origins=f"{origin}, UK", 
                                       destinations=f"{destination}, UK",
                                       mode="driving")
        
        if result['rows'][0]['elements'][0]['status'] == 'OK':
            dist_meters = result['rows'][0]['elements'][0]['distance']['value']
            return dist_meters / 1000.0
    except Exception as e:
        print(f"Error: {origin} -> {destination} ({e})")
    return None

# --- Main Execution ---

df = pd.read_excel('2023 Hazardous Waste Interrogator (Excel) - Version 1.xlsm', sheet_name='2023 Data')

filtered_df = df[
    (df['Arising Region'] == TARGET_REGION) & 
    (df['Waste Code'].isin(TARGET_CODES))
].copy()

print(f"Filtered data: {len(filtered_df)} rows found.")

unique_routes = filtered_df[['Arising District', 'Deposit District']].drop_duplicates()
print(f"Unique routes to calculate: {len(unique_routes)}")

distances = []
for idx, row in unique_routes.iterrows():
    dist = get_road_distance(row['Arising District'], row['Deposit District'])
    distances.append(dist)
    time.sleep(0.1)  

unique_routes['Distance_km'] = distances

final_df = pd.merge(filtered_df, unique_routes, on=['Arising District', 'Deposit District'], how='left')

final_df['Waste_Miles_tkm'] = final_df['Tonnage'] * final_df['Distance_km']

# Carbon Footprint (kg CO2e)
final_df['Carbon_Footprint_kgCO2e'] = final_df['Waste_Miles_tkm'] * EMISSION_FACTOR

# Output
total_carbon = final_df['Carbon_Footprint_kgCO2e'].sum() / 1000  # Convert to tonnes
print(f"Total Carbon Footprint: {total_carbon:.2f} tonnes CO2e")

final_df.to_csv('SouthWest_ClinicalWaste_Analysis.csv', index=False)
print("Saved detailed breakdown to 'SouthWest_ClinicalWaste_Analysis.csv'")
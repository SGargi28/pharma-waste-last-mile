import pandas as pd
import numpy as np
from pyproj import Transformer
import requests
import time

# Configurations
API_KEY = "AIzaSyCiIW4AE2O8E9dIr9A1wBdCpRNcyAljL7g"
INPUT_FILE = '2023 Waste Data Interrogator - Wastes Received (Excel) - Version 2.xlsb'
SHEET_NAME = '2023 Waste Received'
OUTPUT_FILE = 'ClinicalWaste_WasteMile&Emission_Analysis.csv'

# 1.  Transforms UK Easting/Northing to Latitude/Longitude (BNG -> WGS84)
transformer = Transformer.from_crs("epsg:27700", "epsg:4326")

def bng_to_latlon(easting, northing):
    try:
        if pd.isna(easting) or pd.isna(northing):
            return None, None
        lat, lon = transformer.transform(easting, northing)
        return lat, lon
    except:
        return None, None

# 2. Waste Stream Colour Coding
def get_waste_colour(row):
    code = str(row['Waste Code']).strip()
    desc = str(row['EWC Waste Desc']).lower()
    
    if code == '18 01 08*':
        return 'Purple'
    elif code == '18 01 10*':
        return 'White'
    elif code == '18 01 09':
        return 'Blue'
    elif code == '18 01 04':
        return 'Tiger'
    elif code == '18 01 02':
        return 'Red'
    elif code == '18 01 03*':
        # Split logic: If description implies meds/chemicals -> Yellow, else Orange
        if any(x in desc for x in ['chemical', 'medicine', 'pharmaceutical', 'diagnostic']):
            return 'Yellow'
        else:
            return 'Orange'
    elif code == '18 01 06*':
        return 'Yellow/Red'
        
    return 'Unknown'

# 3. CO2 Emission Calculation
def get_co2_kg(row):
    # Factors (kg CO2e per Tonne)
    FACTORS = {
        'incineration_high': 1833.0, 
        'incineration_clinical': 1074.0, 
        'landfill': 587.0,
        'atp': 185.0,
        'recycling': 21.0,
        'transfer': 10.0
    }
    
    tonnes = row['Tonnes Received']
    fate = str(row['Fate']).lower()
    fac_type = str(row['Facility Type']).lower()
    r_code = str(row['R and D code']).upper()
    
    factor = FACTORS['transfer']

    if 'incineration' in fate:
        # High Temp Check
        if '18 01 08' in str(row['Waste Code']) or 'hazardous waste incinerator' in fac_type:
            factor = FACTORS['incineration_high']
        else:
            factor = FACTORS['incineration_clinical']
    elif 'landfill' in fate:
        factor = FACTORS['landfill']
    elif 'treatment' in fate or 'recovery' in fate:
        if r_code.startswith('R05'):
            factor = FACTORS['recycling']
        elif 'transfer' not in fac_type: 
            factor = FACTORS['atp']
            
    return tonnes * factor

# 4. Distance between Origin and Disposal Site
def get_real_road_distance(origin_name, dest_lat, dest_lon):
   
    if pd.isna(dest_lat) or pd.isna(origin_name) or API_KEY == "API_KEY":
        return 0
        
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    
    # Cleaning Origin Name for better API hit rate
    clean_origin = f"{origin_name}, UK"
    dest_coords = f"{dest_lat},{dest_lon}"
    
    params = {
        'origins': clean_origin,
        'destinations': dest_coords,
        'mode': 'driving',
        'key': API_KEY
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            element = data['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                # Returns meters, convert to miles
                meters = element['distance']['value']
                return meters * 0.000621371
    except Exception as e:
        pass
        
    return 0 

# Main Execution
df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, engine='pyxlsb')
df.columns = df.columns.astype(str).str.strip() # Remove any leading/trailing spaces
print(f"Columns: {df.columns.tolist()}")

# 2. Filtering (South West & 18 01)
df_sw = df[
    (df['Facility RPA'] == 'South West') &
    (df['Waste Code'].astype(str).str.startswith('18 01'))
].copy()

# 3. Coordinate Transformation
df_sw['Lat'], df_sw['Long'] = zip(*df_sw.apply(
    lambda x: bng_to_latlon(x['Easting'], x['Northing']), axis=1
))

# 4. Waste Stream Colour & CO2 Emission Calculation
df_sw['Waste Stream Colour'] = df_sw.apply(get_waste_colour, axis=1)
df_sw['CO2_kg'] = df_sw.apply(get_co2_kg, axis=1)

distances = []
for index, row in df_sw.iterrows():
    dist = get_real_road_distance(row['Recorded Origin'], row['Lat'], row['Long'])
    distances.append(dist)
    # time.sleep(0.1)
    
df_sw['Distance_Miles'] = distances

# 5. Waste Mile Calculation
df_sw['Waste Mile'] = df_sw['Distance_Miles'] * df_sw['Tonnes Received']

# 5. Column Selection & Renaming
cols_map = {
    'Facility RPA': 'Facility RPA',       
    'Facility WPA': 'Facility WPA',       
    'Site Name': 'Site Name',             
    'Lat': 'Latitude',                    
    'Long': 'Longitude',                 
    'Waste Code': 'Waste Code',           
    'Site Category': 'Site Category',     
    'Recorded Origin': 'Recorded Origin', 
    'Fate': 'Fate',                       
    'R and D code': 'R and D code',       
    'Tonnes Received': 'Tonnes Received', 
    'Waste Stream Colour': 'Waste Stream Colour', 
    'Distance_Miles': 'Distance (Miles)',         
    'Waste Mile': 'Waste Miles',                 
    'CO2_kg': 'CO2 (kg)'                          
}

final_df = df_sw[list(cols_map.keys())].rename(columns=cols_map)

# 6. Export
final_df.to_csv(OUTPUT_FILE, index=False)
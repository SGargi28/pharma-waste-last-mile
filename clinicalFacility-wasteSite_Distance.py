import pandas as pd
import googlemaps
from pyproj import Transformer
from datetime import datetime

# ==========================================
# 1. CONFIGURATION
# ==========================================
API_KEY = 'AIzaSyCiIW4AE2O8E9dIr9A1wBdCpRNcyAljL7g'  
MAX_DRIVE_MINUTES = 45

# Input Files
FILE_CLINICAL_FACILITY = 'SouthWest_ClinicalFacility_GeoCoded.csv'
FILE_WASTE_SITES = 'SouthWest_Clinical_Received_2023.csv'

# Output Files
OUTPUT_CLINICAL = 'SouthWest_ClinicalFacility_Proximity.csv'
OUTPUT_WASTE = 'SouthWest_WasteSites.csv'

# Target Site Categories (Filter for Column R)
TARGET_CATEGORIES = ['Incineration', 'Landfill', 'Treatment']

# Initialize Google Maps Client
gmaps = googlemaps.Client(key=API_KEY)

# Initialize Coordinate Transformer (BNG -> WGS84)
transformer = Transformer.from_crs("epsg:27700", "epsg:4326")

# ==========================================
# 2. PROCESS WASTE SITES (Output File 1)
# ==========================================
print("1. Processing Waste Sites...")

try:
    df_waste = pd.read_csv(FILE_WASTE_SITES, encoding='latin1')
except:
    df_waste = pd.read_csv(FILE_WASTE_SITES, encoding='cp1252')

# Helper to convert Easting/Northing
def convert_coords(row):
    e, n = row['Easting'], row['Northing']
    try:
        if pd.isna(e) or pd.isna(n):
            return None, None
        lat, lon = transformer.transform(e, n)
        return lat, lon
    except:
        return None, None

# Apply conversion
df_waste['Latitude'], df_waste['Longitude'] = zip(*df_waste.apply(convert_coords, axis=1))

# Extract specific columns (A, C, E, F, H, I, J -> Lat/Long)
# Mapping based on typical WDI headers:
# A=Facility RPA, C=Facility WPA, E=Permit, F=Site Name, H=Permit Type
# I=Easting, J=Northing (Removed, kept Lat/Long)
waste_cols_map = {
    'Facility RPA': 'Facility RPA',
    'Facility WPA': 'Facility WPA',
    'Permit': 'Permit',
    'Site Name': 'Site Name',
    'Permit Type': 'Permit Type',
    'Site Category': 'Site Category', # Keep Site Category for filtering
    'Latitude': 'Latitude',
    'Longitude': 'Longitude'
}

# Create Cleaned Waste DataFrame
df_waste_clean = df_waste[list(waste_cols_map.keys())].copy()

# FILTER LOGIC: Keep only target categories
# We perform a case-insensitive check
pattern = '|'.join(TARGET_CATEGORIES)
df_waste_clean = df_waste_clean[
    df_waste_clean['Site Category'].astype(str).str.contains(pattern, case=False, na=False)
].copy()

print(f"   > Filtered waste sites. kept {len(df_waste_clean)} facilities matching {TARGET_CATEGORIES}")

# Save Waste CSV
df_waste_clean.to_csv(OUTPUT_WASTE, index=False)
print(f"   > Saved filtered waste sites to {OUTPUT_WASTE}")


# ==========================================
# 3. PROCESS CLINICAL FACILITIES (Output File 2)
# ==========================================
print("2. Processing Clinical Facilities & Calculating Distances...")

df_hosp = pd.read_csv(FILE_CLINICAL_FACILITY)

# Prepare lists for derived data
nearest_sites = []
nearest_site_cats = [] # To store the category of the nearest site
distances_miles = []
drive_times_mins = []
within_45_flags = []

# List of waste sites coords for the matrix
waste_destinations = df_waste_clean[['Latitude', 'Longitude']].to_dict('records')
waste_names = df_waste_clean['Site Name'].tolist()
waste_cats = df_waste_clean['Site Category'].tolist()

# Loop through each hospital
for index, row in df_hosp.iterrows():
    origin_lat, origin_lon = row['Latitude'], row['Longitude'] # Columns U, V
    
    if pd.isna(origin_lat) or pd.isna(origin_lon) or not waste_destinations:
        nearest_sites.append("N/A")
        nearest_site_cats.append("N/A")
        distances_miles.append(0)
        drive_times_mins.append(0)
        within_45_flags.append("N/A")
        continue

    # Optimization: Google Matrix API accepts up to 25 destinations per call.
    
    best_time = float('inf')
    best_site = None
    best_cat = None
    best_dist_text = ""
    
    # Batch process destinations (chunks of 25)
    chunk_size = 25
    found_valid = False
    
    for i in range(0, len(waste_destinations), chunk_size):
        chunk_dest = waste_destinations[i:i+chunk_size]
        chunk_names = waste_names[i:i+chunk_size]
        chunk_cats = waste_cats[i:i+chunk_size]
        
        # Format for API
        origins = (origin_lat, origin_lon)
        dests = [(d['Latitude'], d['Longitude']) for d in chunk_dest]
        
        try:
            matrix = gmaps.distance_matrix(origins, dests, mode="driving")
            
            if matrix['status'] == 'OK':
                elements = matrix['rows'][0]['elements']
                for j, element in enumerate(elements):
                    if element['status'] == 'OK':
                        # Duration in seconds
                        duration_sec = element['duration']['value']
                        duration_min = duration_sec / 60
                        
                        if duration_min < best_time:
                            best_time = duration_min
                            best_site = chunk_names[j]
                            best_cat = chunk_cats[j]
                            # Distance text (e.g., "15.4 mi")
                            best_dist_text = element['distance']['text']
                            found_valid = True
                            
        except Exception as e:
            print(f"API Error at row {index}: {e}")

    # Store results for this hospital
    if found_valid:
        nearest_sites.append(best_site)
        nearest_site_cats.append(best_cat)
        distances_miles.append(best_dist_text)
        drive_times_mins.append(round(best_time, 1))
        within_45_flags.append("Yes" if best_time <= MAX_DRIVE_MINUTES else "No")
    else:
        nearest_sites.append("No Route Found")
        nearest_site_cats.append("N/A")
        distances_miles.append("0")
        drive_times_mins.append(0)
        within_45_flags.append("No")

    # Progress Indicator
    if index % 5 == 0:
        print(f"   > Processed {index}/{len(df_hosp)} hospitals...")

# Add Derived Columns
df_hosp['Nearest Waste Site'] = nearest_sites
df_hosp['Nearest Site Category'] = nearest_site_cats # New column
df_hosp['Distance'] = distances_miles
df_hosp['Drive Time (Mins)'] = drive_times_mins
df_hosp['Within 45 Mins?'] = within_45_flags

# Extract Specific Columns
# A-G: Trust Code, Trust Name, Region, Trust Type, Site Code, Site Name, Post Code
# U, V: Latitude, Longitude (Assuming they are at the end based on previous script)
# Derived: Nearest..., Nearest Category, Distance..., Within...

# Define column list explicitly to match requirements
cols_to_keep = [
    'Trust Code', 'Trust Name', 'Commissioning Region', 'Trust Type', 
    'Site Code', 'Site Name', 'Post Code',               # A-G
    'Latitude', 'Longitude',                             # U, V
    'Nearest Waste Site', 'Nearest Site Category',       # Derived
    'Distance', 'Within 45 Mins?'                        # Derived
]

# Create final DF
df_clinical_final = df_hosp[cols_to_keep]

# Save Clinical CSV
df_clinical_final.to_csv(OUTPUT_CLINICAL, index=False)
print(f"   > Saved clinical analysis to {OUTPUT_CLINICAL}")
print("Done.")
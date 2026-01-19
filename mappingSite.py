import pandas as pd
import folium
from folium import plugins

# Configuration
FILE_HOSPITALS_GEO = 'SouthWest_ClinicalFacility_GeoCoded.csv'
FILE_HOSPITALS_PROX = 'SouthWest_ClinicalFacility_Proximity.csv'
FILE_PLANTS = 'SouthWest_WasteSites.csv'
OUTPUT_MAP = 'SouthWest_Waste_Logistics_Map.html'

# Load Hospitals (GeoCoded)
try:
    df_geo = pd.read_csv(FILE_HOSPITALS_GEO, encoding='latin1')
except:
    df_geo = pd.read_csv(FILE_HOSPITALS_GEO)

# Calculate Total Volume
col_incin = 'Incineration (clinical waste) weight (Tonnes)'
col_alt = 'Alternative Treatment (clinical waste) weight (Tonnes)'
col_off = 'Offensive waste weight (Tonnes)'

# Ensure numeric
for col in [col_incin, col_alt, col_off]:
    if col in df_geo.columns:
        df_geo[col] = pd.to_numeric(df_geo[col], errors='coerce').fillna(0)
    else:
        print(f"Warning: Column '{col}' not found. Assuming 0.")
        df_geo[col] = 0

df_geo['Total_Volume'] = df_geo[col_incin] + df_geo[col_alt] + df_geo[col_off]

# B. Load Proximity Data
try:
    df_prox = pd.read_csv(FILE_HOSPITALS_PROX, encoding='latin1')
except:
    df_prox = pd.read_csv(FILE_HOSPITALS_PROX)

# C. Load Waste Plants
try:
    df_plants = pd.read_csv(FILE_PLANTS, encoding='latin1')
except:
    df_plants = pd.read_csv(FILE_PLANTS)


# Create composite key for joining
df_geo['JoinKey'] = df_geo['Site Name'].astype(str).str.strip() + "_" + df_geo['Post Code'].astype(str).str.strip()
df_prox['JoinKey'] = df_prox['Site Name'].astype(str).str.strip() + "_" + df_prox['Post Code'].astype(str).str.strip()

df_hospitals = pd.merge(
    df_geo, 
    df_prox[['JoinKey', 'Within 45 Mins?', 'Nearest Waste Site', 'Distance']], 
    on='JoinKey', 
    how='inner' # Only keep matches
)

df_hospitals = df_hospitals.dropna(subset=['Latitude', 'Longitude'])
df_hospitals = df_hospitals.drop_duplicates(subset=['JoinKey'])
df_plants_unique = df_plants.drop_duplicates(subset=['Permit'])

# Remove invalid lat/long
df_plants_unique = df_plants_unique.dropna(subset=['Latitude', 'Longitude'])

# Generate Map
print("4. Generating Map...")

# Center map on South West (approx centroid)
m = folium.Map(location=[51.0, -3.5], zoom_start=8, tiles='cartodbpositron')

# --- A. PLOT HOSPITALS (Circles) ---
for idx, row in df_hospitals.iterrows():
    
    # Logic: Color
    is_covered = str(row['Within 45 Mins?']).lower() == 'yes'
    color = 'blue' if is_covered else 'red'
    
    # Logic: Radius (Scaled by Volume)
    # Scale factor: e.g., Volume / 10. Min radius 3, Max radius 20.
    vol = row['Total_Volume']
    radius = max(3, min(20, (vol ** 0.5) * 1.5)) # Square root scaling looks better visually
    
    # Tooltip Content
    tooltip_text = f"""
    <b>{row['Site Name']}</b><br>
    Volume: {int(vol)} Tonnes<br>
    Covered (45m): {row['Within 45 Mins?']}<br>
    Nearest: {row['Nearest Waste Site']}
    """
    
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        weight=1,
        tooltip=tooltip_text
    ).add_to(m)


# --- B. PLOT PLANTS (Triangles) ---
# Define colors for categories
category_colors = {
    'Incineration': 'purple',
    'Treatment': 'green',
    'Landfill': 'black',
    'Transfer': 'orange'
}

for idx, row in df_plants_unique.iterrows():
    
    # Determine Color
    cat = str(row['Site Category'])
    plant_color = 'gray' # default
    for key, val in category_colors.items():
        if key.lower() in cat.lower():
            plant_color = val
            break
            
    # Tooltip
    plant_tooltip = f"""
    <b>{row['Site Name']}</b><br>
    Type: {cat}<br>
    Permit: {row['Permit']}
    """
    
    # Plot Triangle (RegularPolygonMarker with 3 sides)
    folium.RegularPolygonMarker(
        location=[row['Latitude'], row['Longitude']],
        number_of_sides=3,
        radius=8,
        color=plant_color,
        fill=True,
        fill_color=plant_color,
        fill_opacity=0.9,
        tooltip=plant_tooltip
    ).add_to(m)


# Add Legend
legend_html = """
<div style="position: fixed; 
     bottom: 50px; left: 50px; width: 250px; height: auto; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity:0.9; padding: 10px;">
     <b>NHS Waste Logistics</b><br>
     <i class="fa fa-circle" style="color:blue"></i> Hospital (Within 45m)<br>
     <i class="fa fa-circle" style="color:red"></i> Hospital (> 45m Drive)<br>
     <small>*Circle size = Waste Volume</small><br>
     <hr>
     <b>Waste Facilities</b><br>
     <i class="fa fa-play" style="color:purple; transform: rotate(-90deg);"></i> Incineration<br>
     <i class="fa fa-play" style="color:green; transform: rotate(-90deg);"></i> Treatment<br>
     <i class="fa fa-play" style="color:black; transform: rotate(-90deg);"></i> Landfill<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
m.save(OUTPUT_MAP)

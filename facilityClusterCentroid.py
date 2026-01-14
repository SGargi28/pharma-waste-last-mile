import pandas as pd
import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.metrics.pairwise import haversine_distances
import matplotlib.pyplot as plt
import seaborn as sns

# Confoguration
INPUT_CLINICAL_FILE = 'SouthWest_ClinicalFacility_GeoCoded.csv'
INPUT_WASTE_SITES_FILE = 'SouthWest_WasteSites.csv'

# Output Files
OUTPUT_DEMAND_CSV = 'SouthWest_Clustered_Demand.csv'
OUTPUT_CENTROIDS_CSV = 'SouthWest_Cluster_Centroids.csv'
OUTPUT_PROPOSED_SITES_CSV = 'SouthWest_Proposed_New_Facilities.csv'
OUTPUT_MAP_IMAGE = 'SouthWest_Optimization_Map.png'

def main():
    print("1. Loading Data...")
    try:
        df_geo = pd.read_csv(INPUT_CLINICAL_FILE)
        df_waste_sites = pd.read_csv(INPUT_WASTE_SITES_FILE)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # --- 2. DATA PREPARATION ---
    incin_col = 'Incineration (clinical waste) weight (Tonnes)'
    at_col = 'Alternative Treatment (clinical waste) weight (Tonnes)'
    off_col = 'Offensive waste weight (Tonnes)'

    # Ensure numeric data and fill missing values
    cols_to_clean = [incin_col, at_col, off_col]
    for col in cols_to_clean:
        if col in df_geo.columns:
            df_geo[col] = pd.to_numeric(df_geo[col], errors='coerce').fillna(0)
        else:
            print(f"Warning: Column '{col}' not found. Assuming 0.")
            df_geo[col] = 0

    # Consolidate Waste Streams
    # 1. Incineration Stream (Hazardous/Infectious)
    df_geo['Incin_Waste'] = df_geo[incin_col]
    
    # 2. AT Stream (Orange Bags + Offensive)
    # Offensive waste is often treated similarly to AT (low temp energy recovery or sterilization)
    df_geo['AT_Waste'] = df_geo[at_col] + df_geo[off_col]
    
    # 3. Total for Clustering
    df_geo['Total_Waste'] = df_geo['Incin_Waste'] + df_geo['AT_Waste']

    # Filter valid coordinates for spatial analysis
    df_demand = df_geo.dropna(subset=['Latitude', 'Longitude']).copy()
    coords_demand = np.radians(df_demand[['Latitude', 'Longitude']].values)

    print(f"   -> Analyzed {len(df_demand)} facilities.")
    print(f"   -> Total Incineration Demand: {df_demand['Incin_Waste'].sum():.2f} tonnes")
    print(f"   -> Total AT Demand: {df_demand['AT_Waste'].sum():.2f} tonnes")

    # 3. HDBSCAN Clustering
    hdb = HDBSCAN(min_cluster_size=5, min_samples=3, metric='haversine')
    cluster_labels = hdb.fit_predict(coords_demand)
    df_demand['Cluster'] = cluster_labels

    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_noise = list(cluster_labels).count(-1)
    print(f"   -> Identified {n_clusters} clusters (Hubs) and {n_noise} noise points.")

    # Calculate Centroids (Collection Hubs)
    
    cluster_summary = df_demand[df_demand['Cluster'] != -1].groupby('Cluster').agg({
        'Latitude': 'mean',
        'Longitude': 'mean',
        'Incin_Waste': 'sum',
        'AT_Waste': 'sum',
        'Total_Waste': 'sum',
        'Site Name': 'count'
    }).reset_index()
    cluster_summary.rename(columns={'Site Name': 'Facility_Count'}, inplace=True)

    # Prepare all nodes (including noise) for facility location analysis
    noise_points = df_demand[df_demand['Cluster'] == -1][
        ['Latitude', 'Longitude', 'Incin_Waste', 'AT_Waste', 'Total_Waste']
    ].copy()
    noise_points['Cluster'] = -1
    noise_points['Facility_Count'] = 1
    
    df_all_nodes = pd.concat([cluster_summary, noise_points], ignore_index=True)

    # 4. Determine Optimal Locations for New Facilities
    print("\n3. Determining Optimal New Facility Locations...")

    def find_weighted_center(nodes_df, waste_col, supply_df, type_keyword):
        """
        Finds the location that minimizes the weighted distance for unserved demand.
        Score = Waste_Volume * Distance_to_Nearest_Existing_Site
        """
        # Filter relevant nodes (those producing this waste type)
        target = nodes_df[nodes_df[waste_col] > 0].copy()
        
        if target.empty:
            return None

        # Calculate Distance to EXISTING facilities of this type
        existing = supply_df[
            supply_df['Site Category'].str.contains(type_keyword, case=False, na=False) |
            supply_df['Permit Type'].str.contains(type_keyword, case=False, na=False)
        ]

        if not existing.empty:
            coords_nodes = np.radians(target[['Latitude', 'Longitude']].values)
            coords_supply = np.radians(existing[['Latitude', 'Longitude']].dropna().values)
            
            # Find distance to closest existing site (km)
            dists = haversine_distances(coords_nodes, coords_supply) * 6371
            target['Dist_to_Existing'] = dists.min(axis=1)
        else:
            target['Dist_to_Existing'] = 50.0 # Default penalty if no sites exist

        # Calculate "Need Score" (High Waste + Far from existing = High Score)
        target['Score'] = target[waste_col] * target['Dist_to_Existing']
        
        total_score = target['Score'].sum()
        if total_score == 0: return target['Latitude'].mean(), target['Longitude'].mean()

        # Weighted Center of Gravity
        best_lat = (target['Latitude'] * target['Score']).sum() / total_score
        best_lon = (target['Longitude'] * target['Score']).sum() / total_score
        
        return best_lat, best_lon

    # A. New Incinerator
    incin_lat, incin_lon = find_weighted_center(df_all_nodes, 'Incin_Waste', df_waste_sites, 'Incinerat')
    print(f"   -> Proposed Incinerator: Lat {incin_lat:.4f}, Lon {incin_lon:.4f}")

    # B. New AT Facility
    at_lat, at_lon = find_weighted_center(df_all_nodes, 'AT_Waste', df_waste_sites, 'Treatment')
    print(f"   -> Proposed AT Facility: Lat {at_lat:.4f}, Lon {at_lon:.4f}")

    # 5. Visualization
    plt.figure(figsize=(12, 10))

    # Plot Clusters
    clustered = df_demand[df_demand['Cluster'] != -1]
    plt.scatter(clustered['Longitude'], clustered['Latitude'], c=clustered['Cluster'], cmap='tab20', s=20, alpha=0.6, label='Clustered GP/Clinics')

    # Plot Noise
    noise = df_demand[df_demand['Cluster'] == -1]
    plt.scatter(noise['Longitude'], noise['Latitude'], c='lightgray', s=15, alpha=0.4, label='Noise (Outliers)')

    # Plot Existing Sites
    incin_sites = df_waste_sites[df_waste_sites['Site Category'].str.contains('Incinerat', case=False, na=False)]
    at_sites = df_waste_sites[~df_waste_sites['Site Category'].str.contains('Incinerat', case=False, na=False)]
    
    plt.scatter(incin_sites['Longitude'], incin_sites['Latitude'], c='darkred', marker='^', s=80, edgecolors='black', label='Existing Incinerators')
    plt.scatter(at_sites['Longitude'], at_sites['Latitude'], c='green', marker='^', s=80, edgecolors='black', label='Existing AT/Treatment')

    # Plot Proposed Sites
    plt.scatter(incin_lon, incin_lat, c='red', marker='*', s=350, edgecolors='black', label='PROPOSED Incinerator', zorder=10)
    plt.scatter(at_lon, at_lat, c='orange', marker='*', s=350, edgecolors='black', label='PROPOSED AT Facility', zorder=10)

    plt.title(f'South West Clinical Waste Optimization\n(HDBSCAN Clusters: {n_clusters})', fontsize=14)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend(loc='lower left', frameon=True)
    plt.grid(True, linestyle='--', alpha=0.3)
    
    plt.savefig(OUTPUT_MAP_IMAGE, dpi=300)
    print(f"   -> Map saved to {OUTPUT_MAP_IMAGE}")

    # 6. Export Results
    df_demand.to_csv(OUTPUT_DEMAND_CSV, index=False)
    cluster_summary.to_csv(OUTPUT_CENTROIDS_CSV, index=False)
    
    proposed_df = pd.DataFrame({
        'Facility_Type': ['Incinerator', 'AT_Facility'],
        'Latitude': [incin_lat, at_lat],
        'Longitude': [incin_lon, at_lon],
        'Rationale': ['Based on Infectious Waste & Distance to Existing Incinerators', 
                      'Based on AT/Offensive Waste & Distance to Existing Treatment']
    })
    proposed_df.to_csv(OUTPUT_PROPOSED_SITES_CSV, index=False)
    
if __name__ == "__main__":
    main()
import os
from dotenv import load_dotenv

load_dotenv() # Loads variables from your .env file
import pandas as pd
import requests
import math

# --- CONFIGURATION ---
# NEW, SECURE WAY
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PARTNERS_FILE = "partners_geocoded.csv"

def geocode_address(address):
    """
    Takes a full address string and returns latitude and longitude 
    using Google's Geocoding API.
    Returns (lat, lon) or None if not found.
    """
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            print(f"Geocoding failed for '{address}'. Status: {data['status']}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during geocoding: {e}")
        return None

def get_driving_distances(origin_coords, destination_coords_list):
    """
    NEW FUNCTION: Uses the Google Distance Matrix API to get driving distances.
    Handles chunking destinations for lists larger than 25.
    """
    all_distances = []
    # The API is limited to 25 destinations per request
    chunk_size = 25 
    
    for i in range(0, len(destination_coords_list), chunk_size):
        chunk = destination_coords_list[i:i + chunk_size]
        
        origin_str = f"{origin_coords[0]},{origin_coords[1]}"
        destinations_str = "|".join([f"{lat},{lng}" for lat, lng in chunk])
        
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin_str}&destinations={destinations_str}&units=imperial&key={API_KEY}"
        
        try:
            response = requests.get(url)
            data = response.json()
            
            if data['status'] == 'OK':
                for element in data['rows'][0]['elements']:
                    if element['status'] == 'OK':
                        # Distance is returned in meters, convert to miles
                        distance_in_meters = element['distance']['value']
                        distance_in_miles = distance_in_meters / 1609.34
                        all_distances.append(distance_in_miles)
                    else:
                        all_distances.append(float('inf')) # Use infinity for failed lookups
            else:
                # Add infinity for all destinations in the failed chunk
                all_distances.extend([float('inf')] * len(chunk))

        except requests.exceptions.RequestException as e:
            print(f"An error occurred with the Distance Matrix API: {e}")
            all_distances.extend([float('inf')] * len(chunk))
            
    return all_distances


def find_closest_partners(customer_address):
    """
    Finds the three closest partners using driving distance.
    """
    print(f"Finding closest partners for: {customer_address}")
    
    # 1. Geocode the customer's address
    customer_coords = geocode_address(customer_address)
    if not customer_coords:
        return "Could not find coordinates for the customer address."

    print(f"Customer coordinates: {customer_coords}")

    # 2. Load the partners data
    try:
        partners_df = pd.read_csv(PARTNERS_FILE)
    except FileNotFoundError:
        return f"Error: The file '{PARTNERS_FILE}' was not found."

    # 3. Get driving distance to each partner
    partner_coords_list = list(zip(partners_df['latitude'], partners_df['longitude']))
    
    print(f"Getting driving distances for {len(partner_coords_list)} partners...")
    distances = get_driving_distances(customer_coords, partner_coords_list)
    
    # Add the calculated distances as a new column
    partners_df['distance_miles'] = distances
    
    # 4. Sort by distance and select the top 3
    closest_partners = partners_df.sort_values(by='distance_miles').head(3)
    
    # 5. Format the result for easy reading
    results = []
    for index, partner in closest_partners.iterrows():
        results.append({
            "partner_name": partner['partner_name'],
            "address": f"{partner['address_line1']}, {partner['city']}, {partner['state']} {partner['postal_code']}",
            "distance_miles": round(partner['distance_miles'], 2)
        })
        
    return results

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    test_address = "Charlotte, NC"
    
    closest = find_closest_partners(test_address)
    
    print("\n--- Closest Service Centers (Driving Distance) ---")
    if isinstance(closest, list):
        for partner in closest:
            print(f"Name: {partner['partner_name']}")
            print(f"Address: {partner['address']}")
            print(f"Distance: {partner['distance_miles']} miles\n")
    else:
        print(closest)
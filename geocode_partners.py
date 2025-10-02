import os
from dotenv import load_dotenv

load_dotenv() # Loads variables from your .env file
import pandas as pd
import requests
import time

# --- CONFIGURATION ---
# NEW, SECURE WAY
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
INPUT_FILE = "partners_clean.csv"
OUTPUT_FILE = "partners_geocoded.csv"

def get_coordinates(address):
    """
    Takes a full address string and returns latitude and longitude using Google's Geocoding API.
    """
    # Construct the API request URL
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY}"
    
    try:
        # Make the API request
        response = requests.get(url)
        # Parse the JSON response
        data = response.json()
        
        # Check if the API returned a valid result
        if data['status'] == 'OK':
            # Extract latitude and longitude
            latitude = data['results'][0]['geometry']['location']['lat']
            longitude = data['results'][0]['geometry']['location']['lng']
            return latitude, longitude
        else:
            print(f"  - Geocoding failed for address: {address}. Status: {data['status']}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"  - An error occurred: {e}")
        return None, None

# 1. Load your CSV file into a pandas DataFrame
try:
    df = pd.read_csv(INPUT_FILE)
except FileNotFoundError:
    print(f"Error: The file '{INPUT_FILE}' was not found. Make sure it's in the same directory as the script.")
    exit()

# 2. Create empty columns for the coordinates
df['latitude'] = None
df['longitude'] = None

print("Starting geocoding process...")

# 3. Loop through each row in the DataFrame
for index, row in df.iterrows():
    # Construct the full address from your columns
    # Note: Using .get(column, '') provides a default empty string if a column is missing
    address_parts = [
        str(row.get('address_line1', '')),
        str(row.get('city', '')),
        str(row.get('state', '')),
        str(row.get('postal_code', ''))
    ]
    full_address = ", ".join(part for part in address_parts if part) # Join non-empty parts

    print(f"Processing row {index + 1}/{len(df)}: {full_address}")

    # Get coordinates for the address
    lat, lng = get_coordinates(full_address)
    
    # Update the DataFrame with the new coordinates
    df.at[index, 'latitude'] = lat
    df.at[index, 'longitude'] = lng
    
    # A small delay to respect API usage limits and avoid errors
    time.sleep(0.1)

# 4. Save the updated DataFrame to a new CSV file
df.to_csv(OUTPUT_FILE, index=False)

print(f"\n✅ Geocoding complete! The updated data has been saved to '{OUTPUT_FILE}'.")
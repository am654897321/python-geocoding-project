import pandas as pd
import re
import io
from collections import Counter # Import the Counter tool

def load_tonnage_key(file_path='York Tonnage Key.csv'):
    """
    Loads the tonnage key CSV, forcing the first column to be read as text
    to preserve leading zeros.
    """
    try:
        with open(file_path, 'r') as f:
            file_content = f.read()
        
        clean_content = file_content.replace('"', '')
        
        # dtype={0: str} forces the first column (index 0) to be read as a string.
        df = pd.read_csv(io.StringIO(clean_content), dtype={0: str})

        # --- Rename columns for consistency ---
        df = df.rename(columns={
            df.columns[0]: 'capacity_code',
            df.columns[1]: 'tons'
        })
        
        return df
        
    except FileNotFoundError:
        print(f"ERROR: The tonnage key file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading the key file: {e}")
        return None

def parse_and_price(text, tonnage_key_df):
    """
    Main function to parse messy text, decode models, count quantities, and apply pricing.
    """
    if tonnage_key_df is None:
        return {"error": "Tonnage key file not loaded."}

    # --- 1. IDENTIFICATION RULES ---
    serial_patterns = [
        r'(?<![A-Z09])(?=[A-Z09]*\d)[A-Z09]{10}(?![A-Z09])',
        r'(?i)(?:serial\s?no?\.?#?|s/n|sn)\s*([A-Z09-]{10,})'
    ]
    for pattern in serial_patterns:
        text = re.sub(pattern, '', text)

    model_pattern = r'\b[A-Z]{2}(?:\d{3}|\d{2}[A-Z])[A-Z09-]*\b'
    
    # --- NEW: Count all model occurrences ---
    all_models_found = [m.upper() for m in re.findall(model_pattern, text, re.IGNORECASE)]
    model_counts = Counter(all_models_found)
    
    # Get a unique list but keep original order
    unique_models_in_order = sorted(model_counts.keys(), key=all_models_found.index)
    
    priced_items = []
    needs_clarification = []
    
    # --- 2. DECODING AND PRICING ---
    for model, quantity in model_counts.items():
        first_five = re.sub(r'[^A-Z09]', '', model)[:5]
        capacity_code = None
        
        if len(first_five) >= 5 and first_five[2:5].isdigit(): # AA999 format
            capacity_code = first_five[2:5]
        elif len(first_five) >= 4 and first_five[2:4].isdigit(): # AA99A format
            capacity_code = first_five[2:4]

        if capacity_code:
            match = tonnage_key_df[tonnage_key_df['capacity_code'] == capacity_code]
            if not match.empty:
                tons = float(match['tons'].iloc[0])
                unit_price = 0
                tier = "unknown"

                if 3.0 <= tons <= 10.0:
                    unit_price = 725
                elif tons in {12.5, 15, 17.5, 20, 25, 27.5}:
                    unit_price = 850

                if unit_price > 0:
                    priced_items.append({
                        "model": model,
                        "quantity": quantity, # Add quantity
                        "tons": tons,
                        "unit_price": unit_price,
                        "line_total": unit_price * quantity # Add line total
                    })
                else:
                    needs_clarification.append({"model": model, "quantity": quantity, "reason": f"Tonnage of {tons} is not in a valid pricing tier."})
            else:
                needs_clarification.append({"model": model, "quantity": quantity, "reason": f"Capacity code '{capacity_code}' not found in key."})
        else:
            needs_clarification.append({"model": model, "quantity": quantity, "reason": "Could not decode a valid capacity code."})

    # --- 3. SUMMARIZE RESULTS ---
    grand_total = sum(item['line_total'] for item in priced_items)
    
    return {
        "priced_items": priced_items,
        "needs_clarification": needs_clarification,
        "summary": {
            "grand_total": grand_total,
            "priced_units_count": sum(item['quantity'] for item in priced_items),
            "total_units_count": len(all_models_found)
        }
    }

def extract_address(text):
    """A simple regex to find a likely street address."""
    pattern = r'\d{3,}\s+[\w\s\.\,\#]+\b(?:[A-Z]{2})\b\s+\d{5}'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None
# pricing.py

import pandas as pd
import re

def load_tonnage_key(file_path='York Tonnage Key.csv'):
    """Loads the tonnage key CSV, treating capacity_code as text."""
    try:
        # Crucially, treat the key column as a string to preserve leading zeros
        return pd.read_csv(file_path, dtype={'capacity_code': str})
    except FileNotFoundError:
        print(f"ERROR: The tonnage key file '{file_path}' was not found.")
        return None

def parse_and_price(text, tonnage_key_df):
    """
    Main function to parse messy text, decode models, and apply pricing.
    """
    if tonnage_key_df is None:
        return {"error": "Tonnage key file not loaded."}

    # --- 1. IDENTIFICATION RULES ---
    
    # Ignore serial numbers first
    serial_patterns = [
        r'(?<![A-Z0-9])(?=[A-Z0-9]*\d)[A-Z0-9]{10}(?![A-Z0-9])',
        r'(?i)(?:serial\s?no?\.?#?|s/n|sn)\s*([A-Z0-9-]{10,})'
    ]
    for pattern in serial_patterns:
        text = re.sub(pattern, '', text)

    # Find model candidates
    model_pattern = r'\b[A-Z]{2}(?:\d{3}|\d{2}[A-Z])[A-Z0-9-]*\b'
    # Find all unique models in order of appearance
    seen = set()
    models_in_order = [m.upper() for m in re.findall(model_pattern, text, re.IGNORECASE) if not (m.upper() in seen or seen.add(m.upper()))]
    
    priced_items = []
    needs_clarification = []
    
    # --- 2. DECODING AND PRICING ---
    
    for model in models_in_order:
        # Extract the first 5 chars and then the code
        first_five = re.sub(r'[^A-Z0-9]', '', model)[:5]
        capacity_code = None
        
        if len(first_five) >= 5 and first_five[2:5].isdigit(): # AA999 format
            capacity_code = first_five[2:5]
        elif len(first_five) >= 4 and first_five[2:4].isdigit(): # AA99A format
            capacity_code = first_five[2:4]

        # Lookup in the tonnage key
        if capacity_code:
            match = tonnage_key_df[tonnage_key_df['capacity_code'] == capacity_code]
            if not match.empty:
                tons = float(match['tons'].iloc[0])
                unit_price = 0
                tier = "unknown"

                if 3.0 <= tons <= 10.0:
                    unit_price = 725
                    tier = "small_3_to_10"
                elif tons in {12.5, 15, 17.5, 20, 25, 27.5}:
                    unit_price = 850
                    tier = "large_12_5_to_27_5"

                if unit_price > 0:
                    priced_items.append({
                        "model": model,
                        "tons": tons,
                        "unit_price": unit_price,
                        "tier": tier
                    })
                else:
                    needs_clarification.append({"model": model, "reason": f"Tonnage of {tons} is not in a valid pricing tier."})
            else:
                needs_clarification.append({"model": model, "reason": f"Capacity code '{capacity_code}' not found in key."})
        else:
            needs_clarification.append({"model": model, "reason": "Could not decode a valid capacity code."})

    # --- 3. SUMMARIZE RESULTS ---
    
    grand_total = sum(item['unit_price'] for item in priced_items)
    
    return {
        "priced_items": priced_items,
        "needs_clarification": needs_clarification,
        "summary": {
            "grand_total": grand_total,
            "priced_units_count": len(priced_items),
            "total_units_count": len(models_in_order)
        }
    }

def extract_address(text):
    """A simple regex to find a likely street address."""
    # This pattern looks for a common address format. It can be improved if needed.
    pattern = r'\d{3,}\s+[\w\s\.\,\#]+\b(?:[A-Z]{2})\b\s+\d{5}'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None
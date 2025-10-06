import pandas as pd
import re
import io
from collections import Counter

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

    # --- 1. IDENTIFICATION RULES (Corrected) ---
    serial_patterns = [
        r'(?<![A-Z0-9])(?=[A-Z0-9]*\d)[A-Z0-9]{10}(?![A-Z0-9])',
        r'(?i)(?:serial\s?no?\.?#?|s/n|sn)\s*([A-Z0-9-]{10,})'
    ]
    for pattern in serial_patterns:
        text = re.sub(pattern, '', text)

    model_pattern = r'\b[A-Z]{2}(?:\d{3}|\d{2}[A-Z])[A-Z0-9-]*\b'
    
    all_models_found = [m.upper() for m in re.findall(model_pattern, text, re.IGNORECASE)]
    model_counts = Counter(all_models_found)
    
    priced_items = []
    needs_clarification = []
    
    # --- 2. DECODING AND PRICING (Corrected) ---
    for model, quantity in model_counts.items():
        first_five = re.sub(r'[^A-Z0-9]', '', model)[:5]
        capacity_code = None
        
        if len(first_five) >= 5 and first_five[2:5].isdigit():
            capacity_code = first_five[2:5]
        elif len(first_five) >= 4 and first_five[2:4].isdigit():
            capacity_code = first_five[2:4]

        if capacity_code:
            match = tonnage_key_df[tonnage_key_df['capacity_code'] == capacity_code]
            if not match.empty:
                tons = float(match['tons'].iloc[0])
                unit_price = 0

                if 3.0 <= tons <= 10.0:
                    unit_price = 725
                elif tons in {12.5, 15, 17.5, 20, 25, 27.5}:
                    unit_price = 850

                if unit_price > 0:
                    priced_items.append({
                        "model": model,
                        "quantity": quantity,
                        "tons": tons,
                        "unit_price": unit_price,
                        "line_total": unit_price * quantity
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

# --- EXAMPLE USAGE / TEST BLOCK ---
# This entire block must have ZERO indentation.
if __name__ == "__main__":
    sample_email_text = """
    Hi team,

    Please price out the following units for the job at 123 Main Street, Anytown, CA 90210.

    The first unit is a York model ZF037. Its serial is W1C2345678.
    We also have a rooftop unit, model number PC99A, serial # E9D8765432.
    Finally, there's an older one, model XX123, which might need clarification.

    Thanks!
    """

    print("--- Starting Pricing Test ---")
    
    tonnage_key = load_tonnage_key('York Tonnage Key.csv')
    
    if tonnage_key is not None:
        results = parse_and_price(sample_email_text, tonnage_key)
        
        import json
        print("\n--- Parsed Results ---")
        print(json.dumps(results, indent=2))
        
        print("\n--- Testing Address Extraction ---")
        address = extract_address(sample_email_text)
        print(f"Extracted Address: {address}")
    else:
        print("Test could not run because the tonnage key file was not found.")
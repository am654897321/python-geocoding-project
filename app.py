# app.py

from flask import Flask, request, jsonify
# Import your two logic modules
from pricing import parse_and_price, load_tonnage_key, extract_address
from find_partners import find_closest_partners

# --- INITIALIZATION ---
app = Flask(__name__)
# Load the tonnage key ONCE when the app starts for maximum speed
TONNAGE_KEY_DF = load_tonnage_key() 

# --- API ENDPOINT ---
@app.route('/api/process_request', methods=['POST'])
def process_full_request():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided in request"}), 400

    messy_text = data['text']

    # --- 1. Get Pricing Info ---
    pricing_results = parse_and_price(messy_text, TONNAGE_KEY_DF)

    # --- 2. Get Partner Info ---
    work_address = extract_address(messy_text)
    partner_results = None
    if work_address:
        partner_results = find_closest_partners(work_address)
    else:
        partner_results = {"error": "Could not extract a valid address from the text."}

    # --- 3. Combine and Return ---
    final_response = {
        "pricing_analysis": pricing_results,
        "partner_locator": partner_results
    }
    
    return jsonify(final_response)

# Note: The old '/api/find_closest' route is no longer needed
# but is left here for reference if you want to keep it.

if __name__ == "__main__":
    # This allows you to test the app locally if you want
    app.run(debug=True, port=5001)
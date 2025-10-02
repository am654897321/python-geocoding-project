from flask import Flask, request, jsonify
from find_partners import find_closest_partners # Imports your function

# Initialize the Flask application
app = Flask(__name__)

# Define a single endpoint for our API
@app.route('/api/find_closest', methods=['POST'])
def handle_find_closest():
    # Get the data that the GPT will send
    data = request.get_json()
    
    # Check if the 'address' key exists in the sent data
    if not data or 'address' not in data:
        return jsonify({"error": "Address not provided"}), 400
        
    customer_address = data['address']
    
    # Call your original function to do the work
    closest = find_closest_partners(customer_address)
    
    # Return the results back to the GPT
    return jsonify(closest)

# This part is for testing on your local machine
if __name__ == "__main__":
    app.run(debug=True, port=5001)
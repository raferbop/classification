from quart import Quart, jsonify, render_template, request
from utils.get_hs_code import generate_product_info_async
from utils.get_commodity_code import process_product_info
from utils.filter_commodity_code import find_best_commodity_match

app = Quart(__name__)

@app.route("/")
async def index():
    """Render the main search page"""
    return await render_template("index.html")

@app.route("/process", methods=["POST"])
async def process_product():
    """Handle web form submission and return JSON response"""
    form = await request.form
    product_name = form.get("product_name", "").strip()

    if not product_name:
        return jsonify({
            "error": "Please enter a valid product name."
        }), 400

    # Step 1: Generate initial product info with HS codes
    product_info = await generate_product_info_async(product_name)
    if not product_info:
        return jsonify({
            "error": "Error processing product information."
        }), 400

    # Step 2: Get matching commodity codes from database
    product_info = process_product_info(product_info)

    # Step 3: Find best matching commodity code
    if 'matching_commodity_info' in product_info:
        commodity_codes = [code for code, _ in product_info['matching_commodity_info']]
        matching_code_info = [
            {"code": code, "description": description} 
            for code, description in product_info['matching_commodity_info']
        ]

        result = await find_best_commodity_match(
            product_info['type'],
            product_info['information'],
            commodity_codes,
            matching_code_info
        )

        product_info['best_commodity_code'] = result['best_code']
        product_info['best_commodity_reasoning'] = result['reasoning']

    return jsonify({"product_info": product_info})

@app.route("/api/classify", methods=["POST"])
async def classify_product():
    """API endpoint to classify a product and return its commodity code"""
    try:
        data = await request.get_json()
        if not data or 'product_name' not in data:
            return jsonify({
                "error": "Product name is required"
            }), 400

        product_name = data["product_name"].strip()
        if not product_name:
            return jsonify({
                "error": "Product name cannot be empty"
            }), 400

        # Get initial product classification
        product_info = await generate_product_info_async(product_name)
        if not product_info:
            return jsonify({
                "error": "Could not classify product"
            }), 400

        # Get commodity codes
        product_info = process_product_info(product_info)
        
        # Find best matching code
        if 'matching_commodity_info' in product_info:
            commodity_codes = [code for code, _ in product_info['matching_commodity_info']]
            matching_code_info = [
                {"code": code, "description": description} 
                for code, description in product_info['matching_commodity_info']
            ]

            result = await find_best_commodity_match(
                product_info['type'],
                product_info['information'],
                commodity_codes,
                matching_code_info
            )

            # Get description for the best matching code
            description = next(
                (info["description"] for info in matching_code_info 
                 if info["code"] == result['best_code']), 
                None
            )

            return jsonify({
                "commodity_code": result['best_code'],
                "description": description,
                "reasoning": result['reasoning']
            })

        return jsonify({
            "error": "No matching commodity code found"
        }), 404

    except Exception as e:
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

# Error handlers
@app.errorhandler(404)
async def not_found(error):
    return jsonify({
        "error": "Resource not found"
    }), 404

@app.errorhandler(405)
async def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed"
    }), 405

@app.errorhandler(400)
async def bad_request(error):
    return jsonify({
        "error": "Bad request"
    }), 400

@app.errorhandler(500)
async def internal_server_error(error):
    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == "__main__":
    app.run(debug=True)
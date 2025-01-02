import openai
import json
import os
from .config import load_api_keys

# Initialize OpenAI client with API key from environment
try:
    config = load_api_keys()
    client = openai.OpenAI(api_key=config['openai_api_key'])
except Exception as e:
    raise ValueError(f"Failed to initialize OpenAI client: {e}")

def find_best_commodity_match(product_type, product_info, commodity_codes, matching_code_info):
    """
    Analyzes the best commodity code match for a product based on its type and information.

    Args:
        product_type: The product type extracted from the product information.
        product_info: A dictionary containing information about the product.
        commodity_codes: A list of commodity codes.
        matching_code_info: A list of dictionaries containing commodity code descriptions.

    Returns:
        dict: A dictionary containing the best matching code and the reasoning behind the selection
    """
    # Debugging: Print input data
    print(f"Product Type: {product_type}")
    print(f"Product Info: {product_info}")
    print(f"Commodity Codes: {commodity_codes}")
    print("Matching Code Info:")
    for info in matching_code_info:
        print(f"  Code: {info['code']}, Description: {info['description']}")

    # Generate the prompt for ChatGPT
    prompt = f"""I have analyzed a product and its information:
Product type: {product_type}
Product information: {product_info}

The extracted commodity codes are: {commodity_codes}
Here are the descriptions for each code:

"""
    for info in matching_code_info:
        if 'description' in info:
            prompt += f"\n* Code: {info['code']}\n{info['description']}"

    prompt += "\nBased on the product type, information, and available commodity code descriptions, which code is the best match and why? Please explain your reasoning and highlight key similarities or discrepancies."

    # Debugging: Print the generated prompt
    print("Generated Prompt:")
    print(prompt)

    # Use OpenAI's Chat model to analyze the prompt
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=400,
    )

    # Debugging: Print the raw response
    print("Raw AI Response:")
    print(response)

    # Extract reasoning from response
    reasoning = response.choices[0].message.content.strip()

    # Debugging: Print the extracted reasoning
    print("Extracted Reasoning:")
    print(reasoning)

    # Parse the response to find the best matching commodity code
    best_code = None
    
    # Look for explicit mention of best/recommended code
    if "best match" in reasoning.lower():
        for info in matching_code_info:
            if info['code'] in reasoning and any(phrase in reasoning.lower() for phrase in ["best match", "most appropriate", "best option"]):
                paragraph = next((p for p in reasoning.split('\n\n') if info['code'] in p and any(phrase in p.lower() for phrase in ["best match", "most appropriate", "best option"])), None)
                if paragraph:
                    best_code = info['code']
                    break
    
    # If no best match found, look for positive justification
    if not best_code:
        for info in matching_code_info:
            if info['code'] in reasoning:
                paragraph = next((p for p in reasoning.split('\n\n') if info['code'] in p), None)
                if paragraph and any(positive in paragraph.lower() for positive in ["aligns", "matches", "appropriate", "suitable", "correct"]):
                    best_code = info['code']
                    break

    # If still no match found, use the first code as fallback
    if not best_code and matching_code_info:
        best_code = matching_code_info[0]['code']
        reasoning = "No clear best match was identified. Using first available code as default."

    # Debugging: Print the identified best code
    print(f"Identified Best Commodity Code: {best_code}")
    print(f"Final Reasoning: {reasoning}")

    # Return both the code and reasoning in a structured format
    return {
        'best_code': best_code,
        'reasoning': reasoning
    }
import json
import os
import pandas as pd
from pathlib import Path
from .config import load_api_keys

# Get the directory where the script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, '..', 'data', 'commodity_code.csv')

def load_commodity_codes():
    """Load commodity codes from CSV file."""
    try:
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded commodity codes CSV with {len(df)} entries")
        return df
    except Exception as e:
        print(f"Error loading commodity codes CSV: {e}")
        return None

def find_commodity_codes(extracted_hs_codes, df):
    """Find matching commodity codes from the CSV data."""
    matching_info = []
    try:
        for hs_code in extracted_hs_codes:
            formatted_hs_code = int(hs_code.replace('.', '')[:6])
            print(f"Searching for matching commodity codes for HS code: {formatted_hs_code}")
            
            # Filter DataFrame for matching HS codes
            matches = df[df['hs_code'] == formatted_hs_code]

            if not matches.empty:
                # Convert matches to list of tuples (code, description)
                for _, row in matches.iterrows():
                    matching_info.append((row['code'], row['description']))
                print(f"Found {len(matches)} matches for HS code {formatted_hs_code}:")
                for code, description in matching_info:
                    print(f"\t- Code: {code}, Description: {description}")
            else:
                print(f"No matching code found for HS code {formatted_hs_code}")
                    
    except Exception as e:
        print(f"Error while finding commodity codes: {e}")
    
    return matching_info

def process_product_info(product_info):
    """Process product information and find matching commodity codes."""
    extracted_hs_codes = product_info.get("hs_codes", [])
    if extracted_hs_codes:
        print(f"Processing HS code(s): {extracted_hs_codes}")
        try:
            # Load CSV data
            df = load_commodity_codes()
            if df is not None:
                matching_info = find_commodity_codes(extracted_hs_codes, df)
                product_info["matching_commodity_info"] = matching_info
            else:
                print("Failed to load commodity codes from CSV.")
        except Exception as e:
            print(f"Error during processing: {e}")
    return product_info

# Load API configuration
try:
    config = load_api_keys()
    if not config.get('openai_api_key'):
        raise ValueError("OpenAI API key not found in configuration")
except Exception as e:
    print(f"Error loading API configuration: {e}")

if __name__ == "__main__":
    # Example usage if run as a script
    sample_product_info = {
        "hs_codes": ["8471.30", "8471.41"]
    }
    result = process_product_info(sample_product_info)
    print("\nProcessed Product Info:")
    print(json.dumps(result, indent=2))
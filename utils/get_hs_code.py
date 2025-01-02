import openai
import re
import json
import os
import logging
import anthropic
from pathlib import Path
from groq import Groq
import requests
from typing import List, Optional, Dict, Any, Tuple
from .config import load_api_keys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HSCodeGenerator:
    def __init__(self):
        """Initialize the HS Code Generator with multiple AI service clients."""
        try:
            self.config = self._load_config()
            self.openai_client = self._initialize_openai()
            self.claude_client = self._initialize_claude()
            self.groq_client = self._initialize_groq()
            # Gemini doesn't need initialization, just the API key
        except Exception as e:
            logger.error(f"Error initializing HSCodeGenerator: {e}")
            raise

    def _load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables."""
        try:
            return load_api_keys()
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise

    def _initialize_openai(self) -> openai.OpenAI:
        """Initialize OpenAI client."""
        return openai.OpenAI(api_key=self.config['openai_api_key'])

    def _initialize_claude(self) -> anthropic.Anthropic:
        """Initialize Claude client."""
        return anthropic.Anthropic(api_key=self.config['claude_api_key'])

    def _initialize_groq(self) -> Groq:
        """Initialize Groq client."""
        return Groq(api_key=self.config['groq_api_key'])

    def get_product_type(self, product_name: str) -> str:
        """Get product type using OpenAI."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in product classification."},
                    {"role": "user", "content": f"What is the product type and category for {product_name}?"}
                ],
                temperature=0.5,
                max_tokens=200
            )
            product_type = response.choices[0].message.content
            logger.info(f"Product Type: {product_type}")
            return product_type
        except Exception as e:
            logger.error(f"Error getting product type: {str(e)}")
            raise

    def get_product_info(self, product_name: str) -> str:
        """Get detailed product information using OpenAI."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in product descriptions."},
                    {"role": "user", "content": f"Provide detailed information about {product_name}, including material composition, primary use, and distinctive features."}
                ],
                temperature=0.5,
                max_tokens=200
            )
            product_info = response.choices[0].message.content
            logger.info(f"Product Information: {product_info}")
            return product_info
        except Exception as e:
            logger.error(f"Error getting product info: {str(e)}")
            raise

    def get_openai_hs_codes(self, product_type: str, product_info: str) -> str:
        """Get HS codes using OpenAI."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert in HS code classification."},
                    {"role": "user", "content": f"Based on the HS Nomenclature 2017 edition, provide the most specific 6-digit HS code classification for {product_type} and {product_info}."}
                ],
                temperature=0.5,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting OpenAI HS codes: {str(e)}")
            return ""

    def get_claude_hs_codes(self, product_type: str, product_info: str) -> str:
        """Get HS codes using Claude."""
        try:
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": f"Based on the HS Nomenclature 2017 edition, provide the most specific 6-digit HS code classification for {product_type} and {product_info}."}
                ]
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Error getting Claude HS codes: {str(e)}")
            return ""

    def get_gemini_hs_codes(self, product_type: str, product_info: str) -> str:
        """Get HS codes using Gemini."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={self.config['gemini_api_key']}"
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{
                        "text": f"Based on the HS Nomenclature 2017 edition, provide the most specific 6-digit HS code classification for {product_type} and {product_info}."
                    }]
                }]
            }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"Error getting Gemini HS codes: {str(e)}")
            return ""

    def get_groq_hs_codes(self, product_type: str, product_info: str) -> str:
        """Get HS codes using Groq."""
        try:
            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert in HS code classification."},
                    {"role": "user", "content": f"Based on the HS Nomenclature 2017 edition, provide the most specific 6-digit HS code classification for {product_type} and {product_info}."}
                ],
                model="llama3-8b-8192",
                max_tokens=200,
                temperature=0.5
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting Groq HS codes: {str(e)}")
            return ""

    def extract_hs_codes(self, text: str) -> List[str]:
        """Extract HS codes from text response."""
        if not text:
            return []
        pattern = re.compile(r'\b\d{4}\.\d{2}\b|\b\d{6}\b|\b\d{8}\b')
        matches = pattern.findall(text)
        formatted_codes = [match.replace('.', '')[:6] for match in matches]
        return list(set(formatted_codes))

    def get_consolidated_hs_codes(self, product_type: str, product_info: str) -> List[str]:
        """Get HS codes from all available AI services and consolidate results."""
        hs_codes_map = {
            'OpenAI': self.get_openai_hs_codes(product_type, product_info),
            'Claude': self.get_claude_hs_codes(product_type, product_info),
            'Gemini': self.get_gemini_hs_codes(product_type, product_info),
            'Groq': self.get_groq_hs_codes(product_type, product_info)
        }

        # Extract and log codes from each service
        all_codes = set()
        for service, response in hs_codes_map.items():
            codes = self.extract_hs_codes(response)
            logger.info(f"HS Codes from {service}: {', '.join(codes)}")
            all_codes.update(codes)

        return list(all_codes) if all_codes else ["No HS codes found"]

    def get_classification_rule(self, product_info: str, hs_code: str, product_type: str) -> str:
        """Get classification rule for the product."""
        try:
            prompt = f"Based on the general rules for the interpretation of the harmonized system, which rule, from 1-6, was used to classify the product? Product Type: {product_type}, Product Information: {product_info}"
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting classification rule: {str(e)}")
            return "Classification rule unavailable"

    def generate_product_info(self, product_name: str) -> Dict[str, Any]:
        """Generate complete product information including HS codes from all services."""
        try:
            product_type = self.get_product_type(product_name)
            product_info = self.get_product_info(product_name)
            hs_codes = self.get_consolidated_hs_codes(product_type, product_info)
            
            # Get classification rules for each HS code
            classification_rules = {}
            for hs_code in hs_codes:
                if hs_code != "No HS codes found":
                    classification_rules[hs_code] = self.get_classification_rule(product_info, hs_code, product_type)

            return {
                "name": product_name,
                "type": product_type,
                "information": product_info,
                "hs_codes": hs_codes,
                "classification_rules": classification_rules,
                "sources": {
                    "openai": self.extract_hs_codes(self.get_openai_hs_codes(product_type, product_info)),
                    "claude": self.extract_hs_codes(self.get_claude_hs_codes(product_type, product_info)),
                    "gemini": self.extract_hs_codes(self.get_gemini_hs_codes(product_type, product_info)),
                    "groq": self.extract_hs_codes(self.get_groq_hs_codes(product_type, product_info))
                }
            }
        except Exception as e:
            logger.error(f"Error generating product information: {str(e)}")
            return None

# Global instance of HSCodeGenerator
_generator = None

def get_generator() -> HSCodeGenerator:
    """Get or create a global instance of HSCodeGenerator."""
    global _generator
    if _generator is None:
        _generator = HSCodeGenerator()
    return _generator

def generate_product_info(product_name: str) -> Dict[str, Any]:
    """
    Standalone function to generate product information and HS codes.
    This is the main entry point used by the Flask application.
    
    Args:
        product_name (str): Name of the product to analyze
        
    Returns:
        Dict[str, Any]: Dictionary containing product information and HS codes
    """
    try:
        generator = get_generator()
        result = generator.generate_product_info(product_name)
        
        if result is None:
            logger.error("Failed to generate product information")
            return None
        
        return result
    except Exception as e:
        logger.error(f"Error in generate_product_info: {str(e)}")
        return None

if __name__ == "__main__":
    # Example usage
    product_name = input("Enter product name: ")
    result = generate_product_info(product_name)
    
    if result:
        print("\nProduct Analysis Results:")
        print(f"Name: {result['name']}")
        print(f"Type: {result['type']}")
        print(f"Information: {result['information']}")
        print("\nHS Codes by Source:")
        for source, codes in result['sources'].items():
            print(f"{source.capitalize()}: {', '.join(codes)}")
        print(f"\nConsolidated HS Codes: {', '.join(result['hs_codes'])}")
        print("\nClassification Rules:")
        for hs_code, rule in result.get('classification_rules', {}).items():
            print(f"HS Code {hs_code}: {rule}")
    else:
        print("Failed to generate product information.")
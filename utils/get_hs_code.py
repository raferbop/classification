import re
import json
import os
import logging
import aiohttp
import asyncio
import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import load_api_keys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HSCodeGenerator:
    def __init__(self):
        """Initialize the HS Code Generator with OpenRouter client."""
        try:
            self.config = self._load_config()
            self.api_key = self.config['openrouter_api_key']
            self.base_url = "https://openrouter.ai/api/v1"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost:5000",  
                "Content-Type": "application/json",
                "X-Title": "HS Code Classifier"
            }
            # Updated models configuration
            self.models = {
                "primary": "openai/gpt-4o-mini",
                "alternates": [
                    "meta-llama/llama-3.3-70b-instruct",
                    "anthropic/claude-3.5-haiku",
                    "nvidia/llama-3.1-nemotron-70b-instruct"
                ]
            }
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

    async def _make_openrouter_request(self, 
                                     prompt: str, 
                                     model: str = None,
                                     temperature: float = 0.5,
                                     max_tokens: int = 1000) -> str:
        """
        Make a request to OpenRouter API.
        
        Args:
            prompt: The prompt to send to the model
            model: The specific model to use (defaults to primary model)
            temperature: Controls randomness in the response
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            str: The model's response text or empty string on failure
        """
        if model is None:
            model = self.models["primary"]

        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/chat/completions"
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert in international trade classification and HS codes."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error for model {model}: {error_text}")
                        return ""
                    
                    result = await response.json()
                    return result['choices'][0]['message']['content']
            except Exception as e:
                logger.error(f"Error making OpenRouter request with model {model}: {str(e)}")
                return ""

    async def get_product_type(self, product_name: str) -> str:
        """Get product type using OpenRouter."""
        prompt = f"""Analyze the following product and provide its specific product type and category:
Product: {product_name}

Please provide a clear and specific product type that would be relevant for HS code classification.
Focus on physical characteristics and primary function rather than brand or marketing terms."""
        
        response = await self._make_openrouter_request(
            prompt=prompt,
            model=self.models["primary"],
            temperature=0.3,
            max_tokens=200
        )
        
        logger.info(f"Product type determination for {product_name}: {response[:100]}...")
        return response

    async def get_product_info(self, product_name: str) -> str:
        """Get detailed product information using OpenRouter."""
        prompt = f"""Provide detailed information about the following product:
Product: {product_name}

Please include:
1. Material composition
2. Primary use/function
3. Key features and characteristics
4. Technical specifications
5. Industry/sector categorization

Focus on details that would be relevant for HS code classification.
Be specific about physical characteristics and functional aspects."""
        
        response = await self._make_openrouter_request(
            prompt=prompt,
            model=self.models["primary"],
            temperature=0.3,
            max_tokens=500
        )
        
        logger.info(f"Product info generated for {product_name}: {response[:100]}...")
        return response

    async def get_classification_rule(self, 
                                    product_info: str, 
                                    hs_code: str, 
                                    product_type: str) -> str:
        """Get classification rule for the product."""
        prompt = f"""Based on the General Rules for the Interpretation (GRI) of the Harmonized System,
which rule (1-6) was primarily used to classify this product?

Product Type: {product_type}
Product Information: {product_info}
Assigned HS Code: {hs_code}

Please explain which GRI rule applies and why, with specific reference to the product's characteristics."""
        
        response = await self._make_openrouter_request(
            prompt=prompt,
            model=self.models["primary"],
            temperature=0.2,
            max_tokens=300
        )
        
        logger.info(f"Classification rule determined for HS code {hs_code}: {response[:100]}...")
        return response

    async def get_hs_codes(self, product_type: str, product_info: str) -> str:
        """
        Get HS codes using multiple models via OpenRouter for consensus.
        Makes parallel requests to different models and aggregates their responses
        for more reliable classification through consensus.
        """
        prompt = f"""Based on the HS Nomenclature 2017 edition, determine the most specific 
6-digit HS code classification for the following product:

Product Type: {product_type}
Product Information: {product_info}

You must provide exactly ONE 6-digit HS code that is most appropriate for this product. Do not suggest alternative classifications.

Please respond with:
1. A single 6-digit HS code in XXXX.XX format
2. A brief explanation of why this classification is the most appropriate

Your response must contain exactly one HS code."""
        
        # Make parallel requests to all models simultaneously
        tasks = []
        model_mapping = {}
        
        # Add primary model
        tasks.append(self._make_openrouter_request(prompt, self.models["primary"]))
        provider, model_name = self.models["primary"].split('/')
        model_mapping[len(tasks)-1] = {"name": model_name, "provider": provider}
        
        # Add alternate models
        for model in self.models["alternates"]:
            tasks.append(self._make_openrouter_request(prompt, model))
            provider, model_name = model.split('/')
            model_mapping[len(tasks)-1] = {"name": model_name, "provider": provider}
        
        # Get all responses in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process responses and map them to sources with extracting codes
        sources = {}
        for idx, response in enumerate(responses):
            model_info = model_mapping[idx]
            source_name = f"{model_info['provider']}/{model_info['name']}"
            
            if isinstance(response, Exception):
                logger.error(f"Error from {source_name}: {str(response)}")
                sources[source_name] = {
                    "response": "",
                    "codes": []
                }
            else:
                logger.info(f"Received valid response from {source_name}")
                codes = self.extract_hs_codes(response)
                sources[source_name] = {
                    "response": response,
                    "codes": codes
                }
                logger.info(f"Extracted codes from {source_name}: {codes}")
        
        return json.dumps({"sources": sources})

    def extract_hs_codes(self, text: str) -> List[str]:
        """
        Extract HS codes from text response.
        
        Handles various formats:
        - XXXX.XX
        - XXXXXX
        - XXXX.XX.XX
        """
        if not text:
            return []
        
        # Pattern matches both 6-digit formats (with or without period)
        pattern = re.compile(r'\b\d{4}\.\d{2}\b|\b\d{6}\b|\b\d{4}\.\d{2}\.\d{2}\b')
        matches = pattern.findall(text)
        
        # Normalize to 6-digit format without periods
        formatted_codes = [match.replace('.', '')[:6] for match in matches]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_codes = [x for x in formatted_codes if not (x in seen or seen.add(x))]
        
        logger.info(f"Extracted HS codes: {unique_codes}")
        return unique_codes

    async def generate_product_info_async(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Generate complete product information asynchronously.
        
        Args:
            product_name: Name of the product to classify
            
        Returns:
            Dictionary containing product information and classifications,
            or None if an error occurs
        """
        try:
            logger.info(f"Starting analysis for product: {product_name}")
            
            # Get product type and info concurrently
            product_type, product_info = await asyncio.gather(
                self.get_product_type(product_name),
                self.get_product_info(product_name)
            )
            
            if not product_type or not product_info:
                logger.error("Failed to get product type or info")
                return None
            
            # Get HS codes from multiple models
            hs_codes_response = await self.get_hs_codes(product_type, product_info)
            response_data = json.loads(hs_codes_response)
            
            # Extract codes from all sources and track their origin
            all_hs_codes = set()
            codes_by_source = {}
            
            for source, data in response_data["sources"].items():
                codes = data.get("codes", [])
                response_text = data.get("response", "")
                if codes:
                    all_hs_codes.update(codes)
                    codes_by_source[source] = {
                        "codes": codes,
                        "response": response_text
                    }
            
            hs_codes = list(all_hs_codes) if all_hs_codes else ["No HS codes found"]
            
            if hs_codes == ["No HS codes found"]:
                logger.warning("No HS codes found in responses")
                classification_rules = {}
            else:
                # Get classification rules for each HS code concurrently
                rule_tasks = [
                    self.get_classification_rule(product_info, hs_code, product_type)
                    for hs_code in hs_codes
                ]
                rules = await asyncio.gather(*rule_tasks)
                classification_rules = dict(zip(hs_codes, rules))

            result = {
                "name": product_name,
                "type": product_type,
                "information": product_info,
                "hs_codes": hs_codes,
                "classification_rules": classification_rules,
                "sources": codes_by_source,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            logger.info(f"Completed analysis for product: {product_name}")
            return result
            
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

async def generate_product_info_async(product_name: str) -> Optional[Dict[str, Any]]:
    """Async entry point for application."""
    try:
        generator = get_generator()
        result = await generator.generate_product_info_async(product_name)
        
        if result is None:
            logger.error("Failed to generate product information")
            return None
        
        return result
    except Exception as e:
        logger.error(f"Error in generate_product_info_async: {str(e)}")
        return None

if __name__ == "__main__":
    async def main():
        product_name = input("Enter product name: ")
        result = await generate_product_info_async(product_name)
        
        if result:
            print("\nProduct Analysis Results:")
            print(f"Name: {result['name']}")
            print(f"Type: {result['type']}")
            print(f"Information: {result['information']}")
            print("\nHS Codes by Source:")
            for source, data in result['sources'].items():
                print(f"\n{source}:")
                print(f"Codes: {', '.join(data['codes'])}")
                print("Response:")
                print(data['response'])
            print("\nConsolidated HS Codes:")
            print(', '.join(result['hs_codes']))
            print("\nClassification Rules:")
            for hs_code, rule in result.get('classification_rules', {}).items():
                print(f"\nHS Code {hs_code}:")
                print(f"Rule: {rule}")
            print(f"\nAnalysis Timestamp: {result['timestamp']}")
        else:
            print("Failed to generate product information.")

    asyncio.run(main())
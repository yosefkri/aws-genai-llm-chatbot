import json
import os
import boto3
import urllib.parse
import urllib.request
import time
import random
import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TavilySearch:
    """
    A class to handle Tavily search API integration for retrieving web search results
    when the LLM doesn't know the answer.
    """
    
    BEDROCK_REGION = os.environ.get('BEDROCK_REGION', 'eu-central-1')
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Base delay in seconds
    
    @staticmethod
    def get_tavily_api_key():
        """
        Retrieve the Tavily API key from AWS Secrets Manager
        """
        # Get the ARN of the secret from environment variable
        secret_arn = os.environ.get('TAVILY_API_KEY_SECRET_ARN')
        if not secret_arn:
            logger.error("TAVILY_API_KEY_SECRET_ARN environment variable is not set")
            raise ValueError("TAVILY_API_KEY_SECRET_ARN environment variable is not set")
            
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=TavilySearch.BEDROCK_REGION
        )
        
        try:
            # Get the secret value
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_arn
            )
            apiKey = get_secret_value_response.get('SecretString')
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            raise e
        
        return apiKey

    @staticmethod
    def make_tavily_request(endpoint, payload, retries=0):
        """ Make a request to any Tavily API endpoint with retry logic
        
        Args:
            endpoint (str): API endpoint path (e.g., 'search', 'extract', 'crawl')
            payload (dict): Request payload
            retries (int): Current retry count

        Returns:
            dict: JSON response from Tavily
        """
        base_url = f"https://api.tavily.com/{endpoint}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Add API key to payload
        try:
            payload["api_key"] = TavilySearch.get_tavily_api_key()
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return {"error": f"Failed to get API key: {str(e)}"}

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(base_url, data=data, headers=headers)

        try:
            logger.info(f"Making request to {base_url}")
            response = urllib.request.urlopen(request)
            response_data = response.read().decode("utf-8")
            logger.info("Received response from Tavily API")
            
            # Parse and return JSON response
            return json.loads(response_data)
                
        except urllib.error.HTTPError as e:
            logger.error(f"Error calling Tavily API: {e}")
            
            # Implement exponential backoff with jitter for retries
            if retries < TavilySearch.MAX_RETRIES:
                # Calculate delay with exponential backoff and jitter
                delay = (TavilySearch.RETRY_DELAY_BASE ** retries) + random.uniform(0, 1)
                logger.info(f"Retrying in {delay:.2f} seconds (attempt {retries + 1}/{TavilySearch.MAX_RETRIES})")
                time.sleep(delay)
                return TavilySearch.make_tavily_request(endpoint, payload, retries + 1)
            
            return {"error": f"API request failed after {TavilySearch.MAX_RETRIES} retries: {str(e)}"}

    @staticmethod
    def search(search_query, **kwargs):
        """ Execute a Tavily AI search
        
        Args:
            search_query (str): Query string
            **kwargs: Optional parameters (search_depth, include_images, etc.)

        Returns:
            dict: JSON response from Tavily search API
        """
        # Default parameters
        payload = {
            "query": search_query,
            "search_depth": "basic"
        }

        # Add any additional parameters
        for key, value in kwargs.items():
            if value is not None:
                payload[key] = value

        return TavilySearch.make_tavily_request("search", payload)

    @staticmethod
    def detect_dont_know(response: str) -> bool:
        """
        Detect if the LLM response indicates it doesn't know the answer.
        
        Args:
            response (str): The LLM response text
            
        Returns:
            bool: True if the response indicates the LLM doesn't know, False otherwise
        """
        # Common phrases that indicate the LLM doesn't know the answer
        dont_know_phrases = [
            "I don't know",
            "I don't have",
            "I'm not sure",
            "I am not sure",
            "I do not know",
            "I do not have",
            "I cannot provide",
            "I can't provide",
            "I don't have access to",
            "I don't have information",
            "I don't have enough information",
            "I don't have current information",
            "I don't have real-time",
            "I cannot access",
            "I cannot browse",
            "I don't have the ability to search",
            "I don't have the capability to access",
            "I don't have up-to-date information",
            "I'm not able to search",
            "I'm not able to browse",
            "I'm not connected to the internet",
            "I don't have internet access",
            "My knowledge is limited to",
            "My training data only includes",
            "My training cut-off",
            "As an AI language model, I don't have access to",
            "Je ne sais pas",
            "Je n'ai pas",
            "Je ne suis pas sûr",
            "Je ne peux pas fournir",
            "Je n'ai pas accès à",
            "Je n'ai pas d'informations",
            "Je n'ai pas suffisamment d'informations",
            "Je ne connais pas",
            "אני לא יודע",
            "אין לי מידע",
            "אין לי גישה",
            "אני לא בטוח",
            "המידע אינו זמין",
            "אין ברשותי מידע"
        ]
        
        # Convert response to lowercase for case-insensitive matching
        response_lower = response.lower()
        
        # Check for any of the phrases in the response
        for phrase in dont_know_phrases:
            if phrase.lower() in response_lower:
                return True
                
        return False

    @staticmethod
    def format_search_results(results: Dict[str, Any]) -> str:
        """
        Format the search results into a readable string for the LLM.
        
        Args:
            results (dict): The search results from Tavily
            
        Returns:
            str: Formatted search results
        """
        if "error" in results:
            return f"Error retrieving search results: {results['error']}"
            
        formatted_text = "### SEARCH RESULTS ###\n\n"
        
        # Add search metadata
        formatted_text += f"Query: {results.get('query', 'Unknown query')}\n"
        formatted_text += f"Search time: {results.get('time', 0):.2f} seconds\n\n"
        
        # Add search results
        if "results" in results and results["results"]:
            for i, result in enumerate(results["results"], 1):
                formatted_text += f"Result {i}:\n"
                formatted_text += f"Title: {result.get('title', 'No title')}\n"
                formatted_text += f"URL: {result.get('url', 'No URL')}\n"
                formatted_text += f"Content: {result.get('content', 'No content')}\n\n"
        else:
            formatted_text += "No search results found.\n\n"
            
        return formatted_text

    @staticmethod
    def enhance_prompt_with_search_results(original_query: str, search_results: Optional[Dict[str, Any]] = None) -> str:
        """
        Create an enhanced prompt that combines the original query with search results.
        
        Args:
            original_query (str): The user's original query
            search_results (dict, optional): The search results from Tavily
            
        Returns:
            str: Enhanced prompt with search results
        """
        enhanced_prompt = "I need you to answer the user's question using the search results provided below.\n\n"
        enhanced_prompt += f"User's original question: {original_query}\n\n"
        
        if search_results:
            formatted_results = TavilySearch.format_search_results(search_results)
            enhanced_prompt += formatted_results
        else:
            enhanced_prompt += "No search results are available.\n\n"
            
        enhanced_prompt += "Based on the search results above, please provide a comprehensive answer to the user's question. "
        enhanced_prompt += "Include relevant information from the search results and cite sources where appropriate. "
        enhanced_prompt += "If the search results don't contain relevant information, acknowledge this and provide the best answer you can "
        enhanced_prompt += "based on your knowledge, clearly indicating what information comes from your knowledge versus the search results."
        
        return enhanced_prompt

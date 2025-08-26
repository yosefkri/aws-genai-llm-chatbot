import os
from aws_lambda_powertools import Logger
from adapters.bedrock.base import BedrockChatAdapter
from adapters.shared.tavily_search import TavilySearch

logger = Logger()

class BedrockChatWithSearchAdapter(BedrockChatAdapter):
    """
    Extension of BedrockChatAdapter that adds web search capability using Tavily
    when the LLM responds with "DONT_KNOW".
    """
    
    def __init__(self, *args, **kwargs):
        logger.info("Initializing BedrockChatWithSearchAdapter")
        super().__init__(*args, **kwargs)
        
    def run(
        self,
        prompt,
        workspace_id=None,
        images=[],
        documents=[],
        videos=[],
        user_groups=[],
        system_prompts={},
        *args,
        **kwargs,
    ):
        """
        Override the run method to add web search capability.
        
        This method first gets a response from the LLM. If the response indicates
        the LLM doesn't know the answer (contains "DONT_KNOW"), it performs a web search
        using Tavily, then sends a new prompt with the search results to the LLM.
        """
        logger.info(f"BedrockChatWithSearchAdapter.run with prompt: {prompt[:100]}...")
        
        # Get initial response from the LLM
        initial_response = super().run(
            prompt,
            workspace_id,
            images,
            documents,
            videos,
            user_groups,
            system_prompts,
            *args,
            **kwargs,
        )
        
        # Check if the response indicates the LLM doesn't know the answer
        if TavilySearch.detect_dont_know(initial_response.get("content", "")):
            logger.info("LLM responded with DONT_KNOW, performing web search")
            
            try:
                # Perform web search using Tavily
                search_results = TavilySearch.search(prompt)
                
                if "error" in search_results:
                    logger.error(f"Error performing web search: {search_results['error']}")
                    return initial_response
                
                # Create enhanced prompt with search results
                enhanced_prompt = TavilySearch.enhance_prompt_with_search_results(
                    prompt, search_results
                )
                
                logger.info(f"Created enhanced prompt with search results: {enhanced_prompt[:100]}...")
                
                # Get final response from the LLM with the enhanced prompt
                final_response = super().run(
                    enhanced_prompt,
                    workspace_id,
                    images,
                    documents,
                    videos,
                    user_groups,
                    system_prompts,
                    *args,
                    **kwargs,
                )
                
                # Add metadata about the web search
                if "metadata" in final_response:
                    final_response["metadata"]["webSearch"] = {
                        "performed": True,
                        "query": prompt,
                        "resultsCount": len(search_results.get("results", [])),
                    }
                
                return final_response
                
            except Exception as e:
                logger.exception(f"Error during web search: {e}")
                # If there's an error during web search, return the original response
                return initial_response
        
        # If the LLM knows the answer, return the original response
        return initial_response

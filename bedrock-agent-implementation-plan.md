# Bedrock Agent Implementation Plan for AWS GenAI LLM Chatbot

## Overview

This document outlines the plan to add Amazon Bedrock agent support to the AWS GenAI LLM Chatbot. The implementation will allow users to configure and use Bedrock agents through the chatbot interface.

## Current Architecture

The AWS GenAI LLM Chatbot currently supports:
- Multiple LLM providers (Bedrock, SageMaker, etc.)
- RAG capabilities with various data stores
- Bedrock Knowledge Bases
- Guardrails for responsible AI

## Implementation Steps

### 1. Update System Configuration Types

**File**: `lib/shared/types.ts`

Extend the `SystemConfig` interface to include Bedrock agent configuration:
- Add an `agent` property to the existing `bedrock` configuration
- Include fields for `enabled`, `agentId`, and `agentVersion`
- This will allow the system to store and access Bedrock agent configuration

### 2. Update Configuration CLI

**File**: `cli/magic-config.ts`

Add prompts for Bedrock agent configuration:
- Add questions after the existing Bedrock configuration section
- First ask if the user wants to enable Bedrock agent (only if Bedrock is enabled)
- If enabled, prompt for agent ID and version
- Update the configuration object creation to include agent settings
- Ensure the configuration is properly saved to the config.json file

### 3. Create Bedrock Agent Client Module

Create a new module for Bedrock agent integration:

**Directory**: `lib/shared/layers/python-sdk/python/genai_core/bedrock_agent/`

- Create a client module to handle communication with the Bedrock agent API
- Implement functions to get a Bedrock agent client
- Handle cross-account access if needed (similar to existing Bedrock KB implementation)
- Create initialization files to expose the client functions

### 4. Create Bedrock Agent Adapter

**File**: `lib/model-interfaces/langchain/functions/request-handler/adapters/bedrock_agent.py`

- Create an adapter class that extends the BaseAdapter
- Implement the necessary methods to interact with Bedrock agents
- Handle agent responses and format them for the chatbot interface
- Register the adapter in the registry to make it available for use

### 5. Update Lambda Function for Query Processing

**File**: `lib/model-interfaces/langchain/functions/request-handler/index.py`

- Update the request handler to support Bedrock agent queries
- Modify the `handle_run` function to detect when to use the Bedrock agent adapter
- Ensure proper error handling for agent-specific errors
- Pass agent configuration from environment variables to the adapter

### 6. Update Environment Variables in Lambda Function

**File**: `lib/chatbot-api/appsync-ws.ts`

- Add environment variables for Bedrock agent configuration
- Pass the agent ID and version from the system configuration to the Lambda function
- Ensure the Lambda function has the necessary permissions to invoke Bedrock agents

### 7. Update AppSync Schema (if needed)

**File**: `lib/chatbot-api/schema/schema.graphql`

- Determine if any schema changes are needed to support Bedrock agent operations
- If needed, add new types, queries, or mutations for agent-specific functionality

### 8. Update Application Model

**Files**: 
- `lib/chatbot-api/functions/api-handler/routes/applications.py`
- Related UI components

- Update the application model to include Bedrock agent as a model option
- Ensure the UI can display and select Bedrock agent models
- Add any agent-specific configuration options to the application settings

### 9. Testing and Validation

- Test the configuration flow to ensure agent settings are properly saved
- Test the integration with Bedrock agent using sample queries
- Validate the responses from Bedrock agent are properly formatted and displayed
- Test error handling for various failure scenarios

## Implementation Sequence

1. Start with updating the configuration types and CLI to allow users to configure Bedrock agent
2. Implement the client and adapter for Bedrock agent
3. Update the Lambda function to process Bedrock agent queries
4. Update the AppSync schema and application model as needed
5. Test the implementation thoroughly

## Considerations

- **Security**: Ensure proper IAM permissions for accessing Bedrock agents
- **Cross-account access**: Support for using Bedrock agents in different AWS accounts
- **Error handling**: Proper handling of agent-specific errors
- **User experience**: Clear indication when interacting with an agent vs. a regular LLM
- **Monitoring**: Add appropriate logging and monitoring for agent interactions

## Future Enhancements

- Support for agent aliases and versions
- Integration with agent action groups
- Support for agent knowledge bases
- UI improvements for agent-specific features

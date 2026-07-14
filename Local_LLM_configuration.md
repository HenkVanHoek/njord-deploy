# Local LLM Configuration: NjordDeploy Expert

This guide describes the process for configuring a specialized Mistral-based model optimized for the NjordDeploy codebase on a system with an RTX 3060 (12GB VRAM).

## 1. Create the Model file
Create a text file named njorddeploy.mf using vi. This file contains the parameters and system instructions essential for context stability and architectural quality.

    FROM mistral-nemo
    # Optimized context window for stability on 12GB VRAM
    PARAMETER num_ctx 90000
    # Low temperature for factual and technical accuracy
    PARAMETER temperature 0.3

    SYSTEM """
    You are an expert software architect specialized in the NjordDeploy project.
    You have full access to the codebase and assist in its maintenance and improvement.

    Critical Directives:
    1. YAML passwords/secrets must always be enclosed in double quotes.
    2. Python code must adhere to PEP 8 with a maximum line length of 88 characters.
    3. Use 4-space indentation for all code blocks in markdown documentation.
    4. Never make assumptions; always ask for the latest file version before proposing changes.
    5. Use the Unpacking-First Mandate for list access to prevent generator faults.
    """

## 2. Build the Model in Ollama
Run the following command in your terminal to create the model on your local machine based on the Model file.

    ollama create njorddeploy-expert -f njorddeploy.mf

## 3. Usage and Context Ingestion
Once the model is created, it will appear as an option in Open WebUI. For deep architectural analysis or complex debugging:
1. Start a new session with the njorddeploy-expert model.
2. Drag and drop your generated llm_context.txt (optimized at ~86k tokens) into the chat.
3. Provide your prompt; the AI now has the full mental map of your logic within the safe limits of your hardware.

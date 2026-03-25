from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()


def llm_initiate():
    """Initialize Azure OpenAI LLM."""
    return AzureChatOpenAI(
        openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        model_name=os.getenv("AZURE_OPENAI_API_MODEL_NAME"),
        temperature=0.1
    )
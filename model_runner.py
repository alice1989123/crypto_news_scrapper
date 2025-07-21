import os
import requests
from openai import OpenAI
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

llama_cpp_host = os.getenv("LLAMA_HOST" )

if not llama_cpp_host:
    logger.error("LLAMA_HOST environment variable is not set")

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "eu-central-1"))
    try:
        response = ssm.get_parameter(
            Name="/scraper/OPENAI_API_KEY",
            WithDecryption=True
        )
        return response["Parameter"]["Value"]
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError("Failed to retrieve OpenAI API key from SSM") from e


def call_llm(prompt, host=f"http://{llama_cpp_host}:8081", n_predict=1000):
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.1
    }

    try:
        response = requests.post(f"{host}/completion", json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("content", "").strip()
    
    # Fallback to OpenAI
    except requests.RequestException as e:
        print(f"Error calling LLM: {e}")
        raise Exception(f"Failed to call LLM at {host}: {e}")
            

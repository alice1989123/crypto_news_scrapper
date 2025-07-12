import os
import requests
from openai import OpenAI
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

llama_cpp_host = os.getenv("LLAMA_CPP_HOST" )

if not llama_cpp_host:
    logger.error("LLAMA_CPP_HOST environment variable is not set")

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


def call_llm(prompt, host="http://llama_cpp_host:8081", n_predict=1000):
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.1
    }

    # Try local LLaMA first
    try:
        response = requests.post(f"{host}/completion", json=payload, timeout=5)
        response.raise_for_status()
        return response.json().get("content", "").strip()
    
    # Fallback to OpenAI
    except requests.RequestException as e:
        print(f"⚠️ Local LLaMA not available, falling back to OpenAI: {e}")
        try:
            api_key = get_openai_api_key()
            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional crypto news summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()

        except Exception as openai_error:
            print(f"❌ Failed to call OpenAI: {openai_error}")
            return "Error: could not get response from LLaMA or OpenAI"

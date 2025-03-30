# llama_runner.py
import os
import requests
from openai import OpenAI
import boto3
from botocore.exceptions import BotoCoreError, ClientError


def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # If not in environment, fetch from SSM Parameter Store
    ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "eu-central-1"))
    try:
        response = ssm.get_parameter(
            Name="/scraper/openai_api_key",
            WithDecryption=True
        )
        return response["Parameter"]["Value"]
    except (BotoCoreError, ClientError) as e:
        raise RuntimeError("Failed to retrieve OpenAI API key from SSM") from e

client = OpenAI(api_key=get_openai_api_key())


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(prompt, host="http://10.66.66.1:8081", n_predict=1000):
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.1
    }

    try:
        response = requests.post(f"{host}/completion", json=payload, timeout=5)
        response.raise_for_status()
        return response.json().get("content", "").strip()
    except requests.RequestException as e:
        print(f"⚠️ Local LLaMA not available, falling back to OpenAI: {e}")
        try:
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

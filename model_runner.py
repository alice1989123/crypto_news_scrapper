# llama_runner.py
import os
import requests
from openai import OpenAI

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

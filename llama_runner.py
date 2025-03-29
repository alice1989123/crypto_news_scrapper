# llama_runner.py
import requests

def call_local_llama(prompt, host="http://10.66.66.1:8081", n_predict=1000):
    payload = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.1
    }

    try:
        response = requests.post(f"{host}/completion", json=payload)
        response.raise_for_status()
        return response.json().get("content", "").strip()
    except requests.RequestException as e:
        print(f"❌ HTTP error calling LLaMA: {e}")
        return "Error: could not reach local LLaMA server"

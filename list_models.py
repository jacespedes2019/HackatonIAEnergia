import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load env vars if you use .env
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in your environment")

genai.configure(api_key=API_KEY)

def main():
    # List all models available for your API key
    for m in genai.list_models():
        # m.supported_generation_methods might include "generateContent"
        print(m.name, "->", m.supported_generation_methods)

if __name__ == "__main__":
    main()
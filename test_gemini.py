from dotenv import load_dotenv
import os
from google import generativeai as genai

# Load variables from .env into environment
load_dotenv()

# Access key AFTER load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Debug: Ensure full key is read
assert api_key is not None, "❌ API key not found"
# assert api_key.startswith("AIza"), f"❌ Invalid key format: {api_key}"

genai.configure(api_key=api_key)

# Test
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("can you browse the web and look for current job openings for remote software developers? from india")
print(response.text)

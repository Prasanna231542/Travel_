from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import requests
import tempfile
import base64
import os

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

# ============================================
# FLASK APP
# ============================================

app = Flask(__name__)
CORS(app)

# ============================================
# API KEYS
# ============================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

# Check whether API keys are available
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env file")

if not MURF_API_KEY:
    raise ValueError("MURF_API_KEY is missing from .env file")

# ============================================
# GEMINI CLIENT
# ============================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)

# ============================================
# PROMPTS
# ============================================

PROMPTS = {

    "Summary": """
You are a professional tourist guide.
Provide a high-level overview of "{place}" in {language}.

Focus on:
- The historical significance
- Why the place is famous
- Key architectural or cultural highlights

Keep the explanation concise, engaging, and easy to follow.
Avoid excessive details and dates.
Limit the response to around 200 words.

Respond ONLY in {language}.
""",

    "Detailed": """
You are a professional tourist guide.
Provide a detailed and immersive explanation of "{place}" in {language}.

Cover:
- Historical background and timeline
- Architectural design and unique features
- Cultural importance and notable events
- Interesting facts and visitor insights

Explain concepts clearly and in a storytelling manner.
Include relevant details and examples to create a rich experience.
Limit the response to around 400 words.

Respond ONLY in {language}.
"""
}

# ============================================
# GENERATE SPEECH USING MURF
# ============================================

def generate_speech(text, voice_id, locale):

    temp_audio = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    )

    url = "https://global.api.murf.ai/v1/speech/stream"

    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "voice_id": voice_id,
        "text": text,
        "locale": locale,
        "model": "FALCON",
        "format": "MP3",
        "sampleRate": 24000,
        "channelType": "MONO"
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    if response.status_code == 200:

        with open(temp_audio.name, "wb") as f:

            for chunk in response.iter_content(
                chunk_size=1024
            ):

                if chunk:
                    f.write(chunk)

                    print(
                        f"Received {len(chunk)} bytes"
                    )

        print("Audio streaming completed")

    else:

        print(
            f"Error: {response.status_code}"
        )

        print(response.text)

    return temp_audio


# ============================================
# GENERATE DESCRIPTION USING GEMINI
# ============================================

def generate_description(place, answer_type, language):

    prompt = PROMPTS[answer_type].format(
        place=place,
        language=language
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return response.text


# ============================================
# AUDIO GUIDE API
# ============================================

@app.route(
    "/generate-audio-guide",
    methods=["POST"]
)
def generate_audio_guide():

    try:

        data = request.json

        place = data["place"]
        answer_type = data["answerType"]
        language = data["language"]
        voice_id = data["voiceId"]
        locale = data["locale"]

        # Generate tourist description
        text_description = generate_description(
            place,
            answer_type,
            language
        )

        # Convert description to speech
        audio_path = generate_speech(
            text_description,
            voice_id,
            locale
        )

        # Read generated audio
        with open(
            audio_path.name,
            "rb"
        ) as audio_file:

            audio_bytes = audio_file.read()

        # Convert audio to Base64
        encoded_audio = base64.b64encode(
            audio_bytes
        ).decode("utf-8")

        return {
            "description": text_description,
            "audioBase64": encoded_audio
        }

    except Exception as e:

        print("Error:", str(e))

        return {
            "error": str(e)
        }, 500


# ============================================
# RUN FLASK SERVER
# ============================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
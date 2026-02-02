---
title: Movie Recap Generator
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
license: mit
---

# Movie Recap Generator

Transform long movies into 2-minute recap videos with AI-generated voiceover narration.

## Features

- **Video Upload**: Upload movie files (MP4, MKV, AVI, MOV)
- **AI Transcription**: Automatically transcribes audio using OpenAI Whisper
- **Smart Summarization**: Generates concise 2-minute recap scripts using GPT-4
- **Natural Voiceover**: Creates professional voiceover using Edge-TTS (free!)
- **Scene Extraction**: Intelligently selects key scenes from the movie
- **Video Compilation**: Combines clips with voiceover into final recap

## Tech Stack

- **UI**: Gradio
- **Video Processing**: MoviePy, OpenCV, FFmpeg
- **Transcription**: OpenAI Whisper
- **AI**: OpenAI GPT-4
- **Text-to-Speech**: Edge-TTS (Microsoft - Free)

## Deploy on Hugging Face Spaces (FREE)

### Step 1: Create a Hugging Face Account
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up for a free account

### Step 2: Create a New Space
1. Click your profile icon → "New Space"
2. Choose a name (e.g., `movie-recap-generator`)
3. Select **Docker** as the SDK
4. Choose **CPU basic** (free) or **GPU** for faster processing
5. Click "Create Space"

### Step 3: Upload Files
Upload these files to your Space:
- `gradio_app.py`
- `Dockerfile`
- `requirements.txt`
- `services/` folder (all files)

### Step 4: Add Secrets
Go to Settings → Variables and secrets → New secret:
- Name: `OPENAI_API_KEY`
- Value: Your OpenAI API key

### Step 5: Your App is Live!
Your app will be available at: `https://huggingface.co/spaces/YOUR_USERNAME/movie-recap-generator`

## Local Development

### Prerequisites
- Python 3.10+
- FFmpeg installed on your system
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd aibot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_key_here

# Run Gradio app
python gradio_app.py

# Or run Flask app
python app.py
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `WHISPER_MODEL` | Whisper model size (tiny/base/small/medium/large) | No (default: base) |
| `TTS_VOICE` | Edge-TTS voice name | No (default: en-US-GuyNeural) |

## How It Works

1. **Upload**: User uploads a movie file
2. **Extract Audio**: Audio track is extracted from the video
3. **Transcribe**: Whisper transcribes the audio to text
4. **Summarize**: GPT-4 generates a 2-minute recap script
5. **Generate Voice**: Edge-TTS creates voiceover from the script
6. **Extract Scenes**: Key scenes are identified and extracted
7. **Compile**: Final video is assembled with voiceover

## Alternative Free Hosting Options

### Option 1: Hugging Face Spaces (Recommended)
- **Pros**: Free GPU, persistent storage, easy deployment
- **Cons**: Queue times during high traffic
- **URL**: huggingface.co/spaces

### Option 2: Google Colab + Gradio
- **Pros**: Free GPU, full control
- **Cons**: Temporary (shuts down after idle)
- Run `gradio_app.py` in Colab with `share=True`

### Option 3: Railway (Free Tier)
- **Pros**: Easy Docker deployment
- **Cons**: Limited hours per month
- **URL**: railway.app

## Docker Deployment

```bash
# Build the image
docker build -t movie-recap .

# Run locally
docker run -p 7860:7860 -e OPENAI_API_KEY=your_key movie-recap

# Open http://localhost:7860
```

## API Endpoints (Flask Version)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/upload` | POST | Upload video file |
| `/api/process/<job_id>` | POST | Start processing |
| `/api/status/<job_id>` | GET | Check job status |
| `/api/download/<job_id>` | GET | Download recap video |

## License

MIT License

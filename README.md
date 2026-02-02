# Movie Recap Generator

A web application that transforms long movies into 2-minute recap videos with AI-generated voiceover narration.

## Features

- **Video Upload**: Upload movie files (MP4, MKV, AVI, MOV)
- **AI Transcription**: Automatically transcribes audio using OpenAI Whisper
- **Smart Summarization**: Generates concise 2-minute recap scripts using GPT-4
- **Natural Voiceover**: Creates professional voiceover using Edge-TTS
- **Scene Extraction**: Intelligently selects key scenes from the movie
- **Video Compilation**: Combines clips with voiceover into final recap

## Tech Stack

- **Backend**: Flask (Python)
- **Video Processing**: MoviePy, OpenCV, FFmpeg
- **Transcription**: OpenAI Whisper
- **AI**: OpenAI GPT-4
- **Text-to-Speech**: Edge-TTS (Microsoft)
- **Frontend**: Bootstrap 5, Vanilla JavaScript

## Setup

### Prerequisites

- Python 3.10+
- FFmpeg installed on your system
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd aibot
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open http://localhost:5000 in your browser

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `WHISPER_MODEL` | Whisper model size (tiny/base/small/medium/large) | No (default: base) |
| `TTS_VOICE` | Edge-TTS voice name | No (default: en-US-GuyNeural) |
| `MAX_VIDEO_SIZE_MB` | Maximum upload size in MB | No (default: 2000) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/upload` | POST | Upload video file |
| `/api/process/<job_id>` | POST | Start processing |
| `/api/status/<job_id>` | GET | Check job status |
| `/api/download/<job_id>` | GET | Download recap video |

## How It Works

1. **Upload**: User uploads a movie file
2. **Extract Audio**: Audio track is extracted from the video
3. **Transcribe**: Whisper transcribes the audio to text
4. **Summarize**: GPT-4 generates a 2-minute recap script
5. **Generate Voice**: Edge-TTS creates voiceover from the script
6. **Extract Scenes**: Key scenes are identified and extracted
7. **Compile**: Final video is assembled with voiceover

## Deployment

### Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Add environment variables in Render dashboard

### Docker

```bash
docker build -t movie-recap .
docker run -p 5000:5000 -e OPENAI_API_KEY=your_key movie-recap
```

## License

MIT License

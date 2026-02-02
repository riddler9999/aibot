"""
Movie Recap Generator - Gradio Interface for Hugging Face Spaces
Transforms long movies into 2-minute recap videos with AI voiceover
"""

import os
import uuid
import tempfile
import shutil
import gradio as gr
from pathlib import Path

# Set environment variables for caching
os.environ["TRANSFORMERS_CACHE"] = "/tmp/transformers_cache"
os.environ["HF_HOME"] = "/tmp/hf_home"

# Import services
from services.video_processor import VideoProcessor
from services.transcriber import Transcriber
from services.summarizer import Summarizer
from services.tts import TextToSpeech
from services.compiler import VideoCompiler


def process_movie(
    video_file,
    movie_title,
    genre,
    voice_style,
    progress=gr.Progress()
):
    """
    Main processing function for movie recap generation

    Args:
        video_file: Uploaded video file path
        movie_title: Title of the movie
        genre: Movie genre
        voice_style: TTS voice selection
        progress: Gradio progress tracker

    Returns:
        Tuple of (output_video_path, script_text, status_message)
    """
    if video_file is None:
        return None, "", "Please upload a video file."

    if not movie_title.strip():
        return None, "", "Please enter a movie title."

    # Create temp directory for this job
    job_id = str(uuid.uuid4())[:8]
    job_folder = os.path.join(tempfile.gettempdir(), f"recap_{job_id}")
    os.makedirs(job_folder, exist_ok=True)

    try:
        # Step 1: Analyze video
        progress(0.05, desc="Analyzing video...")
        video_processor = VideoProcessor(video_file)
        video_info = video_processor.get_video_info()

        # Step 2: Extract audio
        progress(0.10, desc="Extracting audio from video...")
        audio_path = video_processor.extract_audio(job_folder)

        # Step 3: Transcribe audio
        progress(0.20, desc="Transcribing audio (this may take a while)...")
        transcriber = Transcriber()
        transcript = transcriber.transcribe(audio_path)

        # Step 4: Generate recap script
        progress(0.45, desc="Generating recap script with AI...")
        summarizer = Summarizer()
        recap_script = summarizer.generate_recap(
            transcript,
            movie_title,
            genre
        )

        narration = recap_script.get('narration', '')

        # Step 5: Generate voiceover
        progress(0.55, desc="Creating voiceover narration...")
        tts = TextToSpeech(voice=voice_style)
        voiceover_path = tts.generate(narration, job_folder)

        # Step 6: Extract key scenes
        progress(0.70, desc="Extracting key scenes from movie...")
        scene_timestamps = recap_script.get('scene_timestamps', [])
        scenes = video_processor.extract_scenes(scene_timestamps, job_folder)

        if not scenes:
            progress(0.75, desc="Using default scene extraction...")
            scenes = video_processor.extract_scenes([], job_folder)

        # Step 7: Compile final video
        progress(0.85, desc="Compiling final recap video...")
        compiler = VideoCompiler()
        output_path = compiler.compile(
            scenes,
            voiceover_path,
            job_folder,
            f"{movie_title} - 2 Min Recap"
        )

        progress(1.0, desc="Complete!")

        # Format script for display
        script_display = f"""## {movie_title} - 2 Minute Recap

### Narration Script:
{narration}

### Key Moments:
"""
        for i, moment in enumerate(recap_script.get('key_moments', []), 1):
            script_display += f"\n{i}. {moment}"

        return output_path, script_display, f"Recap generated successfully! Duration: ~2 minutes"

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing video: {error_msg}")
        return None, "", f"Error: {error_msg}"

    finally:
        # Cleanup temp files (except output)
        try:
            for item in os.listdir(job_folder):
                item_path = os.path.join(job_folder, item)
                if item_path != output_path and os.path.isfile(item_path):
                    os.remove(item_path)
        except:
            pass


def create_demo():
    """Create the Gradio interface"""

    # Voice options
    voice_choices = [
        ("Guy (US Male)", "en-US-GuyNeural"),
        ("Jenny (US Female)", "en-US-JennyNeural"),
        ("Ryan (UK Male)", "en-GB-RyanNeural"),
        ("Sonia (UK Female)", "en-GB-SoniaNeural"),
        ("Davis (Dramatic)", "en-US-DavisNeural"),
        ("Tony (Storyteller)", "en-US-TonyNeural"),
    ]

    genre_choices = [
        "Action", "Comedy", "Drama", "Horror", "Sci-Fi",
        "Romance", "Thriller", "Documentary", "Animation", "Fantasy"
    ]

    # Custom CSS
    css = """
    .gradio-container {
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    .title {
        text-align: center;
        margin-bottom: 1rem;
    }
    .description {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    """

    with gr.Blocks(css=css, title="Movie Recap Generator") as demo:
        gr.Markdown(
            """
            # Movie Recap Generator
            ### Transform long movies into 2-minute recap videos with AI voiceover

            Upload your movie, and our AI will:
            1. Transcribe the dialogue using Whisper
            2. Generate an engaging recap script with GPT
            3. Create professional voiceover narration
            4. Extract key scenes and compile the final video
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                # Input section
                video_input = gr.Video(
                    label="Upload Movie",
                    sources=["upload"],
                )

                movie_title = gr.Textbox(
                    label="Movie Title",
                    placeholder="Enter the movie title...",
                    max_lines=1
                )

                genre = gr.Dropdown(
                    choices=genre_choices,
                    value="Drama",
                    label="Genre"
                )

                voice = gr.Dropdown(
                    choices=voice_choices,
                    value="en-US-GuyNeural",
                    label="Narrator Voice"
                )

                generate_btn = gr.Button(
                    "Generate 2-Minute Recap",
                    variant="primary",
                    size="lg"
                )

            with gr.Column(scale=1):
                # Output section
                output_video = gr.Video(
                    label="Generated Recap",
                    interactive=False
                )

                status_output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    max_lines=2
                )

        # Script output (collapsible)
        with gr.Accordion("View Generated Script", open=False):
            script_output = gr.Markdown(
                label="Narration Script"
            )

        # Examples
        gr.Markdown(
            """
            ### Tips:
            - For best results, upload movies in MP4 format
            - Processing time depends on video length (typically 5-15 minutes)
            - The AI generates a ~300 word narration script for 2 minutes
            - Key scenes are automatically selected from throughout the movie
            """
        )

        # Connect the button
        generate_btn.click(
            fn=process_movie,
            inputs=[video_input, movie_title, genre, voice],
            outputs=[output_video, script_output, status_output],
            show_progress=True
        )

    return demo


# Create and launch the app
if __name__ == "__main__":
    demo = create_demo()
    demo.queue(max_size=5)  # Enable queue for long-running tasks
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )

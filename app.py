"""
Movie Recap Generator - Main Flask Application
Transforms long movies into 2-minute recap videos with AI voiceover
"""

import os
import uuid
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv

from services.video_processor import VideoProcessor
from services.transcriber import Transcriber
from services.summarizer import Summarizer
from services.tts import TextToSpeech
from services.compiler import VideoCompiler

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_VIDEO_SIZE_MB', 2000)) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'output')

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory job storage (use Redis in production)
jobs = {}

ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'avi', 'mov', 'webm', 'wmv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_video_job(job_id):
    """Background task to process video and create recap"""
    job = jobs[job_id]

    try:
        video_path = job['video_path']
        job_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        os.makedirs(job_folder, exist_ok=True)

        # Step 1: Extract audio
        job['status'] = 'extracting_audio'
        job['progress'] = 10
        video_processor = VideoProcessor(video_path)
        audio_path = video_processor.extract_audio(job_folder)
        job['progress'] = 20

        # Step 2: Transcribe audio
        job['status'] = 'transcribing'
        job['progress'] = 25
        transcriber = Transcriber()
        transcript = transcriber.transcribe(audio_path)
        job['transcript'] = transcript
        job['progress'] = 40

        # Step 3: Generate recap script
        job['status'] = 'generating_script'
        job['progress'] = 45
        summarizer = Summarizer()
        recap_script = summarizer.generate_recap(
            transcript,
            job.get('movie_title', 'Unknown Movie'),
            job.get('genre', 'Drama')
        )
        job['recap_script'] = recap_script
        job['progress'] = 55

        # Step 4: Generate voiceover
        job['status'] = 'generating_voiceover'
        job['progress'] = 60
        tts = TextToSpeech()
        voiceover_path = tts.generate(recap_script['narration'], job_folder)
        job['progress'] = 70

        # Step 5: Extract key scenes
        job['status'] = 'extracting_scenes'
        job['progress'] = 75
        scene_timestamps = recap_script.get('scene_timestamps', [])
        scenes = video_processor.extract_scenes(scene_timestamps, job_folder)
        job['progress'] = 85

        # Step 6: Compile final video
        job['status'] = 'compiling'
        job['progress'] = 90
        compiler = VideoCompiler()
        output_path = compiler.compile(
            scenes,
            voiceover_path,
            job_folder,
            recap_script.get('title', f"{job.get('movie_title', 'Movie')} - 2 Min Recap")
        )
        job['progress'] = 100

        # Cleanup
        job['status'] = 'completed'
        job['output_path'] = output_path
        job['completed_at'] = datetime.now().isoformat()

    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        print(f"Job {job_id} failed: {e}")


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video file upload"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save file
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{job_id}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get metadata from form
    movie_title = request.form.get('title', 'Unknown Movie')
    genre = request.form.get('genre', 'Drama')

    # Create job
    jobs[job_id] = {
        'id': job_id,
        'status': 'uploaded',
        'progress': 0,
        'video_path': filepath,
        'movie_title': movie_title,
        'genre': genre,
        'created_at': datetime.now().isoformat(),
        'filename': file.filename
    }

    return jsonify({
        'job_id': job_id,
        'message': 'Video uploaded successfully',
        'filename': file.filename
    })


@app.route('/api/process/<job_id>', methods=['POST'])
def start_processing(job_id):
    """Start video processing"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    if job['status'] not in ['uploaded', 'failed']:
        return jsonify({'error': f'Cannot process job in status: {job["status"]}'}), 400

    # Start background processing
    job['status'] = 'processing'
    job['progress'] = 5

    thread = threading.Thread(target=process_video_job, args=(job_id,))
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Processing started',
        'job_id': job_id
    })


@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    response = {
        'id': job['id'],
        'status': job['status'],
        'progress': job.get('progress', 0),
        'movie_title': job.get('movie_title'),
        'created_at': job.get('created_at'),
        'completed_at': job.get('completed_at'),
        'error': job.get('error')
    }

    # Include script if available
    if job.get('recap_script'):
        response['recap_script'] = job['recap_script']

    return jsonify(response)


@app.route('/api/download/<job_id>', methods=['GET'])
def download_video(job_id):
    """Download completed recap video"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': 'Video not ready for download'}), 400

    output_path = job.get('output_path')

    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'Output file not found'}), 404

    # Generate download filename
    movie_title = job.get('movie_title', 'movie').replace(' ', '_')
    download_name = f"{movie_title}_2min_recap.mp4"

    return send_file(
        output_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=download_name
    )


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    job_list = []
    for job_id, job in jobs.items():
        job_list.append({
            'id': job['id'],
            'status': job['status'],
            'progress': job.get('progress', 0),
            'movie_title': job.get('movie_title'),
            'created_at': job.get('created_at'),
            'filename': job.get('filename')
        })

    return jsonify(job_list)


@app.route('/api/script/<job_id>', methods=['GET'])
def get_script(job_id):
    """Get the generated recap script"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    if not job.get('recap_script'):
        return jsonify({'error': 'Script not yet generated'}), 400

    return jsonify(job['recap_script'])


@app.route('/api/transcript/<job_id>', methods=['GET'])
def get_transcript(job_id):
    """Get the full transcript"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    if not job.get('transcript'):
        return jsonify({'error': 'Transcript not yet generated'}), 400

    return jsonify({'transcript': job['transcript']})


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    max_size = app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    return jsonify({'error': f'File too large. Maximum size is {max_size}MB'}), 413


@app.errorhandler(500)
def server_error(e):
    """Handle internal server error"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

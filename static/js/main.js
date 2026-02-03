/**
 * Movie Recap Generator - Frontend JavaScript
 */

// DOM Elements
const uploadSection = document.getElementById('upload-section');
const processingSection = document.getElementById('processing-section');
const resultSection = document.getElementById('result-section');
const errorSection = document.getElementById('error-section');

const uploadForm = document.getElementById('upload-form');
const uploadArea = document.getElementById('upload-area');
const videoInput = document.getElementById('video-input');
const uploadPreview = document.getElementById('upload-preview');
const fileNameSpan = document.getElementById('file-name');
const fileSizeSpan = document.getElementById('file-size');
const removeFileBtn = document.getElementById('remove-file');
const uploadBtn = document.getElementById('upload-btn');

const progressBar = document.getElementById('progress-bar');
const statusText = document.getElementById('status-text');
const statusDetail = document.getElementById('status-detail');

const resultVideo = document.getElementById('result-video');
const resultTitle = document.getElementById('result-title');
const downloadBtn = document.getElementById('download-btn');
const viewScriptBtn = document.getElementById('view-script-btn');
const newRecapBtn = document.getElementById('new-recap-btn');
const scriptAccordion = document.getElementById('script-accordion');
const scriptText = document.getElementById('script-text');

const errorMessage = document.getElementById('error-message');
const retryBtn = document.getElementById('retry-btn');

// State
let selectedFile = null;
let currentJobId = null;
let statusPollInterval = null;

// Status messages for each step
const STATUS_MESSAGES = {
    'uploaded': 'Video uploaded successfully',
    'processing': 'Starting processing...',
    'extracting_audio': 'Extracting audio from video...',
    'transcribing': 'Transcribing dialogue with AI...',
    'generating_script': 'Generating recap narration script...',
    'generating_voiceover': 'Creating voiceover narration...',
    'extracting_scenes': 'Extracting key scenes from movie...',
    'compiling': 'Compiling final recap video...',
    'completed': 'Recap generation complete!',
    'failed': 'Processing failed'
};

// Step mappings for progress display
const STEP_MAPPINGS = {
    'uploaded': 'step-upload',
    'processing': 'step-upload',
    'extracting_audio': 'step-audio',
    'transcribing': 'step-transcribe',
    'generating_script': 'step-script',
    'generating_voiceover': 'step-voiceover',
    'extracting_scenes': 'step-scenes',
    'compiling': 'step-compile',
    'completed': 'step-compile'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    // File input
    uploadArea.addEventListener('click', () => videoInput.click());
    videoInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Remove file
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearFile();
    });

    // Form submission
    uploadForm.addEventListener('submit', handleSubmit);

    // Result actions
    downloadBtn.addEventListener('click', handleDownload);
    viewScriptBtn.addEventListener('click', handleViewScript);
    newRecapBtn.addEventListener('click', resetToUpload);
    retryBtn.addEventListener('click', resetToUpload);
}

// File handling
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        validateAndSetFile(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const file = e.dataTransfer.files[0];
    if (file) {
        validateAndSetFile(file);
    }
}

function validateAndSetFile(file) {
    // Check file type
    const validTypes = ['video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime', 'video/webm', 'video/x-ms-wmv'];
    const validExtensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv'];

    const extension = '.' + file.name.split('.').pop().toLowerCase();

    if (!validTypes.includes(file.type) && !validExtensions.includes(extension)) {
        alert('Invalid file type. Please upload a video file (MP4, MKV, AVI, MOV, WebM, WMV).');
        return;
    }

    // Check file size (2GB max)
    const maxSize = 2 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File too large. Maximum size is 2GB.');
        return;
    }

    selectedFile = file;
    showFilePreview(file);
    uploadBtn.disabled = false;
}

function showFilePreview(file) {
    uploadArea.querySelector('.upload-content').classList.add('d-none');
    uploadPreview.classList.remove('d-none');

    fileNameSpan.textContent = file.name;
    fileSizeSpan.textContent = formatFileSize(file.size);
}

function clearFile() {
    selectedFile = null;
    videoInput.value = '';
    uploadArea.querySelector('.upload-content').classList.remove('d-none');
    uploadPreview.classList.add('d-none');
    uploadBtn.disabled = true;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Form submission
async function handleSubmit(e) {
    e.preventDefault();

    if (!selectedFile) {
        alert('Please select a video file.');
        return;
    }

    const movieTitle = document.getElementById('movie-title').value.trim();
    const movieGenre = document.getElementById('movie-genre').value;

    if (!movieTitle) {
        alert('Please enter the movie title.');
        return;
    }

    // Show processing section
    showSection('processing');
    updateStep('step-upload', 'active');
    updateProgress(5, 'Uploading video...');

    try {
        // Upload file
        const formData = new FormData();
        formData.append('video', selectedFile);
        formData.append('title', movieTitle);
        formData.append('genre', movieGenre);

        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.error || 'Upload failed');
        }

        const uploadData = await uploadResponse.json();
        currentJobId = uploadData.job_id;

        updateStep('step-upload', 'completed');
        updateProgress(10, 'Upload complete. Starting processing...');

        // Start processing
        const processResponse = await fetch(`/api/process/${currentJobId}`, {
            method: 'POST'
        });

        if (!processResponse.ok) {
            const error = await processResponse.json();
            throw new Error(error.error || 'Failed to start processing');
        }

        // Start polling for status
        startStatusPolling();

    } catch (error) {
        showError(error.message);
    }
}

// Status polling
function startStatusPolling() {
    statusPollInterval = setInterval(checkStatus, 2000);
}

function stopStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
}

async function checkStatus() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/status/${currentJobId}`);

        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }

        const data = await response.json();

        // Update progress
        updateProgress(data.progress, STATUS_MESSAGES[data.status] || data.status);

        // Update steps
        updateStepsForStatus(data.status);

        // Handle completion
        if (data.status === 'completed') {
            stopStatusPolling();
            showResult(data);
        } else if (data.status === 'failed') {
            stopStatusPolling();
            showError(data.error || 'Processing failed');
        }

    } catch (error) {
        console.error('Status check failed:', error);
    }
}

function updateStepsForStatus(status) {
    const steps = ['step-upload', 'step-audio', 'step-transcribe', 'step-script', 'step-voiceover', 'step-scenes', 'step-compile'];
    const currentStepId = STEP_MAPPINGS[status];
    const currentIndex = steps.indexOf(currentStepId);

    steps.forEach((stepId, index) => {
        if (index < currentIndex) {
            updateStep(stepId, 'completed');
        } else if (index === currentIndex) {
            updateStep(stepId, 'active');
        } else {
            updateStep(stepId, 'pending');
        }
    });

    if (status === 'completed') {
        steps.forEach(stepId => updateStep(stepId, 'completed'));
    }
}

function updateStep(stepId, state) {
    const step = document.getElementById(stepId);
    if (!step) return;

    step.classList.remove('active', 'completed');
    const icon = step.querySelector('.step-icon');

    if (state === 'active') {
        step.classList.add('active');
        icon.className = 'bi bi-arrow-right-circle-fill step-icon';
    } else if (state === 'completed') {
        step.classList.add('completed');
        icon.className = 'bi bi-check-circle-fill step-icon';
    } else {
        icon.className = 'bi bi-circle step-icon';
    }
}

function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressBar.textContent = `${percent}%`;
    statusText.textContent = message;
}

// Result handling
function showResult(data) {
    showSection('result');

    resultTitle.textContent = data.movie_title + ' - 2 Minute Recap';

    // Set video source (will trigger download on play for blob URLs)
    resultVideo.src = `/api/download/${currentJobId}`;

    // Store script if available
    if (data.recap_script) {
        scriptText.textContent = data.recap_script.narration || 'Script not available';
        scriptAccordion.classList.remove('d-none');
    }
}

function handleDownload() {
    if (!currentJobId) return;

    const link = document.createElement('a');
    link.href = `/api/download/${currentJobId}`;
    link.download = `${document.getElementById('movie-title').value}_2min_recap.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function handleViewScript() {
    scriptAccordion.classList.toggle('d-none');

    if (!scriptAccordion.classList.contains('d-none')) {
        // Fetch script if not loaded
        if (!scriptText.textContent || scriptText.textContent === 'Script not available') {
            fetchScript();
        }
    }
}

async function fetchScript() {
    if (!currentJobId) return;

    try {
        const response = await fetch(`/api/script/${currentJobId}`);
        if (response.ok) {
            const data = await response.json();
            scriptText.textContent = data.narration || JSON.stringify(data, null, 2);
        }
    } catch (error) {
        console.error('Failed to fetch script:', error);
    }
}

// Section management
function showSection(sectionName) {
    uploadSection.classList.add('d-none');
    processingSection.classList.add('d-none');
    resultSection.classList.add('d-none');
    errorSection.classList.add('d-none');

    switch (sectionName) {
        case 'upload':
            uploadSection.classList.remove('d-none');
            break;
        case 'processing':
            processingSection.classList.remove('d-none');
            break;
        case 'result':
            resultSection.classList.remove('d-none');
            break;
        case 'error':
            errorSection.classList.remove('d-none');
            break;
    }
}

function showError(message) {
    stopStatusPolling();
    errorMessage.textContent = message;
    showSection('error');
}

function resetToUpload() {
    stopStatusPolling();
    currentJobId = null;
    clearFile();

    // Reset steps
    const steps = ['step-upload', 'step-audio', 'step-transcribe', 'step-script', 'step-voiceover', 'step-scenes', 'step-compile'];
    steps.forEach(stepId => updateStep(stepId, 'pending'));

    // Reset progress
    updateProgress(0, 'Initializing...');

    // Show upload section
    showSection('upload');

    // Clear form
    document.getElementById('movie-title').value = '';
    document.getElementById('movie-genre').value = 'Drama';
}

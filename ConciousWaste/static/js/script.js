/* ═══════════════════════════════════════
   SURVEY APP — script.js
═══════════════════════════════════════ */

// ── State ──────────────────────────────
const answers     = {};
const TOTAL_PAGES = 15; // pages 1-15 (0 = consent)

let currentPage   = 0;
let mediaRecorder = null;
let audioChunks   = [];
let audioBlob     = null;

// ── Page navigation ────────────────────
function goToPage(next) {
    const current = document.querySelector('.page.active');
    if (current) {
        current.classList.add('exit');
        current.classList.remove('active');
        setTimeout(() => current.classList.remove('exit'), 350);
    }

    const target = document.getElementById('page-' + next);
    if (target) {
        setTimeout(function () {
            target.classList.add('active');
            currentPage = next;
            updateProgress();
        }, 60);
    }
}

function updateProgress() {
    const fill = document.getElementById('progressFill');
    const pct  = currentPage === 0 ? 0 : (currentPage / TOTAL_PAGES) * 100;
    fill.style.width = pct + '%';
}

function toggleConsent() {
    const checked = document.getElementById('consentBox').checked;
    document.getElementById('consentBtn').disabled = !checked;
}

// ── Question 1: text input ─────────────
function checkTextInput() {
    const val = document.getElementById('q1').value.trim();
    document.getElementById('nextBtn1').disabled = (val.length === 0);
    answers.q1 = val;
}

// ── Choice buttons (q2 and q3) ─────────
function selectChoice(btn, questionKey, nextPage) {
    // Deselect all siblings inside the same container
    const container = btn.parentElement;
    container.querySelectorAll('button').forEach(b => b.classList.remove('selected'));

    btn.classList.add('selected');
    answers[questionKey] = btn.getAttribute('data-value') || btn.textContent.trim();

    // Short pause so user sees selection, then advance
    setTimeout(() => goToPage(nextPage), 350);
}

// ── Audio recording ────────────────────
async function startRecording() {
    try {
        const stream  = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks   = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            audioBlob     = new Blob(audioChunks, { type: 'audio/webm' });
            const url     = URL.createObjectURL(audioBlob);

            document.getElementById('audioPlayback').src             = url;
            document.getElementById('audioPlaybackSection').style.display = 'flex';
            document.getElementById('nextBtn13').disabled             = false;

            // Hide the "you must record first" hint
            const hint = document.getElementById('recordRequired');
            if (hint) hint.style.display = 'none';

            setRecorderUI(false);
        };

        mediaRecorder.start();
        setRecorderUI(true);

    } catch (err) {
        console.error('Microphone access denied:', err);
        document.getElementById('recorderStatus').textContent =
            '⚠️ Geen toegang tot microfoon. Controleer je browserinstellingen.';
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
}

function setRecorderUI(isRecording) {
    const ring     = document.getElementById('recorderRing');
    const status   = document.getElementById('recorderStatus');
    const startBtn = document.getElementById('startRecordBtn');
    const stopBtn  = document.getElementById('stopRecordBtn');

    if (isRecording) {
        ring.classList.add('recording');
        status.textContent = '🔴 Opname bezig…';
        startBtn.disabled  = true;
        stopBtn.disabled   = false;
    } else {
        ring.classList.remove('recording');
        status.textContent = '✅ Opname opgeslagen – beluister hieronder';
        startBtn.disabled  = false;
        stopBtn.disabled   = true;
    }
}

// ── Submit + kick off TTS ──────────────
async function submitSurvey() {
    const formData = new FormData();

    for (const [key, val] of Object.entries(answers)) {
        formData.append(key, val);
    }

    if (audioBlob) {
        formData.append('audio', audioBlob, 'recording.webm');
    }

    // Go to TTS loading page immediately
    goToPage(14);

    try {
        const res  = await fetch('/submit', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('submit failed');
        const data = await res.json();

        // Poll until the TTS result (audio, or in mock mode the generated text) is ready
        const result = await pollForTTSAudio(data.job_id);

        document.getElementById('ttsLoadingMsg').style.display = 'none';
        document.getElementById('ttsReadyMsg').style.display    = 'block';
        document.getElementById('ttsNextBtn').style.display     = 'flex';

        if (result.audio_url) {
            const player = document.getElementById('ttsAudioPlayer');
            player.src = result.audio_url;
            player.style.display = 'block';
        } else if (result.text) {
            // MOCK_TTS mode: no audio was generated — show the text instead
            const mockText = document.getElementById('ttsMockText');
            mockText.textContent = result.text;
            mockText.style.display = 'block';
        }

    } catch (err) {
        console.error('TTS error:', err);
        document.getElementById('ttsLoadingMsg').textContent =
            '⚠️ Er ging iets mis bij het genereren van audio. Ga toch door.';
        document.getElementById('ttsNextBtn').style.display = 'flex';
    }
}

// ── Init ───────────────────────────────
updateProgress();

// ── TTS: poll Flask for the generated audio ────────────────────────────────
async function pollForTTSAudio(jobId) {
    const maxAttempts = 30; // 30 × 2s = 60s timeout
    let attempts = 0;

    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            attempts++;
            try {
                const res  = await fetch('/tts_status/' + jobId);
                const data = await res.json();

                if (data.status === 'done') {
                    clearInterval(interval);
                    resolve(data);
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    reject(new Error(data.message || 'TTS mislukt'));
                } else if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    reject(new Error('TTS duurde te lang'));
                }
            } catch (err) {
                clearInterval(interval);
                reject(err);
            }
        }, 2000);
    });
}

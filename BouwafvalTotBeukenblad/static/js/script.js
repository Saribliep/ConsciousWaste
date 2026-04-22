/* ═══════════════════════════════════════
   SURVEY APP — script.js
═══════════════════════════════════════ */

// ── State ──────────────────────────────
const answers     = {};
const TOTAL_PAGES = 5; // pages 1-5 (0 = consent)

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
            document.getElementById('nextBtn4').disabled             = false;

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

// ── Submit ─────────────────────────────
async function submitSurvey() {
    const formData = new FormData();

    for (const [key, val] of Object.entries(answers)) {
        formData.append(key, val);
    }

    if (audioBlob) {
        formData.append('audio', audioBlob, 'recording.webm');
    }

    try {
        const res = await fetch('/submit', { method: 'POST', body: formData });
        if (res.ok) {
            goToPage(5);
        } else {
            alert('Er is iets misgegaan bij het opslaan. Probeer opnieuw.');
        }
    } catch (err) {
        console.error('Submit error:', err);
        alert('Geen verbinding. Controleer je internet en probeer opnieuw.');
    }
}

// ── Init ───────────────────────────────
updateProgress();

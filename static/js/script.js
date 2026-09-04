/* ═══════════════════════════════════════
   SURVEY APP — script.js
═══════════════════════════════════════ */

// ── State ──────────────────────────────
const answers     = {};
const TOTAL_PAGES = 19; // pages 1-18 (0 = consent)

let currentPage   = 0;
let mediaRecorder = null;
let audioChunks   = [];
let audioBlob     = null;
let responseId    = null; // set once /submit responds, used later for /feedback

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

// ── Mic permission pre-check ───────────
// Browsers won't let a webpage jump into the phone's system Settings app —
// so instead we ask for mic access right after consent (before the 14-page
// survey) and show clear, platform-specific instructions if it's blocked.
// This way people find out immediately instead of at the very last page.
function micReenableInstructions() {
    const ua = navigator.userAgent;
    if (/iPhone|iPad|iPod/.test(ua)) {
        return "Ga naar Instellingen → Safari/Chrome → Microfoon en zet deze website op 'Toestaan'. Kom daarna terug en tik op 'Probeer opnieuw'.";
    } else if (/Android/.test(ua)) {
        return "Tik op het slotje of (i) icoontje naast de website-adres, kies 'Machtigingen' → 'Microfoon' → 'Toestaan'. Tik daarna op 'Probeer opnieuw'.";
    }
    return "Klik op het slotje of (i) icoontje naast de website-adres in je browser, zet 'Microfoon' op 'Toestaan', en tik daarna op 'Probeer opnieuw'.";
}

async function requestMicAndContinue() {
    const errorBox = document.getElementById('micCheckError');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // We only need to confirm access here — stop the stream immediately,
        // the real recording happens later on page 13.
        stream.getTracks().forEach(t => t.stop());
        errorBox.style.display = 'none';
        goToPage(1);
    } catch (err) {
        console.error('Mic pre-check failed:', err);
        document.getElementById('micCheckInstructions').textContent = micReenableInstructions();
        errorBox.style.display = 'block';
    }
}

// ── Question 1: text input ─────────────
function checkTextInput() {
    const val = document.getElementById('q1').value.trim();
    document.getElementById('nextBtn1').disabled = (val.length === 0);
    answers.q1 = val;
}

// ── Intro audio / maquette (page 2) ────
function playIntroFragment() {
    const audio   = document.getElementById('introAudio');
    const playBtn = document.getElementById('introPlayBtn');
    const nextBtn = document.getElementById('introNextBtn');

    playBtn.disabled    = true;
    playBtn.textContent = '▶ Wordt afgespeeld…';

    audio.play().catch(err => {
        console.error('Intro audio playback failed:', err);
        nextBtn.style.display = 'flex'; // don't strand the user if playback fails
    });

    audio.onended = () => { nextBtn.style.display = 'flex'; };
    audio.onerror = () => { nextBtn.style.display = 'flex'; };
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

// ── Mirror moment (page 16) ────────────
function playMirrorMoment() {
    const audio   = document.getElementById('mirrorAudio');
    const playBtn = document.getElementById('mirrorPlayBtn');
    const nextBtn = document.getElementById('mirrorNextBtn');

    playBtn.disabled    = true;
    playBtn.textContent = '▶ Wordt afgespeeld…';

    audio.play().catch(err => {
        console.error('Mirror audio playback failed:', err);
        nextBtn.style.display = 'flex'; // don't strand the user if playback fails
    });

    audio.onended = () => { nextBtn.style.display = 'flex'; };
    audio.onerror = () => { nextBtn.style.display = 'flex'; };
}

// ── Het Geweten playback (page 17) ─────
function playTtsAudio() {
    const audio   = document.getElementById('ttsAudioPlayer');
    const playBtn = document.getElementById('ttsPlayBtn');
    const nextBtn = document.getElementById('ttsNextBtn');

    playBtn.disabled    = true;
    playBtn.textContent = '▶ Wordt afgespeeld…';

    audio.play().catch(err => {
        console.error('Het Geweten audio playback failed:', err);
        nextBtn.style.display = 'flex'; // don't strand the user if playback fails
    });

    audio.onended = () => { nextBtn.style.display = 'flex'; };
    audio.onerror = () => { nextBtn.style.display = 'flex'; };
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

    // Go to the mirror-moment page immediately — TTS generates in the
    // background (see below) while that fragment plays
    goToPage(17);

    try {
        const res  = await fetch('/submit', { method: 'POST', body: formData });
        if (!res.ok) throw new Error('submit failed');
        const data = await res.json();
        responseId = data.response_id;

        // Poll until the TTS result (audio, or in mock mode the generated text) is ready
        const result = await pollForTTSAudio(data.job_id);

        document.getElementById('ttsLoadingMsg').style.display = 'none';

        if (result.audio_url) {
            // Real audio: show the "sit down and press play" moment —
            // the Doorgaan button only appears once they've started playback
            document.getElementById('ttsReadyMsg').style.display = 'block';
            document.getElementById('ttsAudioPlayer').src = result.audio_url;
        } else if (result.text) {
            // MOCK_TTS mode: no audio was generated — show the name/answers
            // and the generated text side by side instead, and skip straight
            // to a manual Doorgaan since there's nothing to play
            const answersLines = [`naam: ${result.naam || ''}`];
            for (const [key, val] of Object.entries(result.answers || {})) {
                if (key === 'q1') continue; // already shown as naam
                answersLines.push(`${key}: ${val}`);
            }
            document.getElementById('ttsMockAnswers').textContent = answersLines.join('\n');
            document.getElementById('ttsMockText').textContent    = result.text;
            document.getElementById('ttsMockWrap').style.display  = 'flex';
            document.getElementById('ttsNextBtn').style.display   = 'flex';
        }

    } catch (err) {
        console.error('TTS error:', err);
        document.getElementById('ttsLoadingMsg').textContent =
            '⚠️ Er ging iets mis bij het genereren van audio. Ga toch door.';
        document.getElementById('ttsNextBtn').style.display = 'flex';
    }
}

// ── Post-submission feedback (page 18) ─
async function submitFeedback() {
    const btn = document.getElementById('feedbackSubmitBtn');
    btn.disabled = true;

    try {
        await fetch('/feedback', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                response_id: responseId,
                emotion:     document.getElementById('feedbackEmotion').value,
                email:       document.getElementById('feedbackEmail').value,
            }),
        });
    } catch (err) {
        console.error('Feedback submit failed:', err);
    }

    document.getElementById('feedbackThanks').style.display = 'block';
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

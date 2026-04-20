document.getElementById('surveyForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    fetch('/submit', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
      .then(data => {
          console.log('Success:', data);
      })
      .catch((error) => {
          console.error('Error:', error);
      });
});

let mediaRecorder;
let audioChunks = [];

document.getElementById('startRecordBtn').addEventListener('click', async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();
    document.getElementById('stopRecordBtn').disabled = false;
    document.getElementById('startRecordBtn').disabled = true;

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audioPlayback = document.getElementById('audioPlayback');
        audioPlayback.src = audioUrl;
        audioPlayback.play();
        const audioFile = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
        document.getElementById('surveyForm').appendChild(document.createElement('input')).name = 'audio';
        document.getElementById('surveyForm').appendChild(document.createElement('input')).value = audioFile;
    };
});

document.getElementById('stopRecordBtn').addEventListener('click', () => {
    mediaRecorder.stop();
    document.getElementById('stopRecordBtn').disabled = true;
    document.getElementById('startRecordBtn').disabled = false;
});

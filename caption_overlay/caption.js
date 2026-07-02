const WS_URL = "ws://127.0.0.1:8765/";
const captionText = document.getElementById("caption-text");
let hideTimeout = null;

function connect() {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log("Connected to MyCompanion Caption Server");
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "caption") {
            displayCaption(data.text, data.speaker);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s...");
        setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        ws.close();
    };
}

function displayCaption(text, speaker) {
    if (hideTimeout) {
        clearTimeout(hideTimeout);
    }

    // Set styling classes
    captionText.className = `visible ${speaker}`;
    captionText.innerHTML = "";

    const words = text.split(" ");
    let index = 0;

    // Word-by-word animation reveal
    function revealWord() {
        if (index < words.length) {
            captionText.innerHTML += (index === 0 ? "" : " ") + words[index];
            index++;
            // Delay adjusted to human speech speed (approx 180-220ms per word)
            setTimeout(revealWord, 200);
        } else {
            // Auto hide caption 4 seconds after complete reveal
            hideTimeout = setTimeout(() => {
                captionText.classList.remove("visible");
            }, 4000);
        }
    }

    revealWord();
}

// Start connection
connect();

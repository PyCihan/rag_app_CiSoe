const chatContainer = document.getElementById('chatContainer');
const chatHistory = [];

async function uploadPDF() {
    const pdfFile = document.getElementById('pdf').files[0];
    const formData = new FormData();
    formData.append('file', pdfFile);

    const response = await fetch('/upload_pdf', {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();
    location.reload();
}

document.addEventListener('DOMContentLoaded', function() {
    fetchAvailableSources();
    fetchChatHistory();  // Fetch and display chat history on page load
});

async function streamChatResponse() {
    const query = document.getElementById('query').value;
    document.getElementById('query').value = '';

    addMessageToHistory(query, 'user');
    addMessageToHistory('', 'system');

    const response = await fetch('/stream_response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let answer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        answer += chunk;
        updateAnswerDisplay(answer);
    }
}

function addMessageToHistory(message, sender) {
    chatHistory.push({ message, sender });
    renderChatHistory();
}

function renderChatHistory() {
    chatContainer.innerHTML = '';
    chatHistory.forEach(entry => {
        const messageGroup = document.createElement('div');
        messageGroup.classList.add('message-group', entry.sender === 'user' ? 'user-group' : 'system-group');

        const messageLabel = document.createElement('div');
        messageLabel.classList.add('message-label');
        messageLabel.textContent = entry.sender === 'user' ? 'You' : 'System';

        const chatMessage = document.createElement('div');
        chatMessage.classList.add('chat-message', entry.sender === 'user' ? 'user-message' : 'system-message');
        chatMessage.textContent = entry.message;

        messageGroup.appendChild(messageLabel);
        messageGroup.appendChild(chatMessage);
        chatContainer.appendChild(messageGroup);
    });

    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateAnswerDisplay(answer) {
    const lastMessage = chatHistory[chatHistory.length - 1];
    if (lastMessage && lastMessage.sender === 'system') {
        lastMessage.message = answer;
        renderChatHistory();
    }
}

async function queryPDF() {
    const query = document.getElementById('query').value;
    document.getElementById('query').value = '';

    addMessageToHistory(query, 'user');
    addMessageToHistory('', 'system');

    const response = await fetch('/query_pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
    });

    const data = await response.json();
    updateAnswerDisplay(data.answer);

    const sourcesList = document.getElementById('sources-list');
    sourcesList.innerHTML = '';

    if (data.sources) {
        data.sources.forEach(source => {
            const fileName = source.source.split('/').pop();
            const li = document.createElement('li');
            const link = document.createElement('a');
            link.href = `pdfs/${fileName}`;
            link.target = '_blank';
            link.textContent = fileName;
            li.appendChild(link);
            sourcesList.appendChild(li);
        });
    }
}

async function fetchAvailableSources() {
    try {
        const response = await fetch('/list_sources');
        const data = await response.json();
        const pdfList = document.getElementById('pdf-list');
        pdfList.innerHTML = '';

        data.forEach(source => {
            const li = document.createElement('li');
            const link = document.createElement('a');
            link.href = `pdfs/${source}`;
            link.target = '_blank';
            link.textContent = source;
            li.appendChild(link);
            pdfList.appendChild(li);
        });
    } catch (error) {
        console.error('Error fetching sources:', error);
    }
}

const darkModeToggle = document.getElementById('darkModeToggle');
darkModeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    darkModeToggle.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
});

document.getElementById('query').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        document.getElementById('submitBtn').click();
    }
});
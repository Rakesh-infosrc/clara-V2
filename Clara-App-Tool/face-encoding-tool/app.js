const runButton = document.getElementById('runButton');
const statusIndicator = document.getElementById('statusIndicator');
const lastRun = document.getElementById('lastRun');
const duration = document.getElementById('duration');
const encodedCount = document.getElementById('encodedCount');
const logOutput = document.getElementById('logOutput');
const endpointInput = document.getElementById('endpoint');
const encodedList = document.getElementById('encodedList');
const clearListButton = document.getElementById('clearList');

const LOG_MAX_LINES = 400;

function appendLog(message) {
  const timestamp = new Date().toLocaleTimeString();
  const lines = logOutput.textContent.split('\n');
  lines.push(`[${timestamp}] ${message}`);
  if (lines.length > LOG_MAX_LINES) {
    lines.splice(0, lines.length - LOG_MAX_LINES);
  }
  logOutput.textContent = lines.join('\n');
  logOutput.scrollTop = logOutput.scrollHeight;
}

function setStatus(state, text) {
  statusIndicator.className = `status-indicator ${state}`;
  statusIndicator.textContent = text;
}

async function triggerEncoding() {
  const endpoint = endpointInput.value.trim();
  if (!endpoint) {
    appendLog('⚠️ Please enter the trigger endpoint URL before running.');
    return;
  }

  setStatus('running', 'Running');
  appendLog('🚀 Starting face encoding job...');
  appendLog('⏳ This process can take up to a minute while images are processed.');
  runButton.disabled = true;
  const start = Date.now();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ action: 'run_face_encoding' }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const elapsed = Date.now() - start;
    const seconds = (elapsed / 1000).toFixed(1);
    duration.textContent = `${seconds} s`;

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    const data = await response.json().catch(() => ({}));
    const count = data.encoded_count ?? data.count ?? data.total ?? 0;
    encodedCount.textContent = count;
    lastRun.textContent = new Date().toLocaleString();

    const encodedIds = Array.isArray(data.encoded_employee_ids) ? data.encoded_employee_ids : [];
    renderEncodedIds(encodedIds);

    appendLog(`✅ Face encoding complete. Encoded employees: ${count}`);
    if (data.details) {
      appendLog(`ℹ️ Details: ${data.details}`);
    }

    setStatus('success', 'Success');
  } catch (error) {
    if (error.name === 'AbortError') {
      appendLog('⌛ Request timed out after 120 seconds. Check backend logs to confirm whether the job is still running.');
    } else {
      appendLog(`❌ Failed to run job: ${error.message}`);
    }
    appendLog(`❌ Failed to run job: ${error.message}`);
    setStatus('error', 'Error');
  } finally {
    runButton.disabled = false;
  }
}

runButton.addEventListener('click', triggerEncoding);
clearListButton.addEventListener('click', () => {
  renderEncodedIds([]);
});

function renderEncodedIds(ids) {
  encodedList.innerHTML = '';
  if (!ids.length) {
    encodedList.classList.add('empty');
    encodedList.textContent = 'No runs yet.';
    return;
  }

  encodedList.classList.remove('empty');
  ids.forEach((id) => {
    const item = document.createElement('div');
    item.className = 'encoded-list__item';
    item.textContent = id;
    encodedList.appendChild(item);
  });
}

// Initialize status
setStatus('idle', 'Idle');
appendLog('Ready. Configure the endpoint and click the button to run the job.');
renderEncodedIds([]);

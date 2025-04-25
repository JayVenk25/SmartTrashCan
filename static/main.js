const toggleBtn = document.getElementById('toggleBtn');
const resultEl = document.getElementById('result');

toggleBtn.addEventListener('click', async () => {
  resultEl.textContent = 'Please wait...';
  const resp = await fetch('/toggle', { method: 'POST' });
  const data = await resp.json();

  // Update button label
  toggleBtn.textContent = data.state === 'open' ? 'Close' : 'Open';

  // Show analysis when opened
  if (data.state === 'open' && data.item) {
    resultEl.textContent = JSON.stringify(data.item.analysis, null, 2);
  } else {
    resultEl.textContent = '';
  }
});
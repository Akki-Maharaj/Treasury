document.addEventListener('DOMContentLoaded', () => {
  const aiInput = document.getElementById('ai-describe-input');
  const analyzeBtn = document.getElementById('ai-analyze-btn');
  const qSection = document.getElementById('ai-question-section');
  const qPrompt = document.getElementById('ai-question-prompt');
  const qInput = document.getElementById('ai-question-input');
  const answerBtn = document.getElementById('ai-answer-btn');
  const skipBtn = document.getElementById('ai-skip-btn');
  const statusBox = document.getElementById('ai-status-box');
  const statusText = document.getElementById('ai-status-text');
  const filledBadgeContainer = document.getElementById('ai-filled-badges');

  if (!aiInput || !analyzeBtn) return;

  // State
  let currentKey = null;
  let answers = {};
  let skippedInARow = 0;
  let skippedKeys = [];
  let currentCategory = null;
  let filledAttrs = {};

  function renderFilledBadges(filled) {
    if (!filledBadgeContainer) return;
    filledBadgeContainer.innerHTML = '';
    const keys = Object.keys(filled);
    if (keys.length === 0) return;

    keys.forEach(k => {
      const badge = document.createElement('span');
      badge.style.cssText = 'background: #e2e8f0; color: #1e293b; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.78rem; font-weight: 500;';
      badge.textContent = `${k}: ${filled[k]}`;
      filledBadgeContainer.appendChild(badge);
    });
  }

  function prefillListingForm(category, filled, description) {
    // 1. Category dropdown
    const categorySelect = document.getElementById('category');
    if (categorySelect && category) {
      const match = Array.from(categorySelect.options).find(opt => opt.value === category);
      if (match) {
        categorySelect.value = match.value;
      }
    }

    // 2. Title (if empty)
    const titleInput = document.getElementById('title');
    if (titleInput && !titleInput.value.trim()) {
      const parts = [filled.brand, filled.model, filled.year].filter(Boolean);
      if (parts.length > 0) {
        titleInput.value = parts.join(' ');
      }
    }

    // 3. Description (if provided)
    const descInput = document.getElementById('description');
    if (descInput && description) {
      descInput.value = description;
    }

    // 4. Extra details as "key: value" lines
    const extraDetails = document.getElementById('extra_details');
    if (extraDetails) {
      const lines = Object.entries(filled).map(([k, v]) => `${k}: ${v}`);
      if (lines.length > 0) {
        extraDetails.value = lines.join('\n');
      }
    }
  }

  async function sendAnalyzeRequest() {
    const text = aiInput.value.trim();
    if (!text) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';

    try {
      const resp = await fetch('/api/sell/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          answers: answers,
          skipped_in_a_row: skippedInARow,
          skipped_keys: skippedKeys
        })
      });

      if (!resp.ok) throw new Error('API request failed');
      const data = await resp.json();

      currentCategory = data.category;
      filledAttrs = data.filled || {};
      renderFilledBadges(filledAttrs);

      if (data.done) {
        qSection.style.display = 'none';
        statusBox.style.display = 'block';
        statusText.textContent = data.message || 'Details filled! You can review the form below.';
        prefillListingForm(data.category, data.filled, data.description);
      } else if (data.next_question) {
        currentKey = data.next_question.key;
        qPrompt.textContent = data.next_question.text;
        qInput.value = '';
        qSection.style.display = 'block';
        statusBox.style.display = 'none';
        qInput.focus();
      }
    } catch (err) {
      console.error('Sell AI error:', err);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = 'Analyze';
    }
  }

  analyzeBtn.addEventListener('click', () => {
    answers = {};
    skippedInARow = 0;
    skippedKeys = [];
    sendAnalyzeRequest();
  });

  answerBtn.addEventListener('click', () => {
    const val = qInput.value.trim();
    if (val && currentKey) {
      answers[currentKey] = val;
      skippedInARow = 0;
      sendAnalyzeRequest();
    }
  });

  qInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      answerBtn.click();
    }
  });

  skipBtn.addEventListener('click', () => {
    if (currentKey) {
      skippedKeys.push(currentKey);
      skippedInARow += 1;
      sendAnalyzeRequest();
    }
  });
});

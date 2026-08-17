(() => {
  const form = document.getElementById('examForm');
  const cards = [...document.querySelectorAll('.question-card')];
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const reviewBtn = document.getElementById('reviewBtn');
  const modal = document.getElementById('reviewModal');
  const closeReview = document.getElementById('closeReview');
  const confirmSubmit = document.getElementById('confirmSubmit');
  const answeredCount = document.getElementById('answeredCount');
  const progressPercent = document.getElementById('progressPercent');
  const progressRing = document.getElementById('progressRing');
  const dotsContainer = document.getElementById('questionDots');
  const focusIncidentCount = document.getElementById('focusIncidentCount');
  const focusModeBtn = document.getElementById('focusModeBtn');
  const storageKey = `assessment-studio:${form.dataset.attemptId || 'current'}`;
  const I = window.AS_I18N || {};
  const fmt = (key, vars = {}) => String(I[key] || key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? `{${k}}`);

  let current = 0;
  let dragItem = null;
  let submitting = false;
  let hiddenSince = null;
  let fullscreenWasEntered = false;

  const numberFromData = (name) => Number(form.dataset[name] || 0) || 0;
  const security = {
    focus_departures: numberFromData('initialFocus'),
    blur_events: numberFromData('initialBlur'),
    pagehide_events: numberFromData('initialPagehide'),
    contextmenu_attempts: numberFromData('initialContextmenu'),
    copy_attempts: numberFromData('initialCopy'),
    cut_attempts: numberFromData('initialCut'),
    paste_attempts: numberFromData('initialPaste'),
    shortcut_attempts: numberFromData('initialShortcuts'),
    fullscreen_exits: numberFromData('initialFullscreen'),
    away_seconds: numberFromData('initialAway'),
    longest_away_seconds: numberFromData('initialLongestAway'),
  };

  function syncSecurityFields() {
    const mapping = {
      focus_departures: 'security_focus_departures',
      blur_events: 'security_blur_events',
      pagehide_events: 'security_pagehide_events',
      contextmenu_attempts: 'security_contextmenu_attempts',
      copy_attempts: 'security_copy_attempts',
      cut_attempts: 'security_cut_attempts',
      paste_attempts: 'security_paste_attempts',
      shortcut_attempts: 'security_shortcut_attempts',
      fullscreen_exits: 'security_fullscreen_exits',
      away_seconds: 'security_away_seconds',
      longest_away_seconds: 'security_longest_away_seconds',
    };
    Object.entries(mapping).forEach(([key, id]) => {
      const field = document.getElementById(id);
      if (field) field.value = String(security[key]);
    });
    if (focusIncidentCount) focusIncidentCount.textContent = String(security.focus_departures + security.blur_events);
  }

  function currentQuestionId() {
    return cards[current]?.dataset.qid || '';
  }

  function sendIntegrityEvent(type, extra = {}, preferBeacon = false) {
    const payload = {
      type,
      question: currentQuestionId(),
      client_time: new Date().toISOString(),
      visibility: document.visibilityState,
      ...extra,
    };
    const body = JSON.stringify(payload);

    if (preferBeacon && navigator.sendBeacon) {
      try {
        const blob = new Blob([body], { type: 'application/json' });
        if (navigator.sendBeacon('/api/integrity-event', blob)) return;
      } catch (_) {}
    }

    try {
      fetch('/api/integrity-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        credentials: 'same-origin',
        keepalive: true,
      }).catch(() => {});
    } catch (_) {}
  }

  let noticeTimer = null;
  function securityNotice(message) {
    let notice = document.getElementById('securityNotice');
    if (!notice) {
      notice = document.createElement('div');
      notice.id = 'securityNotice';
      notice.className = 'security-notice';
      notice.setAttribute('role', 'status');
      document.body.appendChild(notice);
    }
    notice.textContent = message;
    notice.classList.add('show');
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => notice.classList.remove('show'), 3200);
  }

  // Best-effort anti-translation and anti-selection hints.
  document.documentElement.setAttribute('translate', 'no');
  document.documentElement.classList.add('notranslate');
  document.body.setAttribute('translate', 'no');

  function blockedShortcut(e) {
    const key = String(e.key || '').toLowerCase();
    const command = e.ctrlKey || e.metaKey;
    const devtoolsMac = e.metaKey && e.altKey && ['i', 'j', 'c', 'u'].includes(key);
    const devtoolsWin = e.ctrlKey && e.shiftKey && ['i', 'j', 'c', 'k'].includes(key);
    const commandBlocked = command && ['c', 'x', 'v', 'a', 's', 'p', 'u', 'l', 't', 'n', 'w'].includes(key);
    const translateLike = command && e.shiftKey && ['l', 's'].includes(key);
    return e.key === 'F12' || devtoolsMac || devtoolsWin || commandBlocked || translateLike;
  }

  document.addEventListener('contextmenu', (e) => {
    if (submitting) return;
    e.preventDefault();
    security.contextmenu_attempts += 1;
    syncSecurityFields();
    sendIntegrityEvent('contextmenu');
    securityNotice(fmt('rightClick'));
  }, { capture: true });

  document.addEventListener('copy', (e) => {
    if (submitting) return;
    e.preventDefault();
    security.copy_attempts += 1;
    syncSecurityFields();
    sendIntegrityEvent('copy');
    securityNotice(fmt('copy'));
  }, { capture: true });

  document.addEventListener('cut', (e) => {
    if (submitting) return;
    e.preventDefault();
    security.cut_attempts += 1;
    syncSecurityFields();
    sendIntegrityEvent('cut');
    securityNotice(fmt('cut'));
  }, { capture: true });

  document.addEventListener('paste', (e) => {
    if (submitting) return;
    e.preventDefault();
    security.paste_attempts += 1;
    syncSecurityFields();
    sendIntegrityEvent('paste');
    securityNotice(fmt('paste'));
  }, { capture: true });

  document.addEventListener('selectstart', (e) => {
    if (!submitting && !e.target.closest('input, textarea, select')) e.preventDefault();
  }, { capture: true });

  document.addEventListener('keydown', (e) => {
    if (submitting || !blockedShortcut(e)) return;
    e.preventDefault();
    e.stopPropagation();
    security.shortcut_attempts += 1;
    syncSecurityFields();
    const shortcut = [e.ctrlKey ? 'Ctrl' : '', e.metaKey ? 'Cmd' : '', e.altKey ? 'Alt' : '', e.shiftKey ? 'Shift' : '', e.key]
      .filter(Boolean).join('+');
    sendIntegrityEvent('shortcut', { shortcut });
    securityNotice(fmt('shortcut'));
  }, { capture: true });

  document.addEventListener('visibilitychange', () => {
    if (submitting) return;
    if (document.visibilityState === 'hidden' && hiddenSince === null) {
      hiddenSince = Date.now();
      security.focus_departures += 1;
      syncSecurityFields();
      sendIntegrityEvent('visibility_hidden', {}, true);
      return;
    }
    if (document.visibilityState === 'visible' && hiddenSince !== null) {
      const durationMs = Math.max(0, Date.now() - hiddenSince);
      const durationSeconds = durationMs / 1000;
      security.away_seconds += durationSeconds;
      security.longest_away_seconds = Math.max(security.longest_away_seconds, durationSeconds);
      hiddenSince = null;
      syncSecurityFields();
      sendIntegrityEvent('focus_return', { duration_ms: durationMs });
      securityNotice(fmt('focusRecorded', { count: security.focus_departures + security.blur_events }));
    }
  });

  window.addEventListener('blur', () => {
    if (submitting) return;
    setTimeout(() => {
      if (submitting || document.visibilityState !== 'visible') return;
      const tag = document.activeElement?.tagName;
      if (tag === 'SELECT') return;
      security.blur_events += 1;
      syncSecurityFields();
      sendIntegrityEvent('window_blur');
    }, 250);
  });

  window.addEventListener('pagehide', () => {
    if (submitting) return;
    security.pagehide_events += 1;
    syncSecurityFields();
    sendIntegrityEvent('pagehide', {}, true);
  });

  if (focusModeBtn) {
    const requestFullscreen = document.documentElement.requestFullscreen?.bind(document.documentElement)
      || document.documentElement.webkitRequestFullscreen?.bind(document.documentElement);
    if (!requestFullscreen) {
      focusModeBtn.disabled = true;
      focusModeBtn.textContent = fmt('focusUnavailable');
    } else {
      focusModeBtn.addEventListener('click', async () => {
        try {
          await requestFullscreen();
          fullscreenWasEntered = true;
          focusModeBtn.textContent = fmt('focusActive');
          focusModeBtn.classList.add('active');
        } catch (_) {
          focusModeBtn.textContent = fmt('focusUnavailable');
        }
      });
    }
  }

  function handleFullscreenChange() {
    const active = document.fullscreenElement || document.webkitFullscreenElement;
    if (active) {
      fullscreenWasEntered = true;
      if (focusModeBtn) {
        focusModeBtn.textContent = fmt('focusActive');
        focusModeBtn.classList.add('active');
      }
      return;
    }
    if (fullscreenWasEntered && !submitting) {
      security.fullscreen_exits += 1;
      syncSecurityFields();
      sendIntegrityEvent('fullscreen_exit');
      securityNotice(fmt('focusExited'));
      if (focusModeBtn) {
        focusModeBtn.textContent = fmt('focusReenter');
        focusModeBtn.classList.remove('active');
      }
    }
  }
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

  function orderValue(list) {
    return [...list.querySelectorAll('.sort-item')].map(el => el.dataset.value);
  }

  function syncOrder(list) {
    const id = list.dataset.orderList;
    const hidden = document.getElementById(`order_${id}`);
    hidden.value = JSON.stringify(orderValue(list));
  }

  function markOrderTouched(list) {
    const card = list.closest('.question-card');
    if (card) card.dataset.touched = '1';
    const touched = document.getElementById(`order_touched_${list.dataset.orderList}`);
    if (touched) touched.value = '1';
  }

  document.querySelectorAll('.sortable-list').forEach(list => {
    syncOrder(list);
    list.addEventListener('dragstart', e => {
      dragItem = e.target.closest('.sort-item');
      if (dragItem) dragItem.classList.add('dragging');
    });
    list.addEventListener('dragend', () => {
      if (dragItem) dragItem.classList.remove('dragging');
      dragItem = null;
      markOrderTouched(list); syncOrder(list); saveDraft(); updateProgress();
    });
    list.addEventListener('dragover', e => {
      e.preventDefault();
      if (!dragItem) return;
      const siblings = [...list.querySelectorAll('.sort-item:not(.dragging)')];
      const next = siblings.find(sib => e.clientY <= sib.getBoundingClientRect().top + sib.offsetHeight / 2);
      list.insertBefore(dragItem, next || null);
    });
    list.addEventListener('click', e => {
      const item = e.target.closest('.sort-item');
      if (!item) return;
      if (e.target.closest('.move-up') && item.previousElementSibling) {
        list.insertBefore(item, item.previousElementSibling);
      }
      if (e.target.closest('.move-down') && item.nextElementSibling) {
        list.insertBefore(item.nextElementSibling, item);
      }
      markOrderTouched(list); syncOrder(list); saveDraft(); updateProgress();
    });
  });

  // Listening: prerecorded files or browser speech synthesis. TTS scripts are fetched only when Play is pressed.
  document.querySelectorAll('.audio-btn').forEach(btn => {
    let plays = 0;
    let speaking = false;
    const max = Number(btn.dataset.maxplays || 2);
    const source = btn.dataset.source || 'audio';
    const audio = source === 'audio' ? document.getElementById(btn.dataset.audio) : null;
    const updateRemaining = () => {
      const remaining = max - plays;
      btn.querySelector('small').textContent = remaining === 1 ? fmt('playAvailable') : fmt('playsAvailable', { count: remaining });
      if (!remaining) btn.classList.add('spent');
    };
    const finish = () => { speaking = false; btn.classList.remove('playing'); };
    btn.addEventListener('click', async () => {
      if (plays >= max || speaking) return;
      if (source === 'audio') {
        if (!audio) return;
        plays += 1;
        audio.currentTime = 0;
        try { await audio.play(); } catch (_) { plays -= 1; return; }
        btn.classList.add('playing');
        updateRemaining();
        return;
      }
      if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
        securityNotice(fmt('ttsUnsupported'));
        return;
      }
      speaking = true;
      btn.classList.add('playing');
      try {
        const response = await fetch(btn.dataset.scriptUrl, { credentials: 'same-origin', cache: 'no-store' });
        if (!response.ok) throw new Error('script');
        const payload = await response.json();
        if (!payload.ok || !payload.text) throw new Error('script');
        const utterance = new SpeechSynthesisUtterance(payload.text);
        const lang = payload.lang || btn.dataset.lang || 'auto';
        if (lang && lang !== 'auto') utterance.lang = lang;
        utterance.rate = 0.95;
        utterance.onend = finish;
        utterance.onerror = finish;
        window.speechSynthesis.cancel();
        plays += 1;
        updateRemaining();
        window.speechSynthesis.speak(utterance);
      } catch (_) {
        finish();
        securityNotice(fmt('ttsLoadError'));
      }
    });
    audio?.addEventListener('ended', finish);
    audio?.addEventListener('error', finish);
  });

  function answerValidity(card) {
    const type = card.dataset.type;
    const qid = card.dataset.qid;
    if (type === 'multiple_choice' || type === 'listening' || type === 'true_false') {
      return { valid: Boolean(card.querySelector(`input[name="q_${qid}"]:checked`)), message: fmt('invalidCurrent') };
    }
    if (type === 'short_answer') {
      const field = card.querySelector(`[name="q_${qid}"]`);
      return { valid: Boolean(field && String(field.value || '').trim()), message: fmt('invalidCurrent') };
    }
    if (type === 'numeric') {
      const field = card.querySelector(`[name="q_${qid}"]`);
      const value = Number(String(field?.value || '').trim().replace(',', '.'));
      return { valid: Boolean(String(field?.value || '').trim()) && Number.isFinite(value), message: fmt('invalidNumeric') };
    }
    if (type === 'order') {
      const list = card.querySelector('.sortable-list');
      const values = list ? orderValue(list) : [];
      return { valid: card.dataset.touched === '1' && values.length > 0 && new Set(values).size === values.length, message: fmt('invalidOrder') };
    }
    if (type === 'matching') {
      const selects = [...card.querySelectorAll('select')];
      const values = selects.map(select => select.value);
      return { valid: selects.length > 0 && values.every(Boolean) && new Set(values).size === values.length, message: fmt('invalidMatching') };
    }
    return { valid: false, message: fmt('invalidCurrent') };
  }

  const isAnswered = card => answerValidity(card).valid;

  function firstAnswerControl(card) {
    return card.querySelector('input:not([type="hidden"]), select, button.move-up, button.move-down, .sortable-list');
  }

  function showQuestionError(card, message) {
    const error = card.querySelector('.question-error');
    card.classList.add('question-invalid');
    if (error) { error.textContent = message; error.hidden = false; }
    securityNotice(message);
    firstAnswerControl(card)?.focus();
  }

  function clearQuestionError(card) {
    const error = card.querySelector('.question-error');
    card.classList.remove('question-invalid');
    if (error) error.hidden = true;
  }

  function updateProgress() {
    const answered = cards.filter(isAnswered).length;
    const pct = Math.round((answered / cards.length) * 100);
    answeredCount.textContent = `${answered} / ${cards.length}`;
    progressPercent.textContent = `${pct}%`;
    progressRing.style.setProperty('--progress', `${pct}%`);
    [...dotsContainer.children].forEach((dot, i) => {
      dot.classList.toggle('answered', isAnswered(cards[i]));
      dot.classList.toggle('active', i === current);
    });
    document.querySelectorAll('.section-nav button').forEach(btn => {
      const type = btn.dataset.type;
      const typeCards = cards.filter(c => c.dataset.type === type);
      btn.classList.toggle('complete', typeCards.every(isAnswered));
    });
  }

  function showCard(index, options = {}) {
    current = Math.max(0, Math.min(index, cards.length - 1));
    cards.forEach((card, i) => card.hidden = i !== current);
    prevBtn.disabled = current === 0;
    nextBtn.hidden = current === cards.length - 1;
    reviewBtn.hidden = current !== cards.length - 1;
    reviewBtn.disabled = !cards.every(isAnswered);
    updateProgress();
    const target = cards[current];
    if (!target || options.scroll === false) return;
    requestAnimationFrame(() => {
      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start', inline: 'nearest' });
      target.querySelector('h2')?.focus({ preventScroll: true });
    });
  }

  function navigateTo(index) {
    const target = Math.max(0, Math.min(index, cards.length - 1));
    if (target > current) {
      for (let i = current; i < target; i += 1) {
        const validity = answerValidity(cards[i]);
        if (!validity.valid) {
          if (i !== current) showCard(i);
          showQuestionError(cards[i], validity.message);
          return false;
        }
        clearQuestionError(cards[i]);
      }
    }
    clearQuestionError(cards[current]);
    showCard(target);
    saveDraft();
    return true;
  }

  cards.forEach((card, i) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.title = fmt('question', { count: i + 1 });
    dot.addEventListener('click', () => navigateTo(i));
    dotsContainer.appendChild(dot);
    card.addEventListener('change', () => { clearQuestionError(card); saveDraft(); updateProgress(); });
    card.querySelector('.sortable-list')?.addEventListener('click', () => {
      card.dataset.touched = '1'; saveDraft(); updateProgress();
    });
    card.querySelector('.sortable-list')?.addEventListener('drop', () => {
      card.dataset.touched = '1'; saveDraft(); updateProgress();
    });
  });

  document.querySelectorAll('.section-nav button').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = cards.findIndex(c => c.dataset.type === btn.dataset.type);
      if (idx >= 0) navigateTo(idx);
    });
  });

  function serializeDraft() {
    const data = { fields: {}, orders: {}, touched: {}, current };
    new FormData(form).forEach((value, key) => data.fields[key] = value);
    document.querySelectorAll('.sortable-list').forEach(list => data.orders[list.dataset.orderList] = orderValue(list));
    cards.forEach(c => { if (c.dataset.touched) data.touched[c.dataset.qid] = c.dataset.touched; });
    return data;
  }

  function saveDraft() {
    try { localStorage.setItem(storageKey, JSON.stringify(serializeDraft())); } catch (_) {}
  }

  function applyDraft(data) {
    if (!data) return;
    Object.entries(data.fields || {}).forEach(([name, value]) => {
      // Security counters are never restored from localStorage; server/database values are authoritative.
      if (name.startsWith('security_')) return;
      const fields = [...form.elements].filter(el => el.name === name);
      fields.forEach(el => {
        if (el.type === 'radio') el.checked = el.value === value;
        else if (el.tagName === 'SELECT') el.value = value;
        else if (el.type !== 'hidden' || !el.name.startsWith('security_')) el.value = value;
      });
    });
    Object.entries(data.orders || {}).forEach(([qid, values]) => {
      const list = document.querySelector(`[data-order-list="${qid}"]`);
      if (!list) return;
      values.forEach(v => {
        const item = list.querySelector(`[data-value="${v}"]`);
        if (item) list.appendChild(item);
      });
      syncOrder(list);
    });
    Object.entries(data.touched || {}).forEach(([qid, value]) => {
      const card = cards.find(c => c.dataset.qid === qid);
      if (card) card.dataset.touched = value;
      const touched = document.getElementById(`order_touched_${qid}`);
      if (touched) touched.value = value;
    });
    current = Number.isInteger(data.current) ? data.current : 0;
  }

  function serverDraft() {
    const answers = window.AS_SERVER_DRAFT || {};
    const fields = {};
    const orders = {};
    const touched = {};
    Object.entries(answers).forEach(([qid, value]) => {
      if (qid.endsWith('__touched')) { touched[qid.replace('__touched', '')] = value; return; }
      if (Array.isArray(value)) orders[qid] = value;
      else if (value && typeof value === 'object') Object.entries(value).forEach(([left, match]) => { fields[`q_${qid}__${left}`] = match; });
      else fields[`q_${qid}`] = value;
    });
    return { fields, orders, touched, current: 0 };
  }

  function restoreDraft() {
    applyDraft(serverDraft());
    let data;
    try { data = JSON.parse(localStorage.getItem(storageKey) || 'null'); } catch (_) { return; }
    applyDraft(data);
  }

  prevBtn.addEventListener('click', () => navigateTo(current - 1));
  nextBtn.addEventListener('click', () => navigateTo(current + 1));
  reviewBtn.addEventListener('click', () => {
    const answered = cards.filter(isAnswered).length;
    if (answered !== cards.length) {
      const invalidIndex = cards.findIndex(card => !isAnswered(card));
      if (invalidIndex >= 0) navigateTo(invalidIndex);
      showQuestionError(cards[invalidIndex], answerValidity(cards[invalidIndex]).message);
      return;
    }
    document.getElementById('modalAnswered').textContent = answered;
    document.getElementById('modalMissing').textContent = cards.length - answered;
    document.getElementById('reviewMessage').textContent = answered === cards.length
      ? fmt('allAnswered', { count: cards.length })
      : fmt('missing', { count: cards.length - answered });
    modal.hidden = false;
  });
  closeReview.addEventListener('click', () => modal.hidden = true);
  modal.addEventListener('click', e => { if (e.target === modal) modal.hidden = true; });
  confirmSubmit.addEventListener('click', () => {
    if (!cards.every(isAnswered)) return;
    document.querySelectorAll('.sortable-list').forEach(syncOrder);
    syncSecurityFields();
    localStorage.removeItem(storageKey);
    submitting = true;
    confirmSubmit.disabled = true;
    confirmSubmit.textContent = fmt('submitting');
    form.submit();
  });

  syncSecurityFields();
  restoreDraft();
  showCard(current, { scroll: false });
  if (window.AS_INVALID_QUESTION) {
    const invalidIndex = cards.findIndex(card => card.dataset.qid === String(window.AS_INVALID_QUESTION));
    if (invalidIndex >= 0) {
      showCard(invalidIndex, { scroll: false });
      showQuestionError(cards[invalidIndex], answerValidity(cards[invalidIndex]).message);
    }
  }
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.target.closest('input, textarea, select, button')) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); navigateTo(current - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); navigateTo(current + 1); }
  });
})();

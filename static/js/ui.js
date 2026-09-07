// Dismissible flash toasts and one-time notices.
(() => {
  const ui = window.AS_UI_I18N || {};
  const removeWithMotion = (el) => {
    if (!el || el.dataset.closing === '1') return;
    el.dataset.closing = '1';
    el.classList.add('is-leaving');
    window.setTimeout(() => el.remove(), 220);
  };

  document.querySelectorAll('[data-toast]').forEach((toast) => {
    const close = toast.querySelector('[data-dismiss-toast]');
    close?.addEventListener('click', () => removeWithMotion(toast));

    const timeout = Number.parseInt(toast.dataset.timeout || '5200', 10);
    if (Number.isFinite(timeout) && timeout > 0) {
      let remaining = timeout;
      let startedAt = Date.now();
      let timer = window.setTimeout(() => removeWithMotion(toast), remaining);
      const pause = () => {
        window.clearTimeout(timer);
        remaining = Math.max(0, remaining - (Date.now() - startedAt));
      };
      const resume = () => {
        if (toast.dataset.closing === '1' || remaining <= 0) return;
        startedAt = Date.now();
        timer = window.setTimeout(() => removeWithMotion(toast), remaining);
      };
      toast.addEventListener('mouseenter', pause);
      toast.addEventListener('mouseleave', resume);
      toast.addEventListener('focusin', pause);
      toast.addEventListener('focusout', resume);
    }
  });

  document.querySelectorAll('[data-dismiss-notice]').forEach((button) => {
    button.addEventListener('click', () => removeWithMotion(button.closest('[data-credential-box]')));
  });
})();

(() => {
  const ui = window.AS_UI_I18N || {};
  const sidebar = document.querySelector('[data-teacher-sidebar]');
  const toggle = document.querySelector('[data-sidebar-toggle]');
  if (!sidebar || !toggle) return;
  const storageKey = 'assessmentStudio.teacherSidebarCollapsed';
  const desktop = window.matchMedia('(min-width: 1120px)');

  const applySidebarState = () => {
    const collapsed = desktop.matches && localStorage.getItem(storageKey) === '1';
    document.body.classList.toggle('sidebar-is-collapsed', collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.setAttribute('aria-label', collapsed ? ui.expandNavigation : ui.collapseNavigation);
  };

  toggle.addEventListener('click', () => {
    const collapsed = !document.body.classList.contains('sidebar-is-collapsed');
    localStorage.setItem(storageKey, collapsed ? '1' : '0');
    applySidebarState();
  });
  desktop.addEventListener('change', applySidebarState);
  applySidebarState();
})();

(() => {
  const ui = window.AS_UI_I18N || {};
  const layer = document.querySelector('[data-more-layer]');
  const trigger = document.querySelector('[data-more-open]');
  if (!layer || !trigger) return;
  const sheet = layer.querySelector('[role="dialog"]');
  const closeButtons = layer.querySelectorAll('[data-more-close]');
  let returnFocus = null;

  const focusable = () => Array.from(sheet.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'));
  const close = () => {
    if (layer.hidden) return;
    layer.hidden = true;
    document.body.classList.remove('mobile-sheet-open');
    trigger.setAttribute('aria-expanded', 'false');
    returnFocus?.focus();
  };
  const open = () => {
    returnFocus = document.activeElement;
    layer.hidden = false;
    document.body.classList.add('mobile-sheet-open');
    trigger.setAttribute('aria-expanded', 'true');
    window.requestAnimationFrame(() => sheet.focus());
  };

  trigger.addEventListener('click', open);
  closeButtons.forEach((button) => button.addEventListener('click', close));
  layer.querySelectorAll('a[href]').forEach((link) => link.addEventListener('click', close));
  document.addEventListener('keydown', (event) => {
    if (layer.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    const items = focusable();
    if (!items.length) {
      event.preventDefault();
      sheet.focus();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === sheet)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();

(() => {
  const ui = window.AS_UI_I18N || {};
  document.querySelectorAll('form').forEach((form) => {
    const radios = Array.from(form.querySelectorAll('input[name="password_mode"]'));
    const manual = form.querySelector('input[name="manual_password"]');
    if (!radios.length || !manual) return;
    const sync = () => {
      const mode = radios.find((radio) => radio.checked)?.value || 'auto';
      const manualMode = mode === 'manual';
      manual.disabled = !manualMode;
      manual.closest('label')?.classList.toggle('field-muted', !manualMode);
      if (!manualMode) manual.value = '';
    };
    radios.forEach((radio) => radio.addEventListener('change', sync));
    sync();
  });

  const box = document.querySelector('[data-credential-box]');
  const copyButton = document.querySelector('[data-copy-credentials]');
  copyButton?.addEventListener('click', async () => {
    const text = box?.dataset.copyText || '';
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      const original = copyButton.textContent;
      copyButton.textContent = ui.copied || original;
      window.setTimeout(() => { copyButton.textContent = original; }, 1800);
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
  });
})();

// Generic teacher modals for lightweight edit flows.
(() => {
  const openDialog = (dialog) => {
    if (!dialog) return;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    window.setTimeout(() => dialog.querySelector('input:not([type="hidden"]), select, textarea')?.focus(), 30);
  };
  const closeDialog = (dialog) => {
    if (!dialog) return;
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  };

  document.querySelectorAll('[data-close-modal]').forEach((button) => {
    button.addEventListener('click', () => closeDialog(button.closest('dialog')));
  });
  document.querySelectorAll('dialog.app-modal').forEach((dialog) => {
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog && !dialog.hasAttribute('data-static-modal')) closeDialog(dialog);
    });
    if (dialog.hasAttribute('data-static-modal')) {
      dialog.addEventListener('cancel', event => event.preventDefault());
    }
  });

  document.querySelectorAll('[data-open-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (button.disabled) return;
      const dialog = document.getElementById(button.dataset.openModal || '');
      if (!dialog) return;
      const form = dialog.querySelector('form');
      if (form?.dataset.resetOnOpen === '1') {
        form.reset();
        form.querySelectorAll('input[name="password_mode"]:checked').forEach((radio) => {
          radio.dispatchEvent(new Event('change', { bubbles: true }));
        });
      }
      openDialog(dialog);
    });
  });

  const studentModal = document.getElementById('studentEditModal');
  const studentForm = document.getElementById('studentEditForm');
  document.querySelectorAll('[data-open-student-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!studentModal || !studentForm) return;
      studentForm.action = button.dataset.url || '';
      studentForm.reset();
      studentForm.elements.full_name.value = button.dataset.name || '';
      studentForm.elements.email.value = button.dataset.email || '';
      studentForm.elements.section_id.value = button.dataset.sectionId || '';
      studentForm.elements.student_code.value = button.dataset.code || '';
      studentForm.elements.notes.value = button.dataset.notes || '';
      studentForm.elements.is_active.checked = button.dataset.active === '1';
      openDialog(studentModal);
    });
  });

  const passwordModal = document.getElementById('passwordResetModal');
  const passwordForm = document.getElementById('passwordResetForm');
  document.querySelectorAll('[data-open-password-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!passwordModal || !passwordForm || button.disabled) return;
      passwordForm.action = button.dataset.url || '';
      passwordForm.reset();
      const label = passwordModal.querySelector('[data-password-student]');
      if (label) label.textContent = [button.dataset.name, button.dataset.email].filter(Boolean).join(' · ');
      const auto = passwordForm.querySelector('input[name="password_mode"][value="auto"]');
      if (auto) auto.checked = true;
      const manual = passwordForm.querySelector('input[name="manual_password"]');
      if (manual) {
        manual.disabled = true;
        manual.value = '';
        manual.closest('label')?.classList.add('field-muted');
      }
      const mustChange = passwordForm.querySelector('input[name="must_change_password"]');
      if (mustChange) mustChange.checked = true;
      openDialog(passwordModal);
    });
  });

  const sectionModal = document.getElementById('sectionEditModal');
  const sectionForm = document.getElementById('sectionEditForm');
  document.querySelectorAll('[data-open-section-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!sectionModal || !sectionForm) return;
      sectionForm.action = button.dataset.url || '';
      sectionForm.elements.name.value = button.dataset.name || '';
      sectionForm.elements.description.value = button.dataset.description || '';
      openDialog(sectionModal);
    });
  });

  const subjectModal = document.getElementById('subjectEditModal');
  const subjectForm = document.getElementById('subjectEditForm');
  document.querySelectorAll('[data-open-subject-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!subjectModal || !subjectForm) return;
      subjectForm.action = button.dataset.url || '';
      subjectForm.elements.name.value = button.dataset.name || '';
      subjectForm.elements.description.value = button.dataset.description || '';
      openDialog(subjectModal);
    });
  });

  const categoryModal = document.getElementById('categoryEditModal');
  const categoryForm = document.getElementById('categoryEditForm');
  document.querySelectorAll('[data-open-category-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!categoryModal || !categoryForm) return;
      categoryForm.action = button.dataset.url || '';
      categoryForm.elements.subject_id.value = button.dataset.subjectId || '';
      categoryForm.elements.name.value = button.dataset.name || '';
      categoryForm.elements.description.value = button.dataset.description || '';
      categoryForm.elements.sort_order.value = button.dataset.sortOrder || '0';
      openDialog(categoryModal);
    });
  });
})();

// SweetAlert2 destructive-action confirmations, with a native fallback for offline classrooms.
(() => {
  const yesText = document.body.dataset.confirmYes;
  const noText = document.body.dataset.confirmNo;

  const ask = async (title, text) => {
    if (window.Swal?.fire) {
      const result = await window.Swal.fire({
        title: title || document.body.dataset.confirmTitle,
        text: text || '',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: yesText,
        cancelButtonText: noText,
        reverseButtons: true,
        focusCancel: true,
        confirmButtonColor: '#d45454'
      });
      return Boolean(result.isConfirmed);
    }
    return window.confirm([title, text].filter(Boolean).join('\n\n'));
  };

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      if (form.dataset.confirmed === '1') return;
      event.preventDefault();
      const confirmed = await ask(form.dataset.confirmTitle, form.dataset.confirmText);
      if (!confirmed) return;
      form.dataset.confirmed = '1';
      form.requestSubmit();
    });
  });

  document.querySelectorAll('[data-confirm-submit]').forEach((button) => {
    button.addEventListener('click', async (event) => {
      if (button.dataset.confirmed === '1') return;
      event.preventDefault();
      const confirmed = await ask(button.dataset.confirmTitle, button.dataset.confirmText);
      if (!confirmed) return;
      button.dataset.confirmed = '1';
      button.form?.requestSubmit(button);
    });
  });
})();

(() => {
  const form = document.querySelector('[data-bulk-question-form]');
  if (!form) return;
  form.addEventListener('submit', async (event) => {
    if (form.dataset.bulkConfirmed === '1') return;
    const action = form.elements.action?.value;
    if (action !== 'archive') return;
    event.preventDefault();
    const yesText = document.body.dataset.confirmYes;
    const noText = document.body.dataset.confirmNo;
    let confirmed = false;
    if (window.Swal?.fire) {
      const result = await window.Swal.fire({
        title: form.dataset.confirmTitle || document.body.dataset.confirmTitle,
        text: form.dataset.confirmText || '',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: yesText,
        cancelButtonText: noText,
        reverseButtons: true,
        focusCancel: true,
        confirmButtonColor: '#d45454'
      });
      confirmed = Boolean(result.isConfirmed);
    } else {
      confirmed = window.confirm([form.dataset.confirmTitle, form.dataset.confirmText].filter(Boolean).join('\n\n'));
    }
    if (!confirmed) return;
    form.dataset.bulkConfirmed = '1';
    form.requestSubmit();
  });
})();

(() => {
  const dialog = document.getElementById('studentRulesModal');
  if (!dialog) return;
  const checkbox = dialog.querySelector('input[name="accept_rules"]');
  const submit = dialog.querySelector('[data-rules-accept]');
  const sync = () => { submit.disabled = !checkbox.checked; };
  checkbox.addEventListener('change', sync);
  sync();
  if (!dialog.open && typeof dialog.showModal === 'function') dialog.showModal();
})();

// Exam-version rename modal.
(() => {
  const dialog = document.getElementById('versionEditModal');
  const form = document.getElementById('versionEditForm');
  if (!dialog || !form) return;
  document.querySelectorAll('[data-open-version-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      form.action = button.dataset.url || '';
      form.elements.name.value = button.dataset.name || '';
      if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open','');
      window.setTimeout(() => form.elements.name.focus(), 30);
    });
  });
})();

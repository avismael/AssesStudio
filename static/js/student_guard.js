(() => {
  const stop = (event) => { event.preventDefault(); return false; };
  document.addEventListener('contextmenu', stop, {capture:true});
  document.addEventListener('copy', stop, {capture:true});
  document.addEventListener('dragstart', (e) => { if (!e.target.closest('input,textarea')) stop(e); }, {capture:true});
  document.addEventListener('keydown', (event) => {
    const key = event.key.toLowerCase();
    const blocked = event.key === 'F12' ||
      ((event.ctrlKey || event.metaKey) && ['u','s','p'].includes(key)) ||
      ((event.ctrlKey || event.metaKey) && event.shiftKey && ['i','j','c'].includes(key));
    if (blocked) stop(event);
  }, {capture:true});
})();

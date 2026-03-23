/* EduPlatform — countdown.js
   Live due-date countdowns for assignment cards.
   Usage: <span class="due-countdown" data-due="2025-12-31T23:59"></span>
*/

(function () {
  function formatDiff(ms) {
    if (ms <= 0) return { text: 'Overdue', cls: 'urgent' };
    const s   = Math.floor(ms / 1000);
    const m   = Math.floor(s / 60);
    const h   = Math.floor(m / 60);
    const d   = Math.floor(h / 24);
    if (d > 1)  return { text: `${d}d ${h % 24}h left`, cls: 'ok' };
    if (h >= 1) return { text: `${h}h ${m % 60}m left`, cls: 'soon' };
    return      { text: `${m}m left`, cls: 'urgent' };
  }

  function updateAll() {
    document.querySelectorAll('.due-countdown').forEach(el => {
      const due = new Date(el.dataset.due);
      if (isNaN(due)) return;
      const { text, cls } = formatDiff(due - Date.now());
      el.textContent  = text;
      el.className    = `due-countdown countdown ${cls}`;
    });
  }

  updateAll();
  setInterval(updateAll, 30000);
})();

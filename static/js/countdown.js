/**
 * EduPlatform — countdown.js
 * Member 3 ONLY
 *
 * Live due-date countdown for assignment cards.
 *
 * Usage in templates (Member 3 & Member 4 classwork tabs):
 *   <span class="due-countdown" data-due="2025-12-31T23:59:00"></span>
 *
 * The span is updated every 60 seconds automatically.
 * CSS classes applied: countdown ok | soon | urgent
 *   ok     — more than 48 h remaining  (green)
 *   soon   — 1 h – 48 h remaining     (amber)
 *   urgent — under 1 h / overdue      (red)
 */

(function () {
  'use strict';

  /**
   * Format a millisecond difference into a human-readable string.
   * @param {number} ms  Positive = future, negative/zero = overdue.
   * @returns {{ text: string, cls: string }}
   */
  function formatDiff(ms) {
    if (ms <= 0) return { text: 'Overdue', cls: 'urgent' };

    const totalSeconds = Math.floor(ms / 1000);
    const minutes      = Math.floor(totalSeconds / 60);
    const hours        = Math.floor(minutes / 60);
    const days         = Math.floor(hours / 24);

    if (days >= 2) {
      return { text: `${days}d ${hours % 24}h left`, cls: 'ok' };
    }
    if (hours >= 1) {
      const remainMins = minutes % 60;
      const cls        = hours < 48 ? 'soon' : 'ok';
      return { text: `${hours}h ${remainMins}m left`, cls };
    }
    return { text: `${minutes}m left`, cls: 'urgent' };
  }

  function updateAll() {
    const now = Date.now();
    document.querySelectorAll('.due-countdown[data-due]').forEach(el => {
      const due = new Date(el.dataset.due);
      if (isNaN(due.getTime())) return;
      const { text, cls } = formatDiff(due.getTime() - now);
      el.textContent = text;
      el.className   = `due-countdown countdown ${cls}`;
    });
  }

  // Run immediately, then refresh every 60 seconds
  updateAll();
  setInterval(updateAll, 60_000);
})();

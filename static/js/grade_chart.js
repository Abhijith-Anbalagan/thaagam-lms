/**
 * EduPlatform — grade_chart.js
 * Member 3 ONLY
 *
 * Renders the student grade bar chart using Chart.js (loaded from CDN).
 *
 * Required globals — set in the student grade template before this script:
 *   window.GRADE_LABELS  {string[]}  Assignment titles
 *   window.GRADE_SCORES  {number[]}  Student's scores
 *   window.GRADE_MAX     {number[]}  Max scores per assignment
 */

(function () {
  'use strict';

  const canvas = document.getElementById('gradeChart');
  if (!canvas) return;

  const labels = window.GRADE_LABELS || [];
  const scores = window.GRADE_SCORES || [];
  const maxArr = window.GRADE_MAX    || [];

  if (!labels.length) {
    canvas.parentElement.innerHTML =
      '<div class="empty-state" style="padding:32px;"><p>No graded assignments yet.</p></div>';
    return;
  }

  /** Dynamically load Chart.js 4 from CDN, then render. */
  function loadChartJs(callback) {
    if (window.Chart) { callback(); return; }
    const script  = document.createElement('script');
    script.src    = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    script.onload = callback;
    script.onerror = () => console.error('[grade_chart] Failed to load Chart.js');
    document.head.appendChild(script);
  }

  function render() {
    new window.Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label:           'Your Score',
            data:            scores,
            backgroundColor: 'rgba(76, 104, 215, 0.78)',
            borderColor:     '#4c68d7',
            borderWidth:     1,
            borderRadius:    5,
            borderSkipped:   false,
          },
          {
            label:           'Max Score',
            data:            maxArr,
            backgroundColor: 'rgba(232, 230, 224, 0.85)',
            borderColor:     '#ccc',
            borderWidth:     1,
            borderRadius:    5,
            borderSkipped:   false,
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 12 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const idx = ctx.dataIndex;
                if (ctx.datasetIndex === 0 && maxArr[idx]) {
                  const pct = Math.round((scores[idx] / maxArr[idx]) * 100);
                  return ` ${ctx.dataset.label}: ${ctx.raw} (${pct}%)`;
                }
                return ` ${ctx.dataset.label}: ${ctx.raw}`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#f0efec' },
            ticks: { font: { family: 'JetBrains Mono', size: 11 } },
          },
          x: {
            grid: { display: false },
            ticks: {
              font: { family: 'Inter', size: 11 },
              maxRotation: 35,
              minRotation: 0,
            },
          },
        },
      },
    });
  }

  loadChartJs(render);
})();

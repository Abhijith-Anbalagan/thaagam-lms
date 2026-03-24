/* EduPlatform — grade_chart.js
   Renders the student grade bar chart using Chart.js.

   Required globals (set in template):
     window.GRADE_LABELS  — array of assignment titles
     window.GRADE_SCORES  — array of student scores
     window.GRADE_MAX     — array of max scores
*/

(function () {
  const canvas = document.getElementById('gradeChart');
  if (!canvas) return;

  const labels = window.GRADE_LABELS || [];
  const scores = window.GRADE_SCORES || [];
  const maxArr = window.GRADE_MAX    || [];

  if (!labels.length) return;

  // Dynamically load Chart.js from CDN if not already present
  function loadChartJs(cb) {
    if (window.Chart) { cb(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    s.onload = cb;
    document.head.appendChild(s);
  }

  loadChartJs(function () {
    const datasets = [
      {
        label: 'Score',
        data: scores,
        backgroundColor: 'rgba(76,104,215,0.75)',
        borderColor:     '#4c68d7',
        borderWidth: 1,
        borderRadius: 5,
      },
    ];

    if (maxArr && maxArr.length) {
      datasets.push({
        label: 'Max Score',
        data: maxArr,
        backgroundColor: 'rgba(232,230,224,0.8)',
        borderColor:     '#ccc',
        borderWidth: 1,
        borderRadius: 5,
      });
    }

    new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f0efec' } },
          x: { grid: { display: false } },
        },
      },
    });
  });
})();

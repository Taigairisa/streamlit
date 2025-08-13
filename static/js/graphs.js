// Graphs page behavior: render charts and handle range changes
document.addEventListener('DOMContentLoaded', function () {
  try {
    const dataEl = document.getElementById('chartData');
    if (dataEl && window.Chart) {
      const parsed = JSON.parse(dataEl.textContent || '{}');
      const labels = parsed.labels || [];
      const monthly = parsed.monthly || [];
      const cumulative = parsed.cumulative || [];

      const monthlyCtx = document.getElementById('monthly_chart');
      const cumulativeCtx = document.getElementById('cumulative_chart');
      if (monthlyCtx) {
        new Chart(monthlyCtx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: '当月収支',
              data: monthly,
              borderColor: 'rgba(54, 162, 235, 1)',
              backgroundColor: 'rgba(54, 162, 235, 0.2)',
              tension: 0.2,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: {
              x: { title: { display: true, text: '月' } },
              y: { title: { display: true, text: '当月収支' } },
            }
          }
        });
      }
      if (cumulativeCtx) {
        new Chart(cumulativeCtx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: '累計資産',
              data: cumulative,
              borderColor: 'rgba(255, 159, 64, 1)',
              backgroundColor: 'rgba(255, 159, 64, 0.2)',
              tension: 0.2,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: {
              x: { title: { display: true, text: '月' } },
              y: { title: { display: true, text: '累計資産' } },
            }
          }
        });
      }
    }
  } catch (e) {
    console.error('Failed to render charts:', e);
  }

  const form = document.getElementById('rangeForm');
  const startSel = document.getElementById('startMonth');
  const endSel = document.getElementById('endMonth');
  if (form && startSel && endSel) {
    const submit = () => form.submit();
    startSel.addEventListener('change', submit);
    endSel.addEventListener('change', submit);
  }
});

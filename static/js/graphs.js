// Graphs page behavior: render charts and handle range changes
document.addEventListener('DOMContentLoaded', function () {
  try {
    const monthlyDataEl = document.getElementById('monthlyChartData');
    const cumulativeDataEl = document.getElementById('cumulativeChartData');
    if (monthlyDataEl && cumulativeDataEl && window.vegaEmbed) {
      const monthlySpec = JSON.parse(monthlyDataEl.textContent || '{}');
      const cumulativeSpec = JSON.parse(cumulativeDataEl.textContent || '{}');
      vegaEmbed('#monthly_chart', monthlySpec, { actions: false }).catch(console.error);
      vegaEmbed('#cumulative_chart', cumulativeSpec, { actions: false }).catch(console.error);
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


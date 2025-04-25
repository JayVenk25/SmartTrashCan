let categoryChart, commonChart;
async function loadStats(period) {
  const res = await fetch(`/stats-data/${period}`);
  const data = await res.json();
  document.getElementById('total').textContent = data.total_disposed;
  document.getElementById('footprint').textContent = data.carbon_footprint;
  document.getElementById('recyclable').textContent = data.recyclable;
  document.getElementById('compostable').textContent = data.compostable;
  const ctx1 = document.getElementById('categoryChart').getContext('2d');
  if (categoryChart) categoryChart.destroy();
  categoryChart = new Chart(ctx1, {
    type: 'pie',
    data: {
      labels: ['Recyclable','Compostable','Hazardous','General Waste'],
      datasets: [{ data: [data.recyclable,data.compostable,data.hazardous,data.general_waste] }]
    }
  });
  const ctx2 = document.getElementById('commonChart').getContext('2d');
  if (commonChart) commonChart.destroy();
  commonChart = new Chart(ctx2, {
    type: 'bar',
    data: {
      labels: data.common_items.map(i=>i[0]),
      datasets: [{ data: data.common_items.map(i=>i[1]) }]
    }
  });
  const recentEl = document.getElementById('recent');
  recentEl.innerHTML = '';
  data.recent_items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = `${new Date(item.timestamp).toLocaleString()}: ${item.detected_objects.join(', ')}`;
    recentEl.appendChild(li);
  });
}
document.querySelectorAll('.controls button').forEach(btn => {
  btn.addEventListener('click', ()=> loadStats(btn.dataset.period));
});
loadStats('all');
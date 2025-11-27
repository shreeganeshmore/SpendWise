
let categoryBarChart, categoryPieChart, monthlyLineChart;

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function loadSummary() {
  try {
    const data = await fetchJSON("/api/summary");
    document.getElementById("todayAmount").innerText = "₹" + data.today.toFixed(2);
    document.getElementById("weekAmount").innerText = "₹" + data.week.toFixed(2);
    document.getElementById("monthAmount").innerText = "₹" + data.month.toFixed(2);
  } catch (e) {
    console.error(e);
  }
}

async function loadCategoryCharts() {
  try {
    const data = await fetchJSON("/api/category-data");
    const ctxBar = document.getElementById("categoryBar");
    const ctxPie = document.getElementById("categoryPie");

    if (categoryBarChart) categoryBarChart.destroy();
    if (categoryPieChart) categoryPieChart.destroy();

    categoryBarChart = new Chart(ctxBar, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Amount (₹)",
          data: data.values
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }
      }
    });

    categoryPieChart = new Chart(ctxPie, {
      type: "pie",
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values
        }]
      },
      options: {
        responsive: true
      }
    });
  } catch (e) {
    console.error(e);
  }
}

async function loadMonthlyChart() {
  try {
    const data = await fetchJSON("/api/monthly-data");
    const ctx = document.getElementById("monthlyLine");
    if (monthlyLineChart) monthlyLineChart.destroy();

    monthlyLineChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Monthly Total (₹)",
          data: data.values,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } }
      }
    });
  } catch (e) {
    console.error(e);
  }
}

async function runPrediction() {
  const msgEl = document.getElementById("predictionMsg");
  const textEl = document.getElementById("predictionText");
  msgEl.innerText = "Running prediction...";
  try {
    const data = await fetchJSON("/predict");
    if (data.ok) {
      textEl.innerText = "₹" + data.prediction.toFixed(2);
      msgEl.innerText = "Based on your past monthly spending.";
    } else {
      textEl.innerText = "--";
      msgEl.innerText = data.message || "Prediction unavailable.";
    }
  } catch (e) {
    textEl.innerText = "--";
    msgEl.innerText = "Error running prediction.";
  }
}

async function exportReport() {
  try {
    const data = await fetchJSON("/export_report");
    if (data.ok) {
      alert("Report generated! Check the 'reports' and 'charts' folders on the server.");
    } else {
      alert("Could not generate report.");
    }
  } catch (e) {
    alert("Error generating report.");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  loadSummary();
  loadCategoryCharts();
  loadMonthlyChart();

  const predictBtn = document.getElementById("predictBtn");
  if (predictBtn) {
    predictBtn.addEventListener("click", runPrediction);
  }

  const exportBtn = document.getElementById("exportBtn");
  if (exportBtn) {
    exportBtn.addEventListener("click", exportReport);
  }
});

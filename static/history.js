document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('occupancyChart').getContext('2d');
    const selectedDateEl = document.getElementById('selected-date');
    const chartInfoEl = document.getElementById('chart-info');
    const btnPrevDay = document.getElementById('btn-prev-day');
    const btnNextDay = document.getElementById('btn-next-day');

    let occupancyChart;
    let currentDate = new Date();
    // Nastavíme výchozí datum na včerejšek (protože dnes může mít neúplná data)
    currentDate.setDate(currentDate.getDate() - 1);

    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function formatDateDisplay(date) {
        return date.toLocaleDateString('cs-CZ', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    async function fetchHistoryData(dateStr) {
        try {
            const response = await fetch(`/stats/history?date=${dateStr}`);
            const data = await response.json();

            if (data.error) {
                chartInfoEl.textContent = `Chyba: ${data.error}`;
                chartInfoEl.style.color = '#ef4444';
                return null;
            }

            if (data.length === 0) {
                chartInfoEl.textContent = 'Pro vybraný den nejsou k dispozici žádná data.';
                chartInfoEl.style.color = '#f59e0b';
                return null;
            }

            chartInfoEl.textContent = `Zobrazeno ${data.length} hodinových průměrů`;
            chartInfoEl.style.color = '#94a3b8';
            return data;

        } catch (error) {
            console.error('Error fetching history data:', error);
            chartInfoEl.textContent = 'Chyba při načítání dat.';
            chartInfoEl.style.color = '#ef4444';
            return null;
        }
    }

    function renderChart(labels, dataPoints) {
        if (occupancyChart) {
            occupancyChart.destroy();
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.5)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

        occupancyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Průměr vozidel',
                    data: dataPoints,
                    borderColor: '#38bdf8',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    pointBackgroundColor: '#38bdf8',
                    pointBorderColor: '#fff',
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#94a3b8',
                        bodyColor: '#f8fafc',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    async function loadDataForDate(date) {
        const dateStr = formatDate(date);
        selectedDateEl.textContent = formatDateDisplay(date);

        const data = await fetchHistoryData(dateStr);

        if (data && data.length > 0) {
            const labels = data.map(d => {
                const date = new Date(d.hour_bucket);
                return date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });
            });
            const counts = data.map(d => d.avg_count);
            renderChart(labels, counts);
        } else {
            // Vykreslíme prázdný graf
            renderChart([], []);
        }

        // Aktualizujeme stav tlačítek
        updateButtonStates();
    }

    function updateButtonStates() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const current = new Date(currentDate);
        current.setHours(0, 0, 0, 0);

        // Disable next button if current date is today or later
        if (current >= today) {
            btnNextDay.disabled = true;
            btnNextDay.classList.add('disabled');
        } else {
            btnNextDay.disabled = false;
            btnNextDay.classList.remove('disabled');
        }
    }

    btnPrevDay.addEventListener('click', () => {
        currentDate.setDate(currentDate.getDate() - 1);
        loadDataForDate(currentDate);
    });

    btnNextDay.addEventListener('click', () => {
        if (!btnNextDay.disabled) {
            currentDate.setDate(currentDate.getDate() + 1);
            loadDataForDate(currentDate);
        }
    });

    // Initial load
    loadDataForDate(currentDate);
});

document.addEventListener('DOMContentLoaded', () => {
    const currentCountEl = document.getElementById('current-count');
    const statusBadgeEl = document.getElementById('status-badge');
    const lastUpdatedEl = document.getElementById('last-updated-time');
    const ctx = document.getElementById('occupancyChart').getContext('2d');

    let occupancyChart;

    // Configuration
    const REFRESH_INTERVAL = 30000; // 30 seconds
    const CAPACITY_THRESHOLD_LOW = 30;
    const CAPACITY_THRESHOLD_HIGH = 40; // Example values, adjust based on real capacity

    function loadStoredData() {
        const stored = localStorage.getItem('lastOccupancy');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                // Check if data is not too old (e.g. 24 hours) - optional, but good practice
                // For now, just show it as requested
                currentCountEl.textContent = data.count;
                currentCountEl.classList.remove('loading');
                updateStatus(data.count);

                const date = new Date(data.timestamp);
                lastUpdatedEl.textContent = date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });

                // Add a visual indicator that this is old data, if needed. 
                // The user requested "remember last displayed value".
                // We could add (cached) to the time, but simpler is better.
            } catch (e) {
                console.error("Failed to parse stored data", e);
            }
        }
    }

    async function fetchCurrentData() {
        try {
            const response = await fetch('/current');
            const data = await response.json();

            const count = data.count || 0;
            currentCountEl.textContent = count;
            currentCountEl.classList.remove('loading');

            updateStatus(count);

            const now = new Date();
            lastUpdatedEl.textContent = now.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });

            // Store the data
            localStorage.setItem('lastOccupancy', JSON.stringify({
                count: count,
                timestamp: now.getTime()
            }));

        } catch (error) {
            console.error('Error fetching current data:', error);
            // Only show error if we don't have stored data displayed?
            // Actually, keep the error indicator but maybe keep the old value visible?
            // The original code replaced text with "Chyba načítání".
            // Let's modify to keep the old value if available but show a small error indicator? 
            // Or just stick to original behavior for error, but load stored data initially.
            // If fetch fails, we might want to keep showing the stored data but indicate it's stale.
            // For now, let's stick to the user's robust error handling if fetch fails *after* success.
            // But init logic is handled by loadStoredData.

            // If we have content (from storage), maybe don't overwrite with "Error" immediately?
            // The user didn't explicitly ask for offline mode, just "remember last value".
            // Let's stick to the current error handling for simplicity, or maybe soft fail.
            statusBadgeEl.textContent = 'Chyba načítání';
            statusBadgeEl.className = 'status-badge status-red';
        }
    }

    function updateStatus(count) {
        // Simple logic for demonstration. Ideally should be percentage based if capacity is known.
        // Let's assume a capacity of ~50 for now based on typical town squares, or just use raw numbers.

        statusBadgeEl.className = 'status-badge';

        if (count < CAPACITY_THRESHOLD_LOW) {
            statusBadgeEl.textContent = '🟢 Volno';
            statusBadgeEl.classList.add('status-green');
        } else if (count < CAPACITY_THRESHOLD_HIGH) {
            statusBadgeEl.textContent = '🟠 Mírně obsazeno';
            statusBadgeEl.classList.add('status-orange');
        } else {
            statusBadgeEl.textContent = '🔴 Plno';
            statusBadgeEl.classList.add('status-red');
        }
    }

    async function fetchStatsData() {
        try {
            const response = await fetch('/stats');
            const data = await response.json(); // Data is already sorted ASC

            const labels = data.map(d => {
                const date = new Date(d.hour_bucket);
                return date.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }); // Show hour, e.g., "14:00"
            });
            const counts = data.map(d => d.avg_count);

            renderChart(labels, counts);

        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    function renderChart(labels, dataPoints) {
        if (occupancyChart) {
            occupancyChart.destroy();
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.5)'); // Blue
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
                    pointRadius: 3,
                    pointHoverRadius: 5,
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

    // Load stored data immediately
    loadStoredData();

    // Initial load (network)
    fetchCurrentData();
    fetchStatsData();

    // Auto-refresh
    setInterval(fetchCurrentData, REFRESH_INTERVAL);
    setInterval(fetchStatsData, REFRESH_INTERVAL * 2); // Chart can handle slower updates

    // Service Worker Registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }, err => {
                    console.log('ServiceWorker registration failed: ', err);
                });
        });
    }
});

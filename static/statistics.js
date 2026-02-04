document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('occupancyChart').getContext('2d');
    const dayButtons = document.querySelectorAll('.day-button');
    const selectedDayNameEl = document.getElementById('selected-day-name');
    const chartInfoEl = document.getElementById('chart-info');

    let occupancyChart;
    let currentDay = 1; // Výchozí: pondělí

    // Názvy dní v týdnu
    const dayNames = {
        0: 'Neděle',
        1: 'Pondělí',
        2: 'Úterý',
        3: 'Středa',
        4: 'Čtvrtek',
        5: 'Pátek',
        6: 'Sobota'
    };

    // Prahové hodnoty pro barvy
    const THRESHOLD_LOW = 25;
    const THRESHOLD_HIGH = 40;

    // Funkce pro získání barvy podle počtu aut
    function getColorForValue(value) {
        if (value < THRESHOLD_LOW) {
            return '#22c55e'; // Zelená
        } else if (value <= THRESHOLD_HIGH) {
            return '#eab308'; // Oranžová
        } else {
            return '#ef4444'; // Červená
        }
    }

    async function fetchWeekdayData(day) {
        try {
            const response = await fetch(`/stats/weekday?day=${day}`);
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

            chartInfoEl.textContent = `Zobrazeno průměrů pro ${data.length} hodin`;
            chartInfoEl.style.color = '#94a3b8';
            return data;

        } catch (error) {
            console.error('Error fetching weekday data:', error);
            chartInfoEl.textContent = 'Chyba při načítání dat.';
            chartInfoEl.style.color = '#ef4444';
            return null;
        }
    }

    function filterHourRange(data) {
        // Filtrujeme pouze hodiny 5-22
        return data.filter(d => d.hour >= 5 && d.hour <= 22);
    }

    function renderChart(data) {
        if (occupancyChart) {
            occupancyChart.destroy();
        }

        // Filtrujeme hodiny 5-22
        const filteredData = filterHourRange(data);

        const labels = filteredData.map(d => `${d.hour}:00`);
        const counts = filteredData.map(d => d.avg_count);

        // Vytvoříme pole barev pro každý sloupec
        const backgroundColors = counts.map(count => getColorForValue(count));
        const borderColors = backgroundColors; // Stejné barvy pro border

        occupancyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Průměr vozidel',
                    data: counts,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
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
                        borderWidth: 1,
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y;
                                let status = '';
                                if (value < THRESHOLD_LOW) {
                                    status = '🟢 Volno';
                                } else if (value <= THRESHOLD_HIGH) {
                                    status = '🟠 Mírně obsazeno';
                                } else {
                                    status = '🔴 Plno';
                                }
                                return `${value} aut - ${status}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#94a3b8',
                            font: {
                                size: 11
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#94a3b8',
                            stepSize: 5
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    }

    async function loadDataForDay(day) {
        currentDay = day;
        selectedDayNameEl.textContent = dayNames[day];

        // Aktualizace aktivního tlačítka
        dayButtons.forEach(btn => {
            const btnDay = parseInt(btn.getAttribute('data-day'));
            if (btnDay === day) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        const data = await fetchWeekdayData(day);

        if (data && data.length > 0) {
            renderChart(data);
        } else {
            // Vykreslíme prázdný graf
            renderChart([]);
        }
    }

    // Event listenery pro tlačítka
    dayButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const day = parseInt(btn.getAttribute('data-day'));
            loadDataForDay(day);
        });
    });

    // Počáteční načtení (pondělí)
    loadDataForDay(currentDay);
});

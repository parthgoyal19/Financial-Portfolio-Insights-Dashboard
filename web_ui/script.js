document.addEventListener("DOMContentLoaded", () => {
    // Shared Chart Configuration
    Chart.defaults.color = "#94a3b8";
    Chart.defaults.font.family = "'Outfit', sans-serif";

    // 1. Performance Line Chart (Growth of 100)
    const perfCtx = document.getElementById('performanceChart').getContext('2d');
    
    // Create Gradient for Line
    const gradientBlue = perfCtx.createLinearGradient(0, 0, 0, 400);
    gradientBlue.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
    gradientBlue.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

    const gradientPurple = perfCtx.createLinearGradient(0, 0, 0, 400);
    gradientPurple.addColorStop(0, 'rgba(139, 92, 246, 0.5)');
    gradientPurple.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

    new Chart(perfCtx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [
                {
                    label: 'Stocks (Nifty 50)',
                    data: [100, 105, 102, 108, 115, 118, 114, 122, 125, 130, 128, 135],
                    borderColor: '#3b82f6',
                    backgroundColor: gradientBlue,
                    borderWidth: 3,
                    pointBackgroundColor: '#0a0a0f',
                    pointBorderColor: '#3b82f6',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Crypto (BTC)',
                    data: [100, 110, 130, 115, 90, 105, 120, 140, 135, 150, 165, 145],
                    borderColor: '#8b5cf6',
                    backgroundColor: gradientPurple,
                    borderWidth: 3,
                    pointBackgroundColor: '#0a0a0f',
                    pointBorderColor: '#8b5cf6',
                    pointBorderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { size: 13, family: 'Outfit' },
                    bodyFont: { size: 13, family: 'Outfit' },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    intersect: false,
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false,
                    },
                    border: { display: false }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false,
                    },
                    border: { display: false }
                }
            }
        }
    });

    // 2. Asset Allocation Donut Chart
    const allocCtx = document.getElementById('allocationChart').getContext('2d');
    
    new Chart(allocCtx, {
        type: 'doughnut',
        data: {
            labels: ['Stocks', 'Mutual Funds', 'Crypto'],
            datasets: [{
                data: [55, 25, 20],
                backgroundColor: [
                    '#3b82f6', // blue
                    '#10b981', // green
                    '#f59e0b'  // orange
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: {
                    display: false // We built a custom HTML legend instead
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
});

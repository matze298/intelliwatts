/* Shared canvas fallback for missing or unavailable Chart.js datasets. */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.chart-card canvas').forEach((canvas) => {
        const chart = typeof Chart === 'undefined' ? null : Chart.getChart(canvas);
        const hasValues = chart?.data.datasets.some((dataset) =>
            Array.isArray(dataset.data) && dataset.data.some((point) =>
                point !== null && point !== undefined && !(typeof point === 'number' && !Number.isFinite(point))
            )
        );
        if (hasValues) return;
        const frame = canvas.closest('.chart-frame') || canvas.parentElement;
        if (!frame || frame.querySelector('.chart-unavailable')) return;
        canvas.hidden = true;
        frame.classList.add('chart-fallback');
        canvas.parentElement.querySelector('[data-chart-total]')?.setAttribute('hidden', '');
        frame.closest('.chart-card')?.querySelector('.control-toggle-group')?.setAttribute('hidden', '');
        const fallback = document.createElement('p');
        fallback.className = 'chart-unavailable';
        fallback.textContent = typeof Chart === 'undefined'
            ? 'Charts are temporarily unavailable. Your other dashboard data is still available.'
            : 'No measurements are available for this period.';
        frame.append(fallback);
    });
});

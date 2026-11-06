/* Chart.js display normalization. Missing measurements remain gaps, never false zeroes. */
(function () {
    'use strict';
    const sportNames = {
        Ride: 'Cycling',
        VirtualRide: 'Cycling (indoor)',
        Run: 'Running',
        VirtualRun: 'Running (indoor)',
        WeightTraining: 'Strength',
    };
    const shortDate = new Intl.DateTimeFormat('en', {month: 'short', day: 'numeric', timeZone: 'UTC'});
    function displaySport(name) {
        return sportNames[name] || name || 'Other';
    }
    function validNumber(value) {
        return typeof value === 'number' && Number.isFinite(value) ? value : null;
    }
    function dateLabel(value) {
        if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
        const date = new Date(value + 'T00:00:00Z');
        return Number.isNaN(date.getTime()) ? '' : shortDate.format(date);
    }
    function weekDate(raw) {
        if (typeof raw !== 'string') return null;
        if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
            const date = new Date(raw + 'T00:00:00Z');
            return Number.isNaN(date.getTime()) ? null : date;
        }
        const match = /^(\d{2})\.(\d{2})$/.exec(raw);
        if (!match) return null;
        const day = Number(match[1]);
        const month = Number(match[2]);
        const year = new Date().getUTCFullYear();
        const date = new Date(Date.UTC(year, month - 1, day));
        return date.getUTCDate() === day && date.getUTCMonth() === month - 1 ? date : null;
    }
    function weekLabel(raw, full) {
        const start = weekDate(raw);
        if (!start) return 'Date unavailable';
        const end = new Date(start.getTime() + 6 * 86400000);
        return full ? shortDate.format(start) + ' – ' + shortDate.format(end) : shortDate.format(start);
    }
    window.IWCharts = {displaySport, validNumber, dateLabel, weekLabel};
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = "'DM Sans', sans-serif";
    Chart.defaults.color = '#667a70';
    Chart.defaults.animation = false;
    Chart.register({
        id: 'intelliwattsDataQuality',
        beforeInit(chart) {
            const data = chart.config.data;
            if (!data) return;
            for (const dataset of data.datasets || []) {
                if (!Array.isArray(dataset.data)) continue;
                dataset.data = dataset.data.map(point => {
                    if (point === null || point === undefined) return null;
                    if (typeof point === 'number') return validNumber(point);
                    if (point && typeof point === 'object') {
                        return {...point, y: validNumber(point.y)};
                    }
                    return null;
                });
                dataset.label = displaySport(dataset.label);
            }
            const labels = data.labels || [];
            if (!labels.some(label => dateLabel(label))) return;
            const xScale = chart.config.options?.scales?.x;
            if (!xScale || xScale.type === 'logarithmic') return;
            xScale.ticks = {
                ...xScale.ticks, autoSkip: true, maxTicksLimit: 7, maxRotation: 0, minRotation: 0,
                callback(value) { return dateLabel(labels[value]); }
            };
        },
    });
})();

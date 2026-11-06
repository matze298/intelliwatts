/* Chart.js theme adapter; no changes to training data, chart types, or calculations. */
(() => {
  'use strict';
  if (typeof Chart === 'undefined') return;
  const colorMap = {
    '#4f9472':'#5ee4b6','#d97761':'#ff8b76','#557c9d':'#78b8f1',
    '#18786e':'#61e4b7','#147969':'#51dbad','#89bdb5':'#a2d9cd',
    '#e6ad9e':'#ffb19c','#426c93':'#77b8f3','#9aa9a1':'#a6c5be',
    '#c89b50':'#f3c66f','#d8755c':'#ff8a75','#827a91':'#ab9ec7',
    '#76ae9a':'#70d9b5','#efa48e':'#ffbaa0','#6e91a0':'#80c2da',
    '#b7a48a':'#d6b993','#5d9b89':'#79c9ae','#647c69':'#8bb9a1',
    '#b65e4f':'#f78075','#9c7790':'#bb8eaf','#8b7a9f':'#ac9bc6',
    '#d49a6e':'#eeb087','#527d75':'#78b7a6',
    '#dcebe4':'#355e57','#b6d2c2':'#497b6e','#89b7a3':'#63b795',
    '#5e9c86':'#70e2af','#d3ad6a':'#f3c66f','#bd604c':'#e96e64',
    '#74483e':'#a86663','#374c45':'#4f7973'
  };
  const originals = new WeakMap();
  const originalOptions = new WeakMap();
  const same = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  function swap(color, dark) {
    if (!dark || typeof color !== 'string') return color;
    const normalized = color.toLowerCase();
    if (colorMap[normalized]) return colorMap[normalized];
    if (/^#[a-f0-9]{8}$/.test(normalized)) {
      const base = colorMap[normalized.slice(0,7)];
      return base ? base + normalized.slice(-2) : color;
    }
    if (normalized === '#fff' || normalized === '#ffffff') return '#0e2c2e';
    return color;
  }
  function datasetColors(dataset, dark) {
    let state = originals.get(dataset);
    const current = {borderColor:dataset.borderColor, backgroundColor:dataset.backgroundColor};
    if (!state || !same(current,state.displayed)) {
      state = {original:{...current},displayed:{...current}};
      originals.set(dataset,state);
    }
    for (const name of ['borderColor','backgroundColor']) {
      const source=state.original[name];
      if (source === undefined) continue;
      dataset[name] = Array.isArray(source) ? source.map(c=>swap(c,dark)) : swap(source,dark);
    }
    state.displayed={borderColor:dataset.borderColor,backgroundColor:dataset.backgroundColor};
  }
  function setTheme(chart) {
    const dark = document.documentElement.dataset.theme === 'dark';
    for (const dataset of chart.data?.datasets || []) datasetColors(dataset,dark);
    const opts = chart.options || {};
    let initial = originalOptions.get(chart);
    if (!initial) {
      const scaleOpts=opts.scales || {};
      initial = {
        ticks:Object.fromEntries(Object.entries(scaleOpts).map(([key,axis])=>[key,axis.ticks?.color])),
        grids:Object.fromEntries(Object.entries(scaleOpts).map(([key,axis])=>[key,axis.grid?.color])),
        legend:opts.plugins?.legend?.labels?.color,
        tooltipBackground:opts.plugins?.tooltip?.backgroundColor,
        tooltipTitle:opts.plugins?.tooltip?.titleColor,
        tooltipBody:opts.plugins?.tooltip?.bodyColor
      };
      originalOptions.set(chart,initial);
    }
    for (const [key,axis] of Object.entries(opts.scales || {})) {
      if (!axis.ticks) axis.ticks = {};
      axis.ticks.color = dark ? '#a6c5bd' : initial.ticks[key];
      if (!axis.grid) axis.grid = {};
      if (axis.grid.display !== false) axis.grid.color = dark ? 'rgba(138,202,184,.14)' : initial.grids[key];
      if (axis.border) axis.border.color = dark ? '#42645f' : undefined;
    }
    if (!opts.plugins) opts.plugins = {};
    if (!opts.plugins.legend) opts.plugins.legend = {};
    if (!opts.plugins.legend.labels) opts.plugins.legend.labels = {};
    opts.plugins.legend.labels.color = dark ? '#b4d5c9' : initial.legend;
    if (!opts.plugins.tooltip) opts.plugins.tooltip = {};
    opts.plugins.tooltip.backgroundColor = dark ? '#071e20' : initial.tooltipBackground;
    opts.plugins.tooltip.titleColor = dark ? '#f0fff7' : initial.tooltipTitle;
    opts.plugins.tooltip.bodyColor = dark ? '#d5ede3' : initial.tooltipBody;
  }
  Chart.register({id:'intelliwattsTheme',beforeUpdate:setTheme});
  document.addEventListener('iw-theme-change', () => {
    for (const chart of Object.values(Chart.instances || {})) chart.update('none');
  });
})();

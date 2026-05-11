# Critical Power Heatmap Design

> **Status:** APPROVED
> **Date:** 2026-05-11
> **Topic:** Dashboard Expansion - Critical Power Heatmap

## 1. Goal
Implement a "Critical Power Heatmap" dashboard widget that visualizes an athlete's power capabilities across durations (1s to 2h+). The goal is to identify "performance gaps" by comparing recent performance against seasonal and all-time benchmarks.

## 2. Requirements
- **Data Comparison:** Display three curves: Last 90 Days, Current Season, and All-Time.
- **Visualization:**
    - Line chart using Chart.js.
    - **Logarithmic X-axis** for the time scale (standard for power curves).
    - Watts on the Y-axis.
- **Interactivity:**
    - **Visual Gap Shading:** Shade the area between the 90d curve and the Season curve to highlight potential performance gaps.
    - **Rich Tooltips:** Show absolute values and the delta (watts/percentage) to benchmarks on hover.

## 3. Architecture & Implementation

### 3.1 Backend (Python)
- **File:** `app/planning/providers/power_curve.py`
- **Logic:**
    - Update `PowerCurveProvider.calculate` to fetch three curves from Intervals.icu: `90d`, `s0` (Season), and `all` (All-Time).
    - Update `PowerCurveResult` dataclass to hold the full point arrays (secs/watts) for these three curves.
    - Update `get_dashboard_widget` to return a `DashboardWidget` with `custom_template="power_curve_chart.html"` and the curve data in the `data` dict.

### 3.2 Frontend (HTML/JS)
- **File:** `app/templates/widgets/power_curve_chart.html`
- **Logic:**
    - Implement the Chart.js logic with `type: 'line'`.
    - Configure the X-axis with `type: 'logarithmic'`.
    - Implement custom tooltip callbacks to show gaps.
    - Use `fill: '-1'` or similar Chart.js plugins/features to shade gaps between datasets.

### 3.3 Data Sourcing
- Use `client.power_curves(curves="90d")`, `client.power_curves(curves="s0")`, and `client.power_curves(curves="all")`.

## 4. Testing
- **Unit Tests:** `tests/planning/providers/test_power_curve.py`
    - Mock `IntervalsClient.power_curves` to return sample JSON data.
    - Verify `PowerCurveProvider.calculate` correctly parses and aggregates all three curves.
- **Integration Tests:** `tests/routes/test_integration.py` (or similar)
    - Verify the dashboard endpoint renders with the `power_curve` widget present in the analysis results.

## 5. Success Criteria
- The dashboard displays a logarithmic line chart.
- Three distinct lines are visible (90d, Season, All-Time).
- Performance gaps are visually shaded.
- Hovering reveals precise gap metrics.

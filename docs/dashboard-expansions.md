# Dashboard Expansion Roadmap

This document outlines potential enhancements for the IntelliWatts dashboard, categorized by data availability and implementation complexity.

## 🟢 Category 1: Possible with Existing Data
These features can be implemented using the data already parsed from Intervals.icu (Activities, Wellness, Power Curves).

### 1. Interactive Intensity Distribution ✅
*   **Status:** COMPLETED
*   **Data:** `hr_zone_times` and `power_zone_times` from `ParsedActivity`.
*   **Visualization:** Interactive doughnut chart with toggle between HR and Power.
*   **Value:** Helps athletes verify if they are training at the intended intensity (e.g., following a 80/20 polarized model).

### 2. Longitudinal HRV & Resting HR Trends ✅
*   **Status:** COMPLETED
*   **Data:** `hrv` and `resting_hr` from `ParsedWellness`.
*   **Visualization:** A dual-axis line chart showing daily values with a 7-day rolling average overlay.
*   **Value:** Better visualization of recovery trends and detection of overtraining or illness.

### 3. Activity Type Analysis
*   **Data:** `type` and `duration_h` from `ParsedActivity`.
*   **Visualization:** A donut chart showing the breakdown of training volume by sport (Ride, Run, Swim, etc.).
*   **Value:** Quick overview of cross-training balance.

### 4. Critical Power "Heatmap"
*   **Data:** `ParsedPowerCurve` (Season vs. All-time or 90d).
*   **Visualization:** A line chart with shaded areas representing standard deviations or personal bests.
*   **Value:** Identifies specific duration gaps where the athlete's power is lagging.

---

## 🟡 Category 2: Requires Minor Logic/Parsing Updates
These require data that is likely available in the Intervals.icu API but not currently fully extracted or aggregated.

### 1. Weekly Volume Comparison
*   **Data:** Aggregated `duration_h` or `training_stress` grouped by week.
*   **Visualization:** Bar chart comparing current week vs. previous 4 weeks.
*   **Value:** Visualizes training progression and load management.

### 2. Performance Predicted vs. Actual
*   **Data:** Requires fetching "Planned" activities from Intervals.icu.
*   **Visualization:** Grouped bar chart (Planned vs. Completed).
*   **Value:** High-level compliance monitoring.

---

## 🔴 Category 3: Requires Additional Data Sources
These features require deeper integration or external data.

### 1. Sleep Quality vs. Training Load
*   **Data:** Deeper sleep metrics (Deep, REM) if available via wearables.
*   **Visualization:** Scatter plot with load on X-axis and sleep quality on Y-axis.
*   **Value:** Correlates how training intensity affects recovery quality.

### 2. Nutrition & Fueling Insights
*   **Data:** Integration with MyFitnessPal or similar.
*   **Visualization:** Caloric balance (Burned vs. Consumed).
*   **Value:** Critical for endurance athletes managing energy availability.

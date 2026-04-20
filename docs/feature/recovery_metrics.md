# Readiness & Recovery Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate HRV, Resting HR, and subjective wellness data from Intervals.icu into the training plan generation process to improve athlete readiness assessment.

**Architecture:** Extend the data fetching layer (IntervalsClient), add a wellness parsing module, update the analysis logic to compute 7-day and 42-day wellness trends, and incorporate these insights into the LLM coach prompt.

**Tech Stack:** Python, Requests, Polars, SQLModel.

---

### Task 1: Fetch and Parse Wellness Data

**Files:**
- Modify: `app/intervals/client.py`
- Create: `app/intervals/parser/wellness.py`
- Test: `tests/intervals/test_wellness.py`

- [x] **Step 1: Update `IntervalsClient` to fetch wellness data**
Add a `wellness(days: int)` method to `IntervalsClient` in `app/intervals/client.py`. Use the endpoint `GET /api/v1/athlete/{id}/wellness`. Implement caching similar to `activities()`.

- [x] **Step 2: Create `ParsedWellness` dataclass and parser**
Create `app/intervals/parser/wellness.py` with a `ParsedWellness` dataclass including `date`, `hrv`, `resting_hr`, `sleep_score`, `sleep_quality`, `fatigue`, `soreness`, `stress`, `readiness`, and `comments`.

- [x] **Step 3: Write tests for wellness fetching and parsing**
Create `tests/intervals/test_wellness.py` and verify that data is fetched and parsed correctly.

---

### Task 2: Compute Wellness Trends in Analysis

**Files:**
- Modify: `app/intervals/analysis.py`
- Test: `tests/intervals/test_analysis_wellness.py`

- [x] **Step 1: Update `AnalysisResult` and `compute_analysis`**
Modify `AnalysisResult` to include `wellness_summary`. Update `compute_analysis` to accept an optional `list[ParsedWellness]`.

- [x] **Step 2: Implement wellness aggregation logic**
In `compute_analysis`, use Polars to join wellness data with the daily series. Calculate 7-day and 42-day rolling averages for HRV and RHR to detect deviations.

- [x] **Step 3: Update `compute_load` to also return wellness trends**
Optionally refactor `compute_load` or create a new helper that aggregates both load and wellness status.

---

### Task 3: Update Planner Service and Summary

**Files:**
- Modify: `app/services/planner.py`
- Modify: `app/planning/summary.py`

- [ ] **Step 1: Update `generate_weekly_plan` to fetch wellness**
In `app/services/planner.py`, call `client.wellness()` and pass the parsed results to the analysis and summary builders.

- [ ] **Step 2: Update `build_weekly_summary` to include wellness**
In `app/planning/summary.py`, update the dictionary returned to include a `wellness` section with current values and trends (e.g., "HRV is 10% below 42-day baseline").

---

### Task 4: Enhance Coach Prompt with Readiness Insights

**Files:**
- Modify: `app/planning/coach_prompt.py`

- [ ] **Step 1: Update `SYSTEM_PROMPT`**
Update the instructions in `app/planning/coach_prompt.py` to include rules for wellness metrics. E.g., "If HRV is significantly below baseline, prioritize recovery sessions."

- [ ] **Step 2: Verify the final prompt structure**
Ensure the `summary` JSON passed to the prompt now contains the new wellness data.

---

## Sub-Prompts for Guidance

### Prompt 1: Data Acquisition
"Implement Task 1 of the Readiness & Recovery Metrics plan. Add a `wellness` method to `IntervalsClient` in `app/intervals/client.py` and create a parser in `app/intervals/parser/wellness.py`. Ensure caching is handled and write tests in `tests/intervals/test_wellness.py`."

### Prompt 2: Analysis & Trends
"Implement Task 2 of the Readiness & Recovery Metrics plan. Update `app/intervals/analysis.py` to process wellness data along with activities. Compute 7-day and 42-day rolling averages for HRV and Resting HR to identify trends. Add tests to verify these calculations."

### Prompt 3: Service Integration
"Implement Task 3 of the Readiness & Recovery Metrics plan. Update `app/services/planner.py` to fetch wellness data and `app/planning/summary.py` to include these metrics and trends in the summary sent to the LLM."

### Prompt 4: Prompt Engineering
"Implement Task 4 of the Readiness & Recovery Metrics plan. Update `app/planning/coach_prompt.py` to incorporate instructions for the LLM on how to interpret HRV, RHR, and subjective wellness data when generating the training plan."

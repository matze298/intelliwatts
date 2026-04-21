# Persistent Plan Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement persistent storage for training plans using a Phase/Iteration hierarchy to support dynamic updates and re-planning.

**Architecture:** Hybrid Relational + JSON. Use `TrainingPhase` as a long-term goal container and `TrainingPlan` for weekly iterations, storing the LLM response and structured workout data in JSON columns. Iterative updates will use the stored `prompt_history` (full conversation history) to provide context to the LLM.

**Tech Stack:** Python 3.14, SQLModel (SQLite), FastAPI.

---

### Task 1: Define Plan Models

**Files:**
- Create: `app/models/plan.py`
- Modify: `app/models/__init__.py`
- Modify: `app/main.py`
- Test: `tests/models/test_plan.py`

- [ ] **Step 1: Create the model file with structured JSON fields**
```python
import uuid
from datetime import date, datetime
from typing import Any
from sqlmodel import Field, SQLModel, Column, JSON

class TrainingPhase(SQLModel, table=True):
    """Macro container for a specific training objective."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    primary_goal: str
    start_date: date
    end_date: date
    status: str = Field(default="active")  # active, completed, archived

class TrainingPlan(SQLModel, table=True):
    """Micro execution level, storing the LLM-generated workouts."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phase_id: uuid.UUID = Field(foreign_key="trainingphase.id")
    week_start: date
    raw_content: str
    # workout_data: Structured JSON containing list of workouts, segments, and steps.
    # State-of-the-art: Store as a list of workout objects for easy iteration.
    workout_data: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    # prompt_history: The full conversation history for this iteration cycle.
    prompt_history: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **Step 2: Export models**
In `app/models/__init__.py`, export the new models.

- [ ] **Step 3: Ensure models are imported before init_db**
In `app/main.py`, add imports for `TrainingPhase` and `TrainingPlan`.

- [ ] **Step 4: Write comprehensive model tests**
Test PKs, FKs, and JSON serialization for `workout_data` and `prompt_history`.

- [ ] **Step 5: Run tests**
`docker compose -f sandbox/docker-compose.yml run sandbox pytest tests/models/test_plan.py`

- [ ] **Step 6: Commit**
`git add app/models/plan.py app/models/__init__.py app/main.py tests/models/test_plan.py && git commit -m "feat: add TrainingPhase and TrainingPlan models with structured JSON support"`

---

### Task 2: Implement PlannerService Storage Logic (Checkpoint)

**Files:**
- Modify: `app/services/planner.py`
- Modify: `app/planning/llm_to_icu.py` (Add JSON extraction helper)
- Test: `tests/services/test_planner_storage.py`

- [ ] **Step 1: Add JSON extraction utility to `llm_to_icu.py`**
Refactor `llm_json_to_icu_txt` to expose a `extract_workout_json(ai_response: str) -> list[dict]` function.

- [ ] **Step 2: Implement `get_or_create_active_phase` in `PlannerService`**
Include a `TODO` for future goal-based onboarding.

- [ ] **Step 3: Implement `save_training_plan` with Overwrite logic**
Ensure `updated_at` is refreshed on update.

- [ ] **Step 4: Update `generate_weekly_plan` signature and logic**
Accept an optional `prompt_history` to support iterations.
```python
def generate_weekly_plan(
    user: User, 
    settings: Settings = GLOBAL_SETTINGS, 
    *, 
    use_wellness: bool = True,
    feedback: str | None = None  # New for iterative updates
) -> dict[str, Any]:
    # ... logic to load active phase ...
    # ... logic to load existing plan for history if feedback is provided ...
    # ... call generate_plan with full history ...
    # ... extract JSON and save to DB ...
```

- [ ] **Step 5: Write thorough service tests**
Test: Default phase creation, plan overwriting, and JSON extraction failure cases.

- [ ] **Step 6: Commit**
`git add app/services/planner.py app/planning/llm_to_icu.py tests/services/test_planner_storage.py && git commit -m "feat: integrate plan storage and JSON extraction into PlannerService"`

---

### Task 3: Implement Iterative Updates

**Files:**
- Modify: `app/planning/llm.py`
- Modify: `app/services/planner.py`
- Create: `app/routes/api.py` (New endpoints)
- Test: `tests/services/test_iterations.py`

- [ ] **Step 1: Update `app/planning/llm.py` to handle message history**
Modify `generate_plan` to accept `messages: list[dict]` instead of just `summary`.

- [ ] **Step 2: Implement `update_training_plan` in `PlannerService`**
Logic: Load latest plan -> Append feedback to `prompt_history` -> Call LLM -> Save as new iteration (overwriting the week's current plan).

- [ ] **Step 3: Add `POST /api/plan/update` endpoint**
Accepts `{ "feedback": "string" }`.

- [ ] **Step 4: Write iteration tests**
Verify that the second LLM call receives the previous plan and the new feedback.

- [ ] **Step 5: Commit**
`git add app/planning/llm.py app/services/planner.py app/routes/api.py && git commit -m "feat: implement iterative plan updates using prompt history"`

---

### Task 4: Update Web Routes & UI

**Files:**
- Modify: `app/routes/web.py`
- Modify: `app/templates/dashboard.html`
- Modify: `app/templates/plan.html`

- [ ] **Step 1: Update Dashboard to load stored plan**
If an active plan exists for the current week, show it instead of a "Generate" button.

- [ ] **Step 2: Add "Adjust Plan" UI element**
A text input + button that calls the `/api/plan/update` endpoint.

- [ ] **Step 3: Verification**
Final check of the "Macro-to-Micro" flow.

- [ ] **Step 4: Commit**
`git commit -m "feat: update UI to support persistent and iterative plans"`

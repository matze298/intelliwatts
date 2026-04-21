# Design Spec: Persistent Plan Storage

**Date:** 2026-04-21
**Topic:** Persistent Plan Storage
**Status:** Approved
**Approach:** Hybrid Relational + JSON with Goal-Based Phases

## 1. Architecture

We will implement a hierarchical storage system to support long-term context (Macro-planning) and weekly actionable steps (Micro-planning).

### Data Models (SQLModel)

#### `TrainingPhase`
Acts as the "Macro" container for a specific training objective.
- `id`: `uuid.UUID` (PK)
- `user_id`: `uuid.UUID` (FK to User)
- `primary_goal`: `str` (e.g., "Build FTP", "Century Ride prep")
- `start_date`: `date`
- `end_date`: `date` (Determines the phase horizon)
- `status`: `str` (Enum: `active`, `completed`, `archived`)

#### `TrainingPlan`
The "Micro" execution level, storing the LLM-generated workouts.
- `id`: `uuid.UUID` (PK)
- `phase_id`: `uuid.UUID` (FK to TrainingPhase)
- `week_start`: `date` (Canonical start of the planning week, usually Monday)
- `raw_content`: `str` (The full LLM text response including markdown reasoning)
- `workout_data`: `dict` (JSON blob of the structured workout segments and steps)
- `prompt_history`: `list[dict]` (JSON list of message objects `{"role": "...", "content": "..."}`)
- `created_at`: `datetime`
- `updated_at`: `datetime`

## 2. Components & Data Flow

### `PlannerService` Enhancements
1. **`get_or_create_active_phase(user_id)`**:
   - Searches for a `TrainingPhase` with `status='active'`.
   - If missing, it will (for now) create a default 4-week phase but log a "TODO" to ask the user for goal input in the future.
2. **`save_plan(user_id, plan_data, prompt_history)`**:
   - Locates the active phase.
   - Upserts a `TrainingPlan` for the current `week_start`.
   - **Overwrite Strategy:** If a plan exists for that week, it is updated (Approach A).

### API / Web Routes
- **`GET /plan`**: Now first attempts to load the plan from the DB. If missing or "stale" (optional), it triggers generation.
- **`POST /plan/update`**: Accepts user feedback (e.g., "Make Thursday easier"), loads `prompt_history`, and sends a follow-up prompt to the LLM.

## 3. Error Handling
- **Missing Secrets:** Handled by existing `load_user_secrets` logic.
- **JSON Parsing Errors:** If the LLM returns malformed JSON, we store the `raw_content` but mark the `workout_data` as invalid/empty and alert the user.

## 4. Testing
- **Unit Tests**: Test the SQLModel definitions and relationships.
- **Integration Tests**: Verify the `PlannerService` correctly handles the Overwrite logic and retrieval of context.

## 5. Future Enhancements (to be added to improvement-plan.md)
- **Approach B (Revisions):** Implement versioning for `TrainingPlan` to track how iterations changed.
- **Approach C (Metric-based completion):** Automatically end a phase when a specific Intervals.icu metric (e.g., FTP) is reached.
- **Interactive Onboarding:** Ask the user for their specific goal and duration when starting a new phase.

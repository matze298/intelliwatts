/* In-place planner generation with actual FastAPI progress events. */
(() => {
  "use strict";
  let running = false;

  const id = (name) => document.getElementById(name);
  const text = (name, value) => {
    const element = id(name);
    if (element) element.textContent = value;
  };

  function stage(message) {
    const list = id("planner-progress-steps");
    if (!list) return;
    const previous = list.lastElementChild;
    if (previous) previous.classList.replace("planner-step-active", "planner-step-complete");
    const item = document.createElement("li");
    item.className = "planner-step-active";
    const time = document.createElement("time");
    time.textContent = new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
    const description = document.createElement("span");
    description.textContent = message;
    item.append(time, description);
    list.append(item);
  }

  function showProgress(form) {
    const panel = id("planner-progress");
    if (!panel) return;
    const list = id("planner-progress-steps");
    list.replaceChildren();
    const errorDetails = id("planner-error-details");
    if (errorDetails) {
      errorDetails.open = false;
      errorDetails.classList.add("hidden");
      text("planner-error-traceback", "");
    }
    panel.classList.remove("hidden", "planner-progress-error");
    panel.setAttribute("aria-busy", "true");
    text("planner-progress-title", form.id === "update-plan-form" ? "Updating training plan" : "Generating training plan");
    text("planner-progress-state", "Running");
    stage("Request accepted by IntelliWatts");
  }

  function finish(message, hasError = false) {
    const panel = id("planner-progress");
    if (!panel) return;
    panel.setAttribute("aria-busy", "false");
    panel.classList.toggle("planner-progress-error", hasError);
    const step = id("planner-progress-steps")?.lastElementChild;
    if (step) {
      step.classList.replace("planner-step-active", hasError ? "planner-step-failed" : "planner-step-complete");
    }
    text("planner-progress-state", message);
  }

  function showFailure(message, traceback) {
    const details = id("planner-error-details");
    if (details) {
      details.open = false;
      text("planner-error-message", message);
      text("planner-error-traceback", traceback || "No server traceback was provided. Check the server logs.");
      details.classList.remove("hidden");
    } else {
      stage(message);
    }
    finish("Failed — click the message for details", true);
  }

  function updateRenderedPlan(html, form) {
    const parsed = new DOMParser().parseFromString(html, "text/html");
    // Only swap the actual plan, status, action buttons and notices. Everything
    // else, including navigation and any unsaved goal settings, stays in place.
    for (const key of ["planner-current-status", "planner-action-buttons", "planner-alerts", "planner-plan-body"]) {
      const previous = id(key);
      const replacement = parsed.getElementById(key);
      if (!previous || !replacement) throw new Error("The response did not contain the updated plan.");
      previous.replaceWith(replacement);
    }
    const selectedWeek = form.elements.namedItem("week_start")?.value;
    if (selectedWeek) {
      const url = new URL(window.location.href);
      url.searchParams.set("week_start", selectedWeek);
      window.history.replaceState({}, "", url);
    }
    const validationError = id("planner-alerts")?.querySelector("[data-planner-error]");
    if (validationError) {
      finish("Review the validation message above", true);
      validationError.scrollIntoView({behavior: "smooth", block: "nearest"});
    } else {
      finish("Saved — review your updated plan");
      const heading = id("planner-plan-body")?.querySelector("h2");
      heading?.scrollIntoView({behavior: "smooth", block: "nearest"});
    }
  }

  function formPayload(form) {
    const payload = new FormData(form);
    if (form.id === "update-plan-form") {
      // The update form owns the feedback field; controls belong to Generate.
      // Include the current settings when preparing either API or manual updates.
      for (const key of ["max_hours", "max_sessions", "language_model"]) {
        const control = id(key);
        if (control) payload.set(key, control.value);
      }
      payload.set("available_days_present", "1");
      for (const selected of document.querySelectorAll('input[name="available_days"]:checked')) {
        payload.append("available_days", selected.value);
      }
    }
    return payload;
  }

  function submitManual(form) {
    // POST rather than placing athlete context or revision feedback in a URL.
    const payload = formPayload(form);
    const navigation = document.createElement("form");
    navigation.method = "post";
    navigation.action = "/manual-plan/prepare";
    navigation.hidden = true;
    for (const [name, value] of payload.entries()) {
      const field = document.createElement("input");
      field.type = "hidden";
      field.name = name;
      field.value = value;
      navigation.append(field);
    }
    document.body.append(navigation);
    navigation.submit();
  }

  async function run(form) {
    const panel = id("planner-progress");
    if (!panel) return;
    running = true;
    showProgress(form);
    const controls = [...document.querySelectorAll(
      'button[form="generate-plan-form"], button[form="update-plan-form"], button[form="publish-workout-form"]'
    )];
    for (const control of controls) {
      control.disabled = true;
      control.setAttribute("aria-busy", "true");
    }
    let completed = false;
    try {
      const payload = formPayload(form);
      const response = await fetch(form.action.replace(/\/$/, "") + "/stream", {
        method: "POST",
        body: payload,
        credentials: "same-origin",
        headers: {"Accept": "text/event-stream"},
      });
      if (response.redirected && new URL(response.url).pathname === "/login") {
        window.location.assign(response.url);
        return;
      }
      if (!response.ok || !response.body || !(response.headers.get("content-type") || "").includes("text/event-stream")) {
        throw new Error("The progress connection could not be established. Check the current plan before retrying.");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const {value, done} = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), {stream: !done}).replace(/\r\n/g, "\n");
        let end = buffer.indexOf("\n\n");
        while (end !== -1) {
          const frame = buffer.slice(0, end);
          buffer = buffer.slice(end + 2);
          const data = frame.split("\n").filter(line => line.startsWith("data: ")).map(line => line.slice(6)).join("\n");
          if (data) {
            const event = JSON.parse(data);
            if (event.kind === "stage") {
              stage(event.message);
            } else if (event.kind === "heartbeat") {
              text("planner-progress-state", "Connected · processing");
            } else if (event.kind === "error") {
              const failure = new Error(event.message || "Training-plan generation failed.");
              failure.traceback = typeof event.traceback === "string" ? event.traceback : "";
              throw failure;
            } else if (event.kind === "complete") {
              updateRenderedPlan(event.html, form);
              completed = true;
            }
          }
          end = buffer.indexOf("\n\n");
        }
        if (done) break;
      }
      if (!completed) throw new Error("The progress connection ended without a completed plan. Refresh to check whether it was saved.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not update the plan.";
      const traceback = error?.traceback || (error instanceof Error ? error.stack : "");
      showFailure(message, traceback);
    } finally {
      running = false;
      for (const control of controls) {
        control.disabled = false;
        control.removeAttribute("aria-busy");
      }
    }
  }

  document.addEventListener("submit", event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.matches('form[data-live-progress="true"]')) return;
    event.preventDefault();
    if (running) return;
    if (id("language_model")?.value === "manual") {
      submitManual(form);
      return;
    }
    if (typeof window.fetch !== "function" || !window.ReadableStream || !window.TextDecoder) {
      form.submit();
      return;
    }
    void run(form);
  });
})();
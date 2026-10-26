/**
 * eCourts Intelligence - Interactive Web Dashboard
 */

document.addEventListener("DOMContentLoaded", () => {
  const cnrInput = document.getElementById("cnrInput");
  const charCounter = document.getElementById("charCounter");
  const searchBtn = document.getElementById("searchBtn");
  const progressCard = document.getElementById("progressCard");
  const stepperList = document.getElementById("stepperList");
  const resultsContainer = document.getElementById("resultsContainer");

  let currentCaseData = null;
  let eventSource = null;

  // 1. CNR Input validation & formatting
  cnrInput.addEventListener("input", (e) => {
    // Only alphanumeric, uppercase
    let val = e.target.value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase();
    if (val.length > 16) val = val.substring(0, 16);
    e.target.value = val;

    charCounter.textContent = `${val.length}/16`;
    if (val.length === 16) {
      charCounter.classList.add("valid");
    } else {
      charCounter.classList.remove("valid");
    }
  });

  // 2. Search Form Submit
  document.getElementById("searchForm").addEventListener("submit", (e) => {
    e.preventDefault();
    if (searchBtn.disabled) return;
    const cnr = cnrInput.value.trim().toUpperCase();
    if (cnr.length !== 16) {
      showToast("Please enter a valid 16-character CNR number.", "error");
      cnrInput.focus();
      return;
    }
    startSearch(cnr);
  });

  // 3. Start Search with Server-Sent Events (SSE)
  function startSearch(cnr) {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }

    // Reset UI state
    resultsContainer.style.display = "none";
    progressCard.style.display = "block";
    stepperList.innerHTML = "";
    searchBtn.disabled = true;

    // Initial Stepper step
    addStep("init", "Connecting to eCourts India Gateway...", "active");

    const sseUrl = `/api/search/stream?cnr=${encodeURIComponent(cnr)}`;
    eventSource = new EventSource(sseUrl);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === "progress") {
          handleProgress(payload.step, payload.message);
        } else if (payload.type === "complete") {
          markAllDone();
          currentCaseData = payload.data;
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          setTimeout(() => {
            progressCard.style.display = "none";
            renderCaseResults(payload.data);
            searchBtn.disabled = false;
          }, 300);
        } else if (payload.type === "not_found") {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          addStep("error", payload.error || "Case with this CNR does not exist.", "retry");
          showToast(payload.error || "CNR does not exist.", "error");
          searchBtn.disabled = false;
        } else if (payload.type === "error") {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          addStep("error", payload.error || "Scraping failed.", "retry");
          showToast(payload.error || "Scraping failed.", "error");
          searchBtn.disabled = false;
        }
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.warn("SSE error / closed:", err);
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      searchBtn.disabled = false;
    };
  }

  function handleProgress(step, message) {
    const activeItem = stepperList.querySelector(".stepper-item.active");
    if (activeItem) {
      activeItem.classList.remove("active");
      activeItem.classList.add("done");
      activeItem.querySelector(".stepper-icon").innerHTML = "&#10003;";
    }

    let status = "active";
    if (step === "captcha_retry") {
      status = "retry";
    }

    addStep(step, message, status);
  }

  function addStep(id, text, status = "active") {
    const li = document.createElement("li");
    li.className = `stepper-item ${status}`;

    let iconHtml = "&#9679;";
    if (status === "done") iconHtml = "&#10003;";
    if (status === "retry") iconHtml = "&#8635;";

    li.innerHTML = `
      <span class="stepper-icon">${iconHtml}</span>
      <span class="stepper-text">${escapeHtml(text)}</span>
    `;
    stepperList.appendChild(li);
    li.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function markAllDone() {
    stepperList.querySelectorAll(".stepper-item").forEach((el) => {
      el.classList.remove("active", "retry");
      el.classList.add("done");
      el.querySelector(".stepper-icon").innerHTML = "&#10003;";
    });
  }

  // 4. Render Case Results
  function renderCaseResults(data) {
    resultsContainer.style.display = "block";

    // Overview Header
    document.getElementById("resCourtName").textContent = data.court_name || "District / Taluka Court";
    document.getElementById("resCnrPill").textContent = data.cnr || "";

    const details = data.case_details || {};
    const status = data.case_status || {};

    document.getElementById("resCaseType").textContent = details.case_type || "N/A";
    document.getElementById("resFilingNo").textContent = details.filing_number || "N/A";
    document.getElementById("resStage").textContent = status.case_stage || "N/A";
    document.getElementById("resNextDate").textContent = status.next_hearing_date || "N/A";

    // Tab 1: Case Details Grid
    const detailsGrid = document.getElementById("detailsGrid");
    detailsGrid.innerHTML = "";
    const detailFields = [
      { label: "Case Type", val: details.case_type },
      { label: "Filing Number", val: details.filing_number },
      { label: "Filing Date", val: details.filing_date },
      { label: "Registration Number", val: details.registration_number },
      { label: "Registration Date", val: details.registration_date },
      { label: "CNR Number", val: details.cnr_number },
      { label: "e-Filing Number", val: details.e_filing_number },
      { label: "e-Filing Date", val: details.e_filing_date },
      { label: "Court Number & Judge", val: status.court_number_and_judge },
      { label: "First Hearing Date", val: status.first_hearing_date },
      { label: "Next Hearing Date", val: status.next_hearing_date },
      { label: "Case Stage", val: status.case_stage },
    ];

    detailFields.forEach((item) => {
      if (item.val) {
        detailsGrid.innerHTML += `
          <div class="data-card">
            <div class="data-card-title">${escapeHtml(item.label)}</div>
            <div class="data-card-value">${escapeHtml(item.val)}</div>
          </div>
        `;
      }
    });

    // Tab 2: Parties
    const petList = document.getElementById("petitionersList");
    petList.innerHTML = "";
    (data.petitioners || []).forEach((p) => {
      petList.innerHTML += `
        <div class="party-list-item">
          <div class="party-name">${escapeHtml(p.name)}</div>
          <div class="party-counsel">
            <span>Advocate:</span> 
            <span class="counsel-pill">${escapeHtml(p.advocate || "None Mentioned")}</span>
          </div>
        </div>
      `;
    });

    const respList = document.getElementById("respondentsList");
    respList.innerHTML = "";
    (data.respondents || []).forEach((r) => {
      respList.innerHTML += `
        <div class="party-list-item">
          <div class="party-name">${escapeHtml(r.name)}</div>
          <div class="party-counsel">
            <span>Advocate:</span> 
            <span class="counsel-pill">${escapeHtml(r.advocate || "None Mentioned")}</span>
          </div>
        </div>
      `;
    });

    // Tab 3: Timeline
    const timelineEl = document.getElementById("hearingTimeline");
    timelineEl.innerHTML = "";
    (data.case_history || []).forEach((h) => {
      timelineEl.innerHTML += `
        <div class="timeline-item">
          <div class="timeline-node"><div class="timeline-node-inner"></div></div>
          <div class="timeline-card">
            <div class="timeline-dates">
              <span class="badge-hearing-date">Hearing: ${escapeHtml(h.hearing_date)}</span>
              <span class="badge-purpose">${escapeHtml(h.purpose_of_hearing)}</span>
              <span class="timeline-judge">Business Date: <strong>${escapeHtml(h.business_on_date)}</strong></span>
            </div>
            <div class="timeline-judge">Presiding: ${escapeHtml(h.judge)}</div>
          </div>
        </div>
      `;
    });

    // Tab 4: Acts Table
    const actsBody = document.getElementById("actsTableBody");
    actsBody.innerHTML = "";
    (data.acts || []).forEach((a) => {
      actsBody.innerHTML += `
        <tr>
          <td><strong>${escapeHtml(a.under_act)}</strong></td>
          <td>${escapeHtml(a.under_section)}</td>
        </tr>
      `;
    });

    // Tab 5: Processes Table
    const procBody = document.getElementById("processesTableBody");
    procBody.innerHTML = "";
    (data.processes || []).forEach((pr) => {
      procBody.innerHTML += `
        <tr>
          <td><code style="color:#f59e0b;font-family:var(--font-mono);">${escapeHtml(pr.process_id)}</code></td>
          <td>${escapeHtml(pr.process_title)}</td>
          <td>${escapeHtml(pr.process_date)}</td>
        </tr>
      `;
    });

    // Tab 6: IA Status
    const iaBody = document.getElementById("iaTableBody");
    iaBody.innerHTML = "";
    (data.ia_status || []).forEach((ia) => {
      iaBody.innerHTML += `
        <tr>
          <td><strong style="color:#6366f1;">${escapeHtml(ia.ia_number)}</strong></td>
          <td>${escapeHtml(ia.party_name)}</td>
          <td>${escapeHtml(ia.filing_date)}</td>
          <td>${escapeHtml(ia.next_date)} ${ia.purpose ? `<br/><small style="color:#a5b4fc">(${escapeHtml(ia.purpose)})</small>` : ""}</td>
          <td><span style="color:#10b981;font-weight:600;">${escapeHtml(ia.status)}</span></td>
        </tr>
      `;
    });

    // Tab 7: JSON code
    document.getElementById("jsonCodeBlock").textContent = JSON.stringify(data, null, 2);

    // Update Tab Badges
    document.getElementById("badgeHistoryCount").textContent = (data.case_history || []).length;
    document.getElementById("badgeProcessesCount").textContent = (data.processes || []).length;
    document.getElementById("badgeIaCount").textContent = (data.ia_status || []).length;

    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // 5. Tabs Switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    });
  });

  // 6. Copy CNR Button
  document.getElementById("btnCopyCnr").addEventListener("click", () => {
    if (currentCaseData && currentCaseData.cnr) {
      navigator.clipboard.writeText(currentCaseData.cnr);
      showToast("CNR Number copied to clipboard!", "success");
    }
  });

  // 7. Copy JSON & Download JSON Buttons
  document.getElementById("btnCopyJson").addEventListener("click", () => {
    if (currentCaseData) {
      navigator.clipboard.writeText(JSON.stringify(currentCaseData, null, 2));
      showToast("Full case JSON copied to clipboard!", "success");
    }
  });

  document.getElementById("btnDownloadJson").addEventListener("click", () => {
    if (currentCaseData) {
      const blob = new Blob([JSON.stringify(currentCaseData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ecourts_${currentCaseData.cnr || "case"}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded case JSON successfully!", "success");
    }
  });

  // Helper Toast
  function showToast(msg, type = "info") {
    const box = document.getElementById("toastBox");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.style.borderColor = type === "error" ? "var(--accent-rose)" : type === "success" ? "var(--accent-emerald)" : "var(--accent-primary)";
    toast.innerHTML = `
      <span style="color:${type === "error" ? "#f43f5e" : type === "success" ? "#34d399" : "#818cf8"}">&#9679;</span>
      <span>${escapeHtml(msg)}</span>
    `;
    box.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

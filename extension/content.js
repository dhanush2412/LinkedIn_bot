// JobHunt content script for LinkedIn Easy Apply.
// Detects the Easy Apply modal, injects a "Tailor & Fill" button,
// scrapes job + form data, calls the local jobhunt server, fills the form.
// It NEVER clicks Submit — a human always reviews and submits.

const API_BASE = "http://127.0.0.1:7860";

function toast(msg, ms = 4500) {
  let el = document.getElementById("jobhunt-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "jobhunt-toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.display = "block";
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.style.display = "none"), ms);
}

function findEasyApplyModal() {
  return document.querySelector(
    "div.jobs-easy-apply-modal, div[role='dialog'][aria-labelledby*='easy-apply'], div[data-test-modal][role='dialog']"
  );
}

function scrapeJobMeta() {
  const titleEl = document.querySelector(
    ".job-details-jobs-unified-top-card__job-title, h1.t-24, .jobs-unified-top-card__job-title"
  );
  const companyEl = document.querySelector(
    ".job-details-jobs-unified-top-card__company-name, .job-details-jobs-unified-top-card__primary-description a, .jobs-unified-top-card__company-name"
  );
  const locationEl = document.querySelector(
    ".job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet"
  );
  const jdEl = document.querySelector(
    "#job-details, .jobs-description__content .jobs-box__html-content, .jobs-description-content__text"
  );
  return {
    job_url: location.href,
    job_title: titleEl ? titleEl.innerText.trim() : "",
    company: companyEl ? companyEl.innerText.trim() : "",
    location: locationEl ? locationEl.innerText.trim() : "",
    jd_text: jdEl ? jdEl.innerText.trim() : "",
  };
}

function readFormFields(modal) {
  const fields = [];
  modal.querySelectorAll("input, textarea, select").forEach((el) => {
    if (el.type === "hidden" || el.type === "file") return;
    const labelEl =
      (el.id && modal.querySelector(`label[for='${el.id}']`)) ||
      el.closest("label") ||
      el.closest(
        ".artdeco-text-input, .fb-dash-form-element, [data-test-form-element]"
      )?.querySelector("label, .artdeco-text-input--label");
    const label = labelEl
      ? labelEl.innerText.trim()
      : el.getAttribute("aria-label") || el.name || "";
    fields.push({
      label,
      el,
      type: el.tagName.toLowerCase(),
      inputType: el.type || "",
    });
  });
  return fields;
}

function setReactValue(el, value) {
  const proto =
    el.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
  setter.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillField(field, value) {
  if (value === "NEEDS_HUMAN" || value == null || value === "") return false;
  if (field.type === "select") {
    const opt = Array.from(field.el.options).find((o) =>
      o.text.toLowerCase().includes(String(value).toLowerCase())
    );
    if (opt) {
      field.el.value = opt.value;
      field.el.dispatchEvent(new Event("change", { bubbles: true }));
      field.el.classList.add("jobhunt-ai-filled");
      return true;
    }
    return false;
  }
  setReactValue(field.el, String(value));
  field.el.classList.add("jobhunt-ai-filled");
  return true;
}

function matchProfileValue(label, profile) {
  const l = label.toLowerCase();
  if (/email/i.test(l)) return profile.email;
  if (/phone|mobile/i.test(l)) return profile.phone;
  if (/first\s*name/i.test(l)) return profile.name ? profile.name.split(" ")[0] : "";
  if (/last\s*name/i.test(l))
    return profile.name ? profile.name.split(" ").slice(1).join(" ") : "";
  if (/^name$|full\s*name/i.test(l)) return profile.name;
  if (/city|location/i.test(l)) return profile.location;
  if (/years.*experience|experience.*years/i.test(l))
    return profile.total_years_experience
      ? String(profile.total_years_experience)
      : "";
  return null;
}

function resetBtn() {
  const btn = document.getElementById("jobhunt-fill-btn");
  if (btn) {
    btn.disabled = false;
    btn.textContent = "🎯 Tailor & Fill";
  }
}

async function tailorAndFill() {
  const btn = document.getElementById("jobhunt-fill-btn");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Tailoring...";
  }

  const modal = findEasyApplyModal();
  if (!modal) {
    toast("No Easy Apply modal found. Click 'Easy Apply' first.");
    resetBtn();
    return;
  }

  const meta = scrapeJobMeta();
  const fields = readFormFields(modal);
  const formQuestions = fields
    .filter((f) => f.inputType !== "radio" && f.inputType !== "checkbox")
    .map((f) => f.label)
    .filter((l) => l && l.length > 2);

  // Fetch the candidate's basic contact fields for standard autofill.
  let profile = { name: "", email: "", phone: "", location: "", total_years_experience: 0 };
  try {
    const pr = await fetch(`${API_BASE}/profile`);
    if (pr.ok) profile = await pr.json();
  } catch (e) {
    // server offline is handled by the /tailor fetch below
  }

  let resp;
  try {
    resp = await fetch(`${API_BASE}/tailor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...meta, form_questions: formQuestions }),
    });
  } catch (e) {
    toast("Server offline. Start it with:  python -m jobhunt serve");
    resetBtn();
    return;
  }
  if (!resp.ok) {
    let detail = resp.status;
    try {
      detail = (await resp.json()).detail || resp.status;
    } catch (e) {}
    toast(`Server error: ${detail}. Standard fields still filled.`);
    // fall through: still try profile-based autofill below
  }

  let data = { form_answers: {}, cover_letter: "", resume_pdf_url: "", job_id: "" };
  if (resp.ok) data = await resp.json();

  let filled = 0;
  for (const f of fields) {
    if (!f.label) continue;
    const profileVal = matchProfileValue(f.label, profile);
    if (profileVal) {
      if (fillField(f, profileVal)) filled++;
      continue;
    }
    const aiAnswer = data.form_answers && data.form_answers[f.label];
    if (aiAnswer && aiAnswer !== "NEEDS_HUMAN") {
      if (fillField(f, aiAnswer)) filled++;
    }
  }

  if (resp.ok) {
    chrome.runtime.sendMessage({
      type: "openSidePanel",
      payload: {
        job_id: data.job_id,
        cover_letter: data.cover_letter,
        resume_pdf_url: `${API_BASE}${data.resume_pdf_url}`,
        form_answers: data.form_answers,
      },
    });
  }

  toast(
    `Filled ${filled} field(s). Review yellow-highlighted answers, then click Submit yourself.`
  );
  resetBtn();
}

function injectButton() {
  if (document.getElementById("jobhunt-fill-btn")) return;
  if (!findEasyApplyModal()) return;
  const btn = document.createElement("button");
  btn.id = "jobhunt-fill-btn";
  btn.textContent = "🎯 Tailor & Fill";
  btn.addEventListener("click", tailorAndFill);
  document.body.appendChild(btn);
}

function removeButtonIfModalGone() {
  if (!findEasyApplyModal()) {
    const btn = document.getElementById("jobhunt-fill-btn");
    if (btn) btn.remove();
  }
}

const observer = new MutationObserver(() => {
  injectButton();
  removeButtonIfModalGone();
});
observer.observe(document.body, { childList: true, subtree: true });

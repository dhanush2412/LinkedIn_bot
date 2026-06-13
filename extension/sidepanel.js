function render(data) {
  if (!data) return;
  document.getElementById("cl").textContent = data.cover_letter || "(none)";
  const pdfLink = document.getElementById("pdf");
  if (data.resume_pdf_url) {
    pdfLink.href = data.resume_pdf_url;
    pdfLink.style.display = "inline-block";
  }
  const ans = document.getElementById("answers");
  ans.innerHTML = "";
  Object.entries(data.form_answers || {}).forEach(([q, a]) => {
    const div = document.createElement("div");
    div.className = "qa";
    const isHuman = a === "NEEDS_HUMAN";
    const qDiv = document.createElement("div");
    qDiv.className = "q";
    qDiv.textContent = q;
    const aDiv = document.createElement("div");
    if (isHuman) {
      aDiv.className = "needs-human";
      aDiv.textContent = "⚠ Needs human review";
    } else {
      aDiv.textContent = a;
    }
    div.appendChild(qDiv);
    div.appendChild(aDiv);
    ans.appendChild(div);
  });
}

chrome.storage.local.get(["lastTailored"], (res) => render(res.lastTailored));
chrome.storage.onChanged.addListener((changes) => {
  if (changes.lastTailored) render(changes.lastTailored.newValue);
});

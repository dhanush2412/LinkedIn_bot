fetch("http://127.0.0.1:7860/health")
  .then((r) => r.json())
  .then((j) => {
    const s = document.getElementById("status");
    if (j.status === "ok") {
      s.className = "status ok";
      s.textContent = "Local server: OK";
    } else {
      s.className = "status bad";
      s.textContent = "Server returned unexpected response";
    }
  })
  .catch(() => {
    const s = document.getElementById("status");
    s.className = "status bad";
    s.textContent = "Server offline. Run: python -m jobhunt serve";
  });

document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const label = input.closest(".file-picker")?.querySelector("span");
    if (label) {
      label.textContent = input.files?.[0]?.name || "Choose a file";
    }
  });
});

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

document.querySelectorAll("[data-row-href]").forEach((row) => {
  const open = () => {
    window.location.href = row.dataset.rowHref;
  };
  row.addEventListener("click", (event) => {
    if (!event.target.closest("a, button, input, select")) {
      open();
    }
  });
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      open();
    }
  });
});

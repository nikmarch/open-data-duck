const state = {
  recipes: [],
  selectedId: "",
};

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function findRecipe(id) {
  return state.recipes.find((recipe) => recipe.id === id);
}

function renderOutput(recipe) {
  const terminalCommand = document.querySelector("[data-terminal-command]");
  const terminalOutput = document.querySelector("[data-terminal-output]");
  const resultBody = document.querySelector("[data-result-body]");
  const statusLine = document.querySelector("[data-status-line]");

  if (!recipe) {
    terminalCommand.textContent = "$ odd sql <allowlisted-source-id>";
    terminalOutput.textContent = "Source not found. Pick one of the allowlisted examples.";
    resultBody.innerHTML = '<tr><td colspan="3">No source selected.</td></tr>';
    statusLine.textContent = "Error: unknown preset.";
    return;
  }

  terminalCommand.textContent = `$ ${recipe.command}`;
  terminalOutput.textContent = recipe.sql;
  resultBody.innerHTML = `
    <tr><th scope="row">Source</th><td>${escapeHtml(recipe.id)}</td><td>${escapeHtml(recipe.title)}</td></tr>
    <tr><th scope="row">Type</th><td>${escapeHtml(recipe.source_type)}</td><td>${escapeHtml(recipe.status)}</td></tr>
    <tr><th scope="row">Fields</th><td colspan="2">${escapeHtml(recipe.fields.join(", "))}</td></tr>
    <tr><th scope="row">Result</th><td colspan="2">${escapeHtml(recipe.result_note)}</td></tr>
  `;
  statusLine.textContent = `Ready: ${recipe.description}`;
}

function selectRecipe(id) {
  state.selectedId = id;
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.example === id));
  });
  renderOutput(findRecipe(id));
}

async function bootTerminal() {
  const statusLine = document.querySelector("[data-status-line]");
  try {
    const response = await fetch("demo-recipes.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    state.recipes = payload.examples || [];
    document.querySelector("[data-architecture-note]").textContent = payload.architecture.copy;
    document.querySelectorAll("[data-example]").forEach((button) => {
      button.addEventListener("click", () => selectRecipe(button.dataset.example));
    });
    selectRecipe(state.recipes[0]?.id || "");
  } catch (error) {
    statusLine.textContent = `Error loading demo recipes: ${error.message}`;
    renderOutput(null);
  }
}

document.addEventListener("DOMContentLoaded", bootTerminal);

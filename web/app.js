const state = {
  files: [],
  records: [],
  current: 0,
  objectUrls: [],
};

const fileInput = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const extractButton = document.querySelector("#extract-button");
const selectionStatus = document.querySelector("#selection-status");
const errorBox = document.querySelector("#error-box");
const workspace = document.querySelector("#workspace");
const form = document.querySelector("#invoice-form");
const confirmed = document.querySelector("#confirmed");

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function setFiles(files) {
  clearError();
  const pdfs = Array.from(files).filter(
    (file) => [".pdf", ".jpg", ".jpeg", ".png"].some((suffix) =>
      file.name.toLowerCase().endsWith(suffix),
    ),
  );
  state.files = pdfs;
  selectionStatus.textContent = pdfs.length
    ? `Выбрано файлов: ${pdfs.length}`
    : "Файлы не выбраны";
  extractButton.disabled = pdfs.length === 0;
}

fileInput.addEventListener("change", () => setFiles(fileInput.files));

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
}
dropZone.addEventListener("drop", (event) => setFiles(event.dataTransfer.files));

function getNested(object, path) {
  return path.split(".").reduce((current, key) => current?.[key], object);
}

function setNested(object, path, value) {
  const keys = path.split(".");
  const finalKey = keys.pop();
  let current = object;
  for (const key of keys) {
    if (!current[key]) current[key] = {};
    current = current[key];
  }
  current[finalKey] = value;
}

function saveCurrentRecord() {
  const record = state.records[state.current];
  if (!record) return;
  for (const input of form.querySelectorAll("input[name]")) {
    let value = input.value.trim();
    if (input.type === "number") value = value === "" ? null : Number(value);
    else value = value || null;
    setNested(record, input.name, value);
  }
  record.items = Array.from(document.querySelectorAll("#items-body tr")).map((row, index) => ({
    line_number: index + 1,
    name: row.querySelector('[data-field="name"]').value.trim(),
    unit: row.querySelector('[data-field="unit"]').value.trim() || null,
    quantity: numberOrNull(row.querySelector('[data-field="quantity"]').value),
    unit_price: numberOrNull(row.querySelector('[data-field="unit_price"]').value),
    line_total: numberOrNull(row.querySelector('[data-field="line_total"]').value),
  }));
  record.reviewed = confirmed.checked;
}

function numberOrNull(value) {
  const trimmed = String(value).trim();
  return trimmed === "" ? null : Number(trimmed);
}

function innIsValid(value) {
  if (!/^\d{10}(\d{2})?$/.test(value || "")) return false;
  const digits = Array.from(value, Number);
  const checksum = (weights) => weights.reduce((sum, weight, index) => sum + weight * digits[index], 0) % 11 % 10;
  if (digits.length === 10) {
    return checksum([2, 4, 10, 3, 5, 9, 4, 6, 8]) === digits[9];
  }
  return checksum([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === digits[10]
    && checksum([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) === digits[11];
}

function validateRecord(record) {
  const issues = [];
  const add = (field, message) => issues.push({ field, message });
  const required = [
    ["invoice_number", "Не указан номер счёта"],
    ["invoice_date", "Не указана дата счёта"],
    ["supplier.name", "Не указано название поставщика"],
    ["supplier.inn", "Не указан ИНН поставщика"],
    ["total_amount", "Не указана итоговая сумма"],
  ];
  for (const [field, message] of required) {
    if (getNested(record, field) == null || getNested(record, field) === "") add(field, message);
  }

  for (const partyName of ["supplier", "buyer"]) {
    const party = record[partyName];
    if (!party) continue;
    const label = partyName === "supplier" ? "поставщика" : "покупателя";
    if (party.inn && !innIsValid(party.inn)) add(`${partyName}.inn`, `ИНН ${label} не прошёл проверку контрольной суммы`);
    if (party.kpp && !/^\d{9}$/.test(party.kpp)) add(`${partyName}.kpp`, `КПП ${label} должен содержать 9 цифр`);
    if (partyName === "supplier" && party.bik && !/^\d{9}$/.test(party.bik)) add("supplier.bik", "БИК должен содержать 9 цифр");
    if (partyName === "supplier" && party.bank_account && !/^\d{20}$/.test(party.bank_account)) add("supplier.bank_account", "Расчётный счёт должен содержать 20 цифр");
  }

  if ([record.subtotal_amount, record.vat_amount, record.total_amount].every((value) => value != null)
      && Math.abs(record.subtotal_amount + record.vat_amount - record.total_amount) > 0.01) {
    add("total_amount", "Сумма без НДС + НДС не равна итогу");
  }

  let itemSum = 0;
  (record.items || []).forEach((item, index) => {
    if (!item.name) add(`items.${index}.name`, `Позиция ${index + 1}: не указано наименование`);
    if (item.quantity == null || item.quantity <= 0) add(`items.${index}.quantity`, `Позиция ${index + 1}: количество должно быть больше нуля`);
    if (item.unit_price == null || item.unit_price < 0) add(`items.${index}.unit_price`, `Позиция ${index + 1}: некорректная цена`);
    if (item.line_total == null || item.line_total < 0) add(`items.${index}.line_total`, `Позиция ${index + 1}: некорректная сумма`);
    if ([item.quantity, item.unit_price, item.line_total].every((value) => value != null)
        && Math.abs(item.quantity * item.unit_price - item.line_total) > 0.01) {
      add(`items.${index}.line_total`, `Позиция ${index + 1}: количество × цена не равно сумме`);
    }
    if (item.line_total != null) itemSum += item.line_total;
  });
  if (record.items?.length && record.subtotal_amount != null && Math.abs(itemSum - record.subtotal_amount) > 0.01) {
    add("subtotal_amount", "Сумма товарных позиций не равна сумме без НДС");
  }
  return issues;
}

function inputForField(field) {
  if (!field.startsWith("items.")) return form.querySelector(`[name="${field}"]`);
  const [, index, itemField] = field.split(".");
  return document.querySelectorAll("#items-body tr")[Number(index)]?.querySelector(`[data-field="${itemField}"]`);
}

function updateValidation() {
  const record = state.records[state.current];
  if (!record) return;
  saveCurrentRecord();
  form.querySelectorAll("input").forEach((input) => {
    input.classList.remove("field-invalid", "field-uncertain");
    input.removeAttribute("title");
  });
  const issues = validateRecord(record);
  for (const issue of issues) {
    const input = inputForField(issue.field);
    if (input) {
      input.classList.add("field-invalid");
      input.title = issue.message;
    }
  }
  for (const [field, confidence] of Object.entries(record.confidence || {})) {
    if (confidence < 0.8) inputForField(field)?.classList.add("field-uncertain");
  }
  const summary = document.querySelector("#validation-summary");
  if (issues.length) {
    summary.innerHTML = `<strong>Найдены ошибки проверки</strong><ul>${issues.map((issue) => `<li>${escapeHtml(issue.message)}</li>`).join("")}</ul>`;
    summary.hidden = false;
  } else {
    summary.hidden = true;
    summary.innerHTML = "";
  }
  record.validationIssueCount = issues.length;
  record.reviewed = confirmed.checked;
  updateReviewStatus();
}

function renderItems(items) {
  const body = document.querySelector("#items-body");
  body.innerHTML = "";
  for (const item of items || []) addItemRow(item);
}

function addItemRow(item = {}, number = null) {
  const body = document.querySelector("#items-body");
  const row = document.createElement("tr");
  row.innerHTML = `
    <td class="item-number">${number ?? body.children.length + 1}</td>
    <td><input data-field="name" value="${escapeHtml(item.name ?? "")}" /></td>
    <td><input class="item-unit" data-field="unit" value="${escapeHtml(item.unit ?? "")}" /></td>
    <td><input class="item-numeric" data-field="quantity" type="number" step="0.001" value="${item.quantity ?? ""}" /></td>
    <td><input class="item-numeric" data-field="unit_price" type="number" step="0.01" value="${item.unit_price ?? ""}" /></td>
    <td><input class="item-numeric" data-field="line_total" type="number" step="0.01" value="${item.line_total ?? ""}" /></td>
    <td><button class="remove-item" type="button" title="Удалить позицию">×</button></td>
  `;
  row.querySelector(".remove-item").addEventListener("click", () => {
    row.remove();
    renumberItems();
    updateValidation();
  });
  body.append(row);
}

function renumberItems() {
  document.querySelectorAll("#items-body tr").forEach((row, index) => {
    row.querySelector(".item-number").textContent = index + 1;
  });
}

function renderRecord() {
  const record = state.records[state.current];
  if (!record) return;

  document.querySelector("#record-counter").textContent = `${state.current + 1} / ${state.records.length}`;
  document.querySelector("#previous-record").disabled = state.current === 0;
  document.querySelector("#next-record").disabled = state.current === state.records.length - 1;
  document.querySelector("#document-name").textContent = record.source_file;
  document.querySelector("#pdf-preview").src = state.objectUrls[state.current];

  for (const input of form.querySelectorAll("input[name]")) {
    input.value = getNested(record, input.name) ?? "";
  }
  renderItems(record.items);
  confirmed.checked = Boolean(record.reviewed);

  const warnings = document.querySelector("#warnings");
  if (record.warnings?.length) {
    warnings.innerHTML = `<strong>Обратите внимание</strong><ul>${record.warnings
      .map((warning) => `<li>${escapeHtml(warning)}</li>`)
      .join("")}</ul>`;
    warnings.hidden = false;
  } else {
    warnings.hidden = true;
    warnings.innerHTML = "";
  }
  updateReviewStatus();
  updateValidation();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function updateReviewStatus() {
  const badge = document.querySelector("#status-badge");
  const record = state.records[state.current];
  const checkedWithErrors = confirmed.checked && record?.validationIssueCount > 0;
  badge.textContent = checkedWithErrors
    ? "Проверено, есть ошибки"
    : confirmed.checked ? "Проверено" : "Требуется проверка";
  badge.classList.toggle("ready", confirmed.checked && !checkedWithErrors);
  badge.classList.toggle("has-errors", checkedWithErrors);
}

confirmed.addEventListener("change", () => {
  const record = state.records[state.current];
  if (record) record.reviewed = confirmed.checked;
  updateReviewStatus();
});

document.querySelector("#add-item").addEventListener("click", () => {
  addItemRow();
  updateValidation();
});

form.addEventListener("input", (event) => {
  if (event.target === confirmed) return;
  updateValidation();
});

document.querySelector("#previous-record").addEventListener("click", () => {
  saveCurrentRecord();
  state.current -= 1;
  renderRecord();
});
document.querySelector("#next-record").addEventListener("click", () => {
  saveCurrentRecord();
  state.current += 1;
  renderRecord();
});

extractButton.addEventListener("click", async () => {
  clearError();
  extractButton.disabled = true;
  extractButton.textContent = "Обработка…";
  const payload = new FormData();
  for (const file of state.files) payload.append("files", file, file.name);

  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      headers: { "X-Invoice-Agent": "1" },
      body: payload,
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "Не удалось обработать документы");

    state.objectUrls.forEach((url) => URL.revokeObjectURL(url));
    state.objectUrls = state.files.map((file) => URL.createObjectURL(file));
    state.records = body.records.map((record) => ({ ...record, reviewed: false }));
    state.current = 0;
    workspace.hidden = false;
    renderRecord();
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
  } finally {
    extractButton.disabled = false;
    extractButton.textContent = "Извлечь данные";
  }
});

async function exportRegister(format) {
  saveCurrentRecord();
  const unreviewed = state.records.filter((record) => !record.reviewed).length;
  if (unreviewed > 0) {
    const proceed = window.confirm(
      `Не проверено документов: ${unreviewed}. Всё равно сформировать реестр?`,
    );
    if (!proceed) return;
  }

  const response = await fetch(`/api/export?format=${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Invoice-Agent": "1" },
    body: JSON.stringify({ records: state.records }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    showError(body.error || "Не удалось сформировать реестр");
    return;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `invoice-register.${format}`;
  link.click();
  URL.revokeObjectURL(url);
}

document.querySelector("#export-csv").addEventListener("click", () => exportRegister("csv"));
document.querySelector("#export-xlsx").addEventListener("click", () => exportRegister("xlsx"));


if (window.Chart) {
  Chart.defaults.color = "#5a2f0f";
  Chart.defaults.borderColor = "rgba(180, 83, 9, 0.2)";
  Chart.defaults.plugins.legend.labels.color = "#5a2f0f";
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(255, 248, 235, 0.96)";
  Chart.defaults.plugins.tooltip.titleColor = "#3f2b12";
  Chart.defaults.plugins.tooltip.bodyColor = "#5a2f0f";
}

const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => b.classList.remove("active"));
    tabPanels.forEach((panel) => panel.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.getAttribute("data-tab");
    document
      .querySelector(`.tab-panel[data-panel="${target}"]`)
      .classList.add("active");
  });
});

const addItemBtn = document.getElementById("add-item");
if (addItemBtn) {
  addItemBtn.addEventListener("click", () => {
    const wrapper = document.getElementById("items");
    if (!wrapper) {
      return;
    }
    const rawOptions = wrapper.getAttribute("data-item-options") || "";
    const options = rawOptions.split("|").filter(Boolean);
    const optionHtml = options.length
      ? options.map((opt) => `<option value="${opt}">${opt}</option>`).join("")
      : "<option value=\"\">Select</option>";
    const row = document.createElement("div");
    row.className = "table-row";
    row.innerHTML = `
      <div>
        <select name="item_type">
          ${optionHtml}
        </select>
      </div>
      <div><input type="number" name="item_qty" value="1" min="1" /></div>
      <div><input type="text" name="item_notes" placeholder="Style, fabric, etc." /></div>
      <div><button type="button" class="btn ghost item-delete" aria-label="Remove item">×</button></div>
    `;
    wrapper.appendChild(row);
  });
}

let activeMeasureInput = null;
const MEASURE_FRACTION_LIST_ID = "measure-fraction-suggestions";
let requirementToggleUid = 0;
let activeTamilSuggestionState = null;

const TAMIL_VOWEL_SIGNS = {
  a: "",
  aa: "ா",
  i: "ி",
  ii: "ீ",
  u: "ு",
  uu: "ூ",
  e: "ெ",
  ee: "ே",
  ai: "ை",
  o: "ொ",
  oo: "ோ",
  au: "ௌ",
};

const TAMIL_INDEPENDENT_VOWELS = {
  a: "அ",
  aa: "ஆ",
  i: "இ",
  ii: "ஈ",
  u: "உ",
  uu: "ஊ",
  e: "எ",
  ee: "ஏ",
  ai: "ஐ",
  o: "ஒ",
  oo: "ஓ",
  au: "ஔ",
};

const TAMIL_CONSONANTS_PRIMARY = {
  ng: "ங",
  nj: "ஞ",
  zh: "ழ",
  th: "த",
  ch: "ச",
  sh: "ச",
  kh: "க",
  gh: "க",
  dh: "த",
  bh: "ப",
  ph: "ப",
  k: "க",
  g: "க",
  c: "ச",
  s: "ச",
  j: "ஜ",
  t: "ட",
  d: "ட",
  n: "ந",
  p: "ப",
  b: "ப",
  m: "ம",
  y: "ய",
  r: "ர",
  l: "ல",
  v: "வ",
  w: "வ",
  h: "ஹ",
  f: "ஃப",
  q: "க",
  x: "க்ச",
  z: "ஜ",
};

const TAMIL_CONSONANTS_ALT = {
  ...TAMIL_CONSONANTS_PRIMARY,
  sh: "ஷ",
  s: "ஸ",
};

const TAMIL_VOWEL_KEYS = [
  "aa",
  "ii",
  "uu",
  "ee",
  "oo",
  "ai",
  "au",
  "a",
  "i",
  "u",
  "e",
  "o",
];

const TAMIL_CONSONANT_KEYS = Object.keys(TAMIL_CONSONANTS_PRIMARY).sort(
  (a, b) => b.length - a.length
);

function transliterateRomanWordToTamil(rawWord, consonantMap) {
  const word = String(rawWord || "").toLowerCase();
  let out = "";
  let i = 0;
  while (i < word.length) {
    const ch = word[i];
    if (!/[a-z]/.test(ch)) {
      out += ch;
      i += 1;
      continue;
    }

    let consonantKey = "";
    for (const key of TAMIL_CONSONANT_KEYS) {
      if (word.startsWith(key, i)) {
        consonantKey = key;
        break;
      }
    }
    if (consonantKey) {
      const base = consonantMap[consonantKey] || "";
      i += consonantKey.length;
      let vowelKey = "";
      for (const vKey of TAMIL_VOWEL_KEYS) {
        if (word.startsWith(vKey, i)) {
          vowelKey = vKey;
          break;
        }
      }
      if (vowelKey) {
        out += `${base}${TAMIL_VOWEL_SIGNS[vowelKey] ?? ""}`;
        i += vowelKey.length;
      } else {
        out += `${base}்`;
      }
      continue;
    }

    let independent = "";
    for (const vKey of TAMIL_VOWEL_KEYS) {
      if (word.startsWith(vKey, i)) {
        independent = TAMIL_INDEPENDENT_VOWELS[vKey] || "";
        i += vKey.length;
        break;
      }
    }
    if (independent) {
      out += independent;
      continue;
    }
    out += ch;
    i += 1;
  }
  return out;
}

function transliterateToTamilSuggestions(token) {
  const clean = String(token || "").trim();
  if (!/^[a-z]+$/i.test(clean) || clean.length < 2) {
    return [];
  }
  const primary = transliterateRomanWordToTamil(clean, TAMIL_CONSONANTS_PRIMARY);
  const alternate = transliterateRomanWordToTamil(clean, TAMIL_CONSONANTS_ALT);
  const suggestions = [];
  if (primary) suggestions.push(primary);
  if (alternate && alternate !== primary) suggestions.push(alternate);
  return suggestions.slice(0, 3);
}

function getRomanTokenAtCursor(value, cursor) {
  const text = String(value || "");
  const safeCursor = Number.isFinite(cursor) ? cursor : text.length;
  const left = text.slice(0, safeCursor);
  const right = text.slice(safeCursor);
  const leftMatch = left.match(/[a-zA-Z]+$/);
  const rightMatch = right.match(/^[a-zA-Z]*/);
  const leftPart = leftMatch ? leftMatch[0] : "";
  const rightPart = rightMatch ? rightMatch[0] : "";
  const token = `${leftPart}${rightPart}`;
  if (!token) {
    return null;
  }
  const start = safeCursor - leftPart.length;
  const end = safeCursor + rightPart.length;
  return { token, start, end };
}

function ensureTamilSuggestionBox(textarea) {
  if (!textarea) return null;
  if (textarea.parentElement) {
    textarea.parentElement.classList.add("tamil-ime-host");
  }
  let box = textarea.parentElement?.querySelector(".tamil-suggestion-box");
  if (!box) {
    box = document.createElement("div");
    box.className = "tamil-suggestion-box";
    box.hidden = true;
    textarea.insertAdjacentElement("afterend", box);
  }
  return box;
}

function hideTamilSuggestions(textarea) {
  if (!textarea) return;
  const box = textarea.parentElement?.querySelector(".tamil-suggestion-box");
  if (box) {
    box.hidden = true;
    box.innerHTML = "";
  }
  if (activeTamilSuggestionState && activeTamilSuggestionState.textarea === textarea) {
    activeTamilSuggestionState = null;
  }
}

function applyTamilSuggestion(textarea, picked) {
  if (!activeTamilSuggestionState || !textarea || !picked) {
    return;
  }
  const { start, end } = activeTamilSuggestionState;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  textarea.value = `${before}${picked}${after}`;
  const nextPos = before.length + picked.length;
  textarea.setSelectionRange(nextPos, nextPos);
  textarea.focus();
  hideTamilSuggestions(textarea);
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function replaceTokenInTextarea(textarea, start, end, replacement, trailing = "") {
  if (!textarea) return;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  textarea.value = `${before}${replacement}${trailing}${after}`;
  const nextPos = before.length + replacement.length + trailing.length;
  textarea.setSelectionRange(nextPos, nextPos);
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function wireTamilNotesSuggestions(container) {
  container.querySelectorAll('textarea[name="measure_notes"], textarea[name="notes"], textarea[placeholder*="notes"], textarea[placeholder*="Notes"]').forEach((textarea) => {
    if (textarea.dataset.tamilSuggestWired === "1") {
      return;
    }
    textarea.dataset.tamilSuggestWired = "1";
    textarea.setAttribute("autocomplete", "off");
    const box = ensureTamilSuggestionBox(textarea);
    if (!box) return;

    const refresh = () => {
      const cursor = textarea.selectionStart;
      const tokenInfo = getRomanTokenAtCursor(textarea.value, cursor);
      if (!tokenInfo) {
        hideTamilSuggestions(textarea);
        return;
      }
      const suggestions = transliterateToTamilSuggestions(tokenInfo.token);
      if (!suggestions.length) {
        hideTamilSuggestions(textarea);
        return;
      }
      box.innerHTML = "";
      suggestions.forEach((word) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tamil-suggestion-item";
        btn.textContent = word;
        btn.addEventListener("mousedown", (event) => {
          event.preventDefault();
          applyTamilSuggestion(textarea, word);
        });
        box.appendChild(btn);
      });
      const firstBtn = box.querySelector(".tamil-suggestion-item");
      if (firstBtn) {
        firstBtn.classList.add("active");
      }
      box.hidden = false;
      activeTamilSuggestionState = {
        textarea,
        start: tokenInfo.start,
        end: tokenInfo.end,
      };
    };

    textarea.addEventListener("input", refresh);
    textarea.addEventListener("focus", refresh);
    textarea.addEventListener("click", refresh);
    textarea.addEventListener("keyup", refresh);
    textarea.addEventListener("blur", () => {
      setTimeout(() => hideTamilSuggestions(textarea), 120);
    });
    textarea.addEventListener("keydown", (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      const hasSuggestions =
        activeTamilSuggestionState &&
        activeTamilSuggestionState.textarea === textarea &&
        !box.hidden &&
        box.children.length > 0;

      const commitKey = event.key;
      const shouldCommitWithDelimiter =
        commitKey === " " ||
        commitKey === "Enter" ||
        commitKey === "." ||
        commitKey === "," ||
        commitKey === "!" ||
        commitKey === "?" ||
        commitKey === ";" ||
        commitKey === ":";
      if (hasSuggestions && shouldCommitWithDelimiter) {
        const first = box.querySelector(".tamil-suggestion-item");
        if (first && activeTamilSuggestionState) {
          event.preventDefault();
          const trailing = commitKey === "Enter" ? "\n" : commitKey;
          replaceTokenInTextarea(
            textarea,
            activeTamilSuggestionState.start,
            activeTamilSuggestionState.end,
            first.textContent || "",
            trailing
          );
          hideTamilSuggestions(textarea);
        }
        return;
      }

      if (!hasSuggestions) {
        return;
      }
      if (event.key === "Tab" || event.key === "Enter") {
        event.preventDefault();
        const first = box.querySelector(".tamil-suggestion-item");
        if (first) {
          applyTamilSuggestion(textarea, first.textContent || "");
        }
      } else if (event.key === "Escape") {
        hideTamilSuggestions(textarea);
      }
    });
  });
}

function getMeasurementCustomerPrefix() {
  const hidden = document.getElementById("customer-id-hidden");
  const display = document.getElementById("customer-id-display");
  const hiddenRaw = hidden ? String(hidden.value || "").trim() : "";
  if (/^\d+$/.test(hiddenRaw)) {
    return String(parseInt(hiddenRaw, 10)).padStart(6, "0");
  }
  const displayRaw = display ? String(display.value || "").trim() : "";
  const digits = displayRaw.replace(/\D+/g, "");
  if (digits) {
    return String(parseInt(digits, 10)).padStart(6, "0");
  }
  return "000001";
}

function refreshMeasurementTitles(scope = document) {
  const blocks = Array.from(scope.querySelectorAll(".measurement-list .measurement-block"));
  if (!blocks.length) {
    return;
  }
  const prefix = getMeasurementCustomerPrefix();
  blocks.forEach((block, index) => {
    const orderNoText = `${prefix}/${index + 1}`;
    const orderNoInput = block.querySelector(".measure-order-no-input");
    if (orderNoInput) {
      orderNoInput.value = orderNoText;
    }
    const orderNo = block.querySelector(".measure-order-no-value");
    if (orderNo) {
      orderNo.textContent = orderNoText;
    }
  });
}
window.refreshMeasurementTitles = refreshMeasurementTitles;

function wireMeasurementDateSync(scope = document) {
  const workerHidden = document.getElementById("worker-delivery-date-hidden");
  const dueHidden = document.getElementById("due-date-hidden");
  const blocks = Array.from(document.querySelectorAll(".measurement-list .measurement-block"));
  if (!blocks.length) {
    return;
  }

  const defaultWorker = workerHidden ? (workerHidden.value || "") : "";
  const defaultDue = dueHidden ? (dueHidden.value || "") : "";
  const syncHiddenFromFirstBlock = () => {
    const firstBlock = document.querySelector(".measurement-list .measurement-block");
    if (!firstBlock) {
      return;
    }
    const firstWorker = firstBlock.querySelector(".measure-worker-date-input");
    const firstDue = firstBlock.querySelector(".measure-due-date-input");
    if (workerHidden && firstWorker) {
      workerHidden.value = firstWorker.value || "";
    }
    if (dueHidden && firstDue) {
      dueHidden.value = firstDue.value || "";
    }
  };

  blocks.forEach((block) => {
    const workerInput = block.querySelector(".measure-worker-date-input");
    const dueInput = block.querySelector(".measure-due-date-input");
    if (workerInput && !workerInput.value && defaultWorker) {
      workerInput.value = defaultWorker;
    }
    if (dueInput && !dueInput.value && defaultDue) {
      dueInput.value = defaultDue;
    }

    if (workerInput && workerInput.dataset.dateWired !== "1") {
      workerInput.dataset.dateWired = "1";
      const syncWorker = () => syncHiddenFromFirstBlock();
      workerInput.addEventListener("change", syncWorker);
      workerInput.addEventListener("input", syncWorker);
    }
    if (dueInput && dueInput.dataset.dateWired !== "1") {
      dueInput.dataset.dateWired = "1";
      const syncDue = () => syncHiddenFromFirstBlock();
      dueInput.addEventListener("change", syncDue);
      dueInput.addEventListener("input", syncDue);
    }
  });
  syncHiddenFromFirstBlock();
}

function ensureMeasureFractionDatalist() {
  let list = document.getElementById(MEASURE_FRACTION_LIST_ID);
  if (list) {
    return list;
  }
  list = document.createElement("datalist");
  list.id = MEASURE_FRACTION_LIST_ID;
  document.body.appendChild(list);
  updateMeasureFractionOptions("1");
  return list;
}

function updateMeasureFractionOptions(rawValue) {
  const list = document.getElementById(MEASURE_FRACTION_LIST_ID);
  if (!list) {
    return;
  }
  const text = String(rawValue || "").trim();
  const token = text.split(/\s+/)[0] || "";
  const tokenMatch = token.match(/^\d+(?:\.\d+)?$/);
  const anyMatch = text.match(/(\d+(?:\.\d+)?)/);
  const base = tokenMatch ? token : (anyMatch ? anyMatch[1] : "1");
  const values = [
    `${base}`,
    `${base} 1/2`,
    `${base} 1/4`,
    `${base} 3/4`,
  ];
  list.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    list.appendChild(option);
  });
}

function filterSubcategoryOptions(block) {
  const categorySelect = block.querySelector(".category-select");
  const subSelect = block.querySelector(".subcategory-select");
  if (!categorySelect || !subSelect) {
    return;
  }
  const categoryId = categorySelect.value || "";
  const options = Array.from(subSelect.querySelectorAll("option"));
  options.forEach((opt) => {
    const optCat = opt.getAttribute("data-category-id") || "";
    if (!optCat) {
      opt.hidden = false;
      return;
    }
    opt.hidden = categoryId && optCat !== categoryId;
  });
  if (categoryId && subSelect.value) {
    const selected = subSelect.querySelector(`option[value="${subSelect.value}"]`);
    if (selected && selected.hidden) {
      subSelect.value = "";
    }
  }
}

function wireRequirementToggleIds(container) {
  container
    .querySelectorAll('.req-toggle input[type="checkbox"]')
    .forEach((input) => {
      const toggle = input.closest(".req-toggle");
      const label = toggle ? toggle.querySelector("label") : null;
      const base = (input.value || "option")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "");
      requirementToggleUid += 1;
      const id = `req-${base || "option"}-${requirementToggleUid}`;
      input.id = id;
      if (label) {
        label.setAttribute("for", id);
      }
    });
}

function wireMeasureInputs(container) {
  ensureMeasureFractionDatalist();
  wireRequirementToggleIds(container);
  wireTamilNotesSuggestions(container);
  container.querySelectorAll(".measure-input").forEach((input) => {
    if (input.dataset.measureWired === "1") {
      return;
    }
    input.dataset.measureWired = "1";
    input.setAttribute("list", MEASURE_FRACTION_LIST_ID);
    input.setAttribute("autocomplete", "off");
    input.addEventListener("focus", () => {
      activeMeasureInput = input;
      updateMeasureFractionOptions(input.value);
    });
    input.addEventListener("input", () => {
      updateMeasureFractionOptions(input.value);
    });
  });

  function syncRequirementValue(block) {
    const hidden = block.querySelector('input[name="measure_requirements"]');
    if (!hidden) {
      return;
    }
    const selected = Array.from(
      block.querySelectorAll('.req-toggle input[type="checkbox"]:checked')
    )
      .map((input) => String(input.value || "").trim())
      .filter(Boolean);
    hidden.value = selected.join(", ");
  }

  const measurementBlocks = container.classList?.contains("measurement-block")
    ? [container]
    : Array.from(container.querySelectorAll(".measurement-block"));

  measurementBlocks.forEach((block) => {
    block.querySelectorAll('.req-toggle input[type="checkbox"]').forEach((input) => {
      if (input.dataset.reqWired === "1") {
        return;
      }
      input.dataset.reqWired = "1";
      input.addEventListener("change", () => syncRequirementValue(block));
    });
    syncRequirementValue(block);
  });

  container.querySelectorAll(".fraction-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      if (!activeMeasureInput) {
        return;
      }
      const fraction = chip.getAttribute("data-value");
      const current = activeMeasureInput.value.trim();
      if (!current) {
        activeMeasureInput.value = fraction;
        activeMeasureInput.focus();
        return;
      }
      if (current.includes(fraction)) {
        activeMeasureInput.focus();
        return;
      }
      activeMeasureInput.value = `${current} ${fraction}`.trim();
      activeMeasureInput.focus();
    });
  });

  container.querySelectorAll(".category-select").forEach((select) => {
    if (select.dataset.measureWired === "1") {
      return;
    }
    select.dataset.measureWired = "1";
    select.addEventListener("change", () => {
      const block = select.closest(".measurement-block");
      if (block) {
        filterSubcategoryOptions(block);
        const subSelect = block.querySelector(".subcategory-select");
        if (subSelect) {
          subSelect.dispatchEvent(new Event("change"));
        }
      }
    });
    const block = select.closest(".measurement-block");
    if (block) {
      filterSubcategoryOptions(block);
    }
  });

  container.querySelectorAll(".subcategory-select").forEach((select) => {
    if (select.dataset.measureWired === "1") {
      return;
    }
    select.dataset.measureWired = "1";
    const block = select.closest(".measurement-block");
    const fieldsWrap = block ? block.querySelector(".measurement-fields") : null;
    const emptyNote = block ? block.querySelector(".measurement-empty") : null;
    const normalizeFieldGroup = (group) => {
      if (!group) return [];
      if (Array.isArray(group)) {
        return group
          .map((field) => {
            if (!field || typeof field !== "object") return null;
            const key = String(field.key || field.id || "").trim();
            const label = String(field.label || field.name || key).trim();
            if (!key) return null;
            return { key, label };
          })
          .filter(Boolean);
      }
      if (typeof group === "object") {
        return Object.entries(group)
          .map(([key, label]) => {
            const safeKey = String(key || "").trim();
            const safeLabel = String(label || safeKey).trim();
            if (!safeKey) return null;
            return { key: safeKey, label: safeLabel };
          })
          .filter(Boolean);
      }
      return [];
    };
    const renderFields = () => {
      if (!fieldsWrap) {
        return;
      }
      const existingValues = {};
      fieldsWrap.querySelectorAll('input[name^="measure_"]').forEach((input) => {
        const key = String(input.name || "").replace(/^measure_/, "");
        if (!key) {
          return;
        }
        existingValues[key] = input.value || "";
      });
      const map = window.measurementFieldMap || {};
      const subId = select.value || "";
      const fields = normalizeFieldGroup(subId && map[subId] ? map[subId] : []);
      const allFieldKeys = [];
      Object.values(map).forEach((group) => {
        normalizeFieldGroup(group).forEach((field) => {
          const key = (field.key || "").trim();
          if (key && !allFieldKeys.includes(key)) {
            allFieldKeys.push(key);
          }
        });
      });
      fieldsWrap.innerHTML = "";
      fieldsWrap.classList.remove("grid", "four");
      const visibleFieldKeys = [];
      if (!fields.length) {
        if (emptyNote) {
          emptyNote.style.display = "";
        }
      } else {
        if (emptyNote) {
          emptyNote.style.display = "none";
        }
        fieldsWrap.classList.add("grid", "four");
        fields.forEach((field) => {
          const label = document.createElement("label");
          const fieldKey = (field.key || field.id || "").trim();
          const fieldLabel = field.label || "";
          if (!fieldKey) {
            return;
          }
          visibleFieldKeys.push(fieldKey);
          const title = document.createElement("span");
          title.className = "field-label";
          title.dataset.fieldKey = fieldKey;
          title.textContent = fieldLabel;
          const input = document.createElement("input");
          input.className = "measure-input";
          input.type = "text";
          input.name = `measure_${fieldKey}`;
          input.setAttribute("list", MEASURE_FRACTION_LIST_ID);
          input.setAttribute("autocomplete", "off");
          if (Object.prototype.hasOwnProperty.call(existingValues, fieldKey)) {
            input.value = existingValues[fieldKey];
          }
          label.appendChild(title);
          label.appendChild(input);
          fieldsWrap.appendChild(label);
        });
      }

      // Keep backend list parsing aligned: each measurement block must submit
      // one value (possibly empty) for every known measurement field key.
      allFieldKeys.forEach((key) => {
        if (visibleFieldKeys.includes(key)) {
          return;
        }
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = `measure_${key}`;
        hidden.value = "";
        fieldsWrap.appendChild(hidden);
      });
    };
    select.addEventListener("change", renderFields);
    renderFields();
  });

  container.querySelectorAll(".qty-btn").forEach((btn) => {
    if (btn.dataset.measureWired === "1") {
      return;
    }
    btn.dataset.measureWired = "1";
    btn.addEventListener("click", () => {
      const step = Number(btn.dataset.step || 0);
      const input = btn.parentElement?.querySelector("input");
      if (!input) return;
      const current = Number(input.value || 1);
      const next = Math.max(1, current + step);
      input.value = String(next);
    });
  });
}

document.querySelectorAll(".measurement-list").forEach((panel) => {
  wireMeasureInputs(panel);
});
wireTamilNotesSuggestions(document);
refreshMeasurementTitles(document);
wireMeasurementDateSync(document);

document.querySelectorAll(".add-measure").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.getAttribute("data-target");
    const list = document.getElementById(target);
    const template = document.getElementById("measure-template");
    if (!list || !template) {
      return;
    }
    const clone = template.content.cloneNode(true);
    const newBlock = clone.querySelector(".measurement-block");
    list.appendChild(clone);
    if (newBlock) {
      newBlock.querySelectorAll("input, select, textarea").forEach((el) => {
        if (el.matches(".measure-input")) {
          el.setAttribute("autocomplete", "off");
        }
        if (el instanceof HTMLInputElement) {
          if (el.type === "checkbox" || el.type === "radio") {
            el.checked = false;
            return;
          }
          if (el.classList.contains("measure-order-date-display")) {
            return;
          }
          if (el.type === "button" || el.type === "submit" || el.type === "hidden" || el.type === "file") {
            return;
          }
          el.value = el.name === "measure_qty" ? "1" : "";
        } else if (el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement) {
          el.value = "";
        }
      });
      wireMeasureInputs(newBlock);
      if (window.wireImagePickers) {
        // Wire pickers against the list so newly appended block is included.
        window.wireImagePickers(list);
      }
      refreshMeasurementTitles(document);
      wireMeasurementDateSync(document);
    } else {
      wireMeasureInputs(list);
      if (window.wireImagePickers) {
        window.wireImagePickers(list);
      }
      refreshMeasurementTitles(document);
      wireMeasurementDateSync(document);
    }
  });
});

document.addEventListener("click", (event) => {
  const itemBtn = event.target.closest(".item-delete");
  if (itemBtn) {
    const row = itemBtn.closest(".table-row");
    if (row) {
      row.remove();
    }
  }
  const measureBtn = event.target.closest(".measure-delete");
  if (measureBtn) {
    const block = measureBtn.closest(".measurement-block");
    if (block) {
      block.remove();
      refreshMeasurementTitles(document);
      wireMeasurementDateSync(document);
    }
  }
});


const statusCard = document.querySelector(".chart-card");
if (statusCard && window.Chart) {
  const statusChartEl = document.getElementById("statusChart");
  if (statusChartEl) {
    const progress = Number(statusCard.dataset.progress || 0);
    const ready = Number(statusCard.dataset.ready || 0);
    const delivered = Number(statusCard.dataset.delivered || 0);
    new Chart(statusChartEl, {
      type: "doughnut",
      data: {
        labels: ["In-Progress", "Ready", "Delivered"],
        datasets: [
          {
            data: [progress, ready, delivered],
            backgroundColor: ["#2f80ff", "#f0b59f", "#16a34a"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        plugins: {
          legend: { position: "bottom" },
        },
        cutout: "65%",
      },
    });
  }
}

const teamCard = document.querySelector('.chart-card[data-shirt]');
if (teamCard && window.Chart) {
  const teamChartEl = document.getElementById("teamChart");
  if (teamChartEl) {
    const shirt = Number(teamCard.dataset.shirt || 0);
    const pant = Number(teamCard.dataset.pant || 0);
    new Chart(teamChartEl, {
      type: "bar",
      data: {
        labels: ["Shirt team", "Pant team"],
        datasets: [
          {
            label: "Active orders",
            data: [shirt, pant],
            backgroundColor: ["#a54628", "#2f3a3a"],
            borderRadius: 12,
          },
        ],
      },
      options: {
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
      },
    });
  }
}



const toggleBtn = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const main = document.querySelector(".main-content");

if (toggleBtn && sidebar && main) {
  toggleBtn.addEventListener("click", () => {
    sidebar.classList.toggle("closed");
    main.classList.toggle("full");
  });
}

document.querySelectorAll(".table-wrap").forEach((wrap) => {
  const filters = Array.from(wrap.querySelectorAll(".table-filters input"));
  const rows = Array.from(wrap.querySelectorAll(".table-row")).filter(
    (row) => !row.classList.contains("table-head")
  );
  if (!filters.length || !rows.length) {
    return;
  }

  const filterSpec = filters.map((input, index) => {
    const col = Number(input.dataset.col ?? index);
    return { input, col };
  });

  const applyFilters = () => {
    rows.forEach((row) => {
      let visible = true;
      for (const spec of filterSpec) {
        const value = spec.input.value.trim().toLowerCase();
        if (!value) {
          continue;
        }
        const cells = row.querySelectorAll(":scope > div");
        const cell = cells[spec.col];
        let text = cell ? cell.textContent.toLowerCase() : "";
        if (cell) {
          const input = cell.querySelector("input, select");
          if (input) {
            text += ` ${input.value.toLowerCase()}`;
          }
        }
        if (!text.includes(value)) {
          visible = false;
          break;
        }
      }
      row.style.display = visible ? "" : "none";
    });
  };

  filters.forEach((input) => {
    input.addEventListener("input", applyFilters);
  });
});

const inventoryTable = document.getElementById("inventory-table");
const inventoryFilters = document.querySelectorAll(".inventory-filters input");
if (inventoryTable && inventoryFilters.length) {
  const rows = Array.from(inventoryTable.querySelectorAll("tbody tr"));
  const applyInventoryFilters = () => {
    rows.forEach((row) => {
      const cells = row.querySelectorAll("td");
      if (!cells.length) {
        return;
      }
      let visible = true;
      inventoryFilters.forEach((input) => {
        const value = input.value.trim().toLowerCase();
        if (!value) {
          return;
        }
        const col = Number(input.dataset.col || 0);
        const text = cells[col] ? cells[col].textContent.toLowerCase() : "";
        if (!text.includes(value)) {
          visible = false;
        }
      });
      row.style.display = visible ? "" : "none";
    });
  };
  inventoryFilters.forEach((input) => {
    input.addEventListener("input", applyInventoryFilters);
  });
}

const vendorTable = document.getElementById("vendor-table");
const vendorFilters = document.querySelectorAll(".vendor-filters input");
if (vendorTable && vendorFilters.length) {
  const rows = Array.from(vendorTable.querySelectorAll("tbody tr"));
  const applyVendorFilters = () => {
    rows.forEach((row) => {
      const cells = row.querySelectorAll("td");
      if (!cells.length) {
        return;
      }
      let visible = true;
      vendorFilters.forEach((input) => {
        const value = input.value.trim().toLowerCase();
        if (!value) {
          return;
        }
        const col = Number(input.dataset.col || 0);
        const text = cells[col] ? cells[col].textContent.toLowerCase() : "";
        if (!text.includes(value)) {
          visible = false;
        }
      });
      row.style.display = visible ? "" : "none";
    });
  };
  vendorFilters.forEach((input) => {
    input.addEventListener("input", applyVendorFilters);
  });
}

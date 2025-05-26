console.log("🟢 [EXT] Event Create script gestart");

let hasInjected = false;
let lastURL = location.href;

const userLang = navigator.language.slice(0, 2);
console.log("🌐 Gedetecteerde taal:", userLang);

const t = window.translations?.[userLang] || window.translations?.["en"] || {};
console.log("📘 Vertalingen geladen:", t);

// ⏱️ Voeg functie toe voor microsecondenprecisie
function formatToMicroseconds(date) {
  const iso = date.toISOString();
  const match = iso.match(/^(.+\.\d{3})Z$/);
  return match ? `${match[1]}000Z` : iso.replace('Z', '000Z');
}

function observeURLandInject() {
  console.log("🔁 Observer actief om URL te monitoren...");
  setInterval(() => {
    const currentURL = location.href;
    if (currentURL !== lastURL) {
      console.log("🌍 URL veranderd:", currentURL);
      lastURL = currentURL;
      hasInjected = false;
    }

    if (currentURL.includes("/eventedit") && !hasInjected) {
      console.log("✅ Op eventedit pagina - probeer te injecteren");
      const interval = setInterval(() => {
        const success = tryInjectUI();
        if (success) {
          console.log("✅ Injectie gelukt");
          clearInterval(interval);
        } else {
          console.log("⏳ Injectie poging mislukt, probeer opnieuw...");
        }
      }, 300);
    }
  }, 500);
}

function tryInjectUI() {
  console.log("🔍 Probeer DOM te vinden...");

  const editable = document.querySelector("div[contenteditable='true'][role='textbox']");
  const descriptionContainer = editable?.closest("div[jsname='yrriRe']");
  const container = document.querySelector("div.ewPPR");
  const saveButton = document.querySelector('#xSaveBu');

  // 👇 Check of editable en descriptionContainer gevonden zijn
  if (!editable || !descriptionContainer) {
    console.warn("❌ Beschrijvingscontainer of editable veld niet gevonden");
    return false;
  }

  if (!saveButton) {
    console.warn("❌ Opslaan-knop niet gevonden");
    return false;
  }

  if (!container) {
    console.warn("❌ Container ewPPR niet gevonden");
    return false;
  }

  const injectTarget = descriptionContainer?.parentElement || container;

  if (!injectTarget || !saveButton) return false;

  if (document.querySelector(".custom-extension-wrapper")) {
    console.log("ℹ️ UI al geïnjecteerd");
    hasInjected = true;
    return true;
  }

  injectUI(editable, injectTarget, saveButton, descriptionContainer);
  hasInjected = true;
  return true;
}


function updateDescription(textarea, data) {
  const json = JSON.stringify(data, null, 2);
  console.log("💾 JSON geschreven naar veld:", json);
  textarea.innerText = json;
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function validateForm(inputs, saveButton) {
  const sessionValid = inputs.session_type.value.trim() !== "";
  const capacityValue = inputs.capacity.value.trim();
  const capacityValid = capacityValue !== "" && !isNaN(Number(capacityValue));
  const descriptionValid = inputs.description.value.trim() !== "";

  const guestsRaw = inputs.guestspeaker.value.trim();
  const guestList = guestsRaw.split(",").map(e => e.trim());
  const guestValid = guestsRaw !== "" && guestList.every(email => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email));

  const allValid = sessionValid && capacityValid && guestValid && descriptionValid;

  console.log("🔍 Validatie status:", {
    sessionValid,
    capacityValid,
    guestValid,
    descriptionValid
  });

  saveButton.style.cursor = allValid ? "pointer" : "not-allowed";
  saveButton.setAttribute("aria-disabled", allValid ? "false" : "true");
  saveButton.disabled = !allValid;

  return allValid;
}

function injectUI(textarea, injectTarget, saveButton, descriptionContainer) {
  if (descriptionContainer) {
    descriptionContainer.style.display = "none";
    const toolbar = descriptionContainer.previousElementSibling;
    if (toolbar && toolbar.getAttribute("role") === "toolbar") {
      toolbar.style.display = "none";
    }
  }

  const wrapper = document.createElement("div");
  wrapper.className = "custom-extension-wrapper";

  let jsonData = {
    uuid: formatToMicroseconds(new Date()),
    guestspeaker: [],
    session_type: "",
    capacity: 0,
    description: ""
  };

  // 🧼 JSON proberen te parsen vanuit textarea
  let existingText = textarea.innerText
    .replace(/\u00A0/g, ' ')
    .replace(/[\r\n]+/g, '\n')
    .replace(/^\s*[\n\r]/gm, '')
    .trim();

  console.log("📝 Beschrijving na opschoning:\n", existingText);

  if (existingText) {
    try {
      const parsed = JSON.parse(existingText);
      if (parsed && typeof parsed === "object") {
        jsonData = { ...jsonData, ...parsed };
        console.log("✅ JSON uit beschrijving geladen:", jsonData);
      }
    } catch (e1) {
      console.warn("❌ JSON parsing mislukt:", e1.message);
      try {
        const fixed = existingText
          .replace(/(\w+):/g, '"$1":')
          .replace(/'/g, '"');
        const parsed = JSON.parse(fixed);
        if (parsed && typeof parsed === "object") {
          jsonData = { ...jsonData, ...parsed };
          console.log("🛠️ Gedeeltelijk herstelde JSON geladen:", jsonData);
        }
      } catch (e2) {
        console.error("❌ Ook herstelde JSON parsing mislukt:", e2.message);
      }
    }
  }

  const inputs = {};
  const errors = {};

  const fields = [
    { key: "session_type", type: "text", label: t.eventType || "Event type" },
    { key: "capacity", type: "number", label: t.capacity || "Capacity" },
    { key: "guestspeaker", type: "text", label: t.guestspeaker || "Guest speakers" },
    { key: "description", type: "textarea", label: t.description || "Description" }
  ];

  fields.forEach(({ key, type, label }) => {
    const fieldWrapper = document.createElement("div");
    fieldWrapper.className = "custom-field";

    const labelEl = document.createElement("label");
    labelEl.textContent = label;
    labelEl.className = "custom-label";

    let input;
    if (type === "textarea") {
      input = document.createElement("textarea");
      input.rows = 4;
    } else {
      input = document.createElement("input");
      input.type = type;
    }

    input.className = "custom-input";

    // 🔄 Initieel invullen met JSON-data
    input.value = key === "guestspeaker"
      ? (jsonData[key]?.join(", ") || "")
      : (jsonData[key] ?? "");

    inputs[key] = input;

    const errorEl = document.createElement("div");
    errorEl.className = "custom-error";
    errorEl.style.display = "none";
    errors[key] = errorEl;

    input.addEventListener("input", () => {
      const value = input.value.trim();

      if (key === "guestspeaker") {
        const emails = value.split(",").map(e => e.trim());
        const invalid = emails.find(e => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e));
        if (value === "") {
          errorEl.textContent = t.emailError || "Please enter a valid email address.";
          errorEl.style.display = "block";
          jsonData[key] = [];
        } else if (invalid) {
          errorEl.textContent = t.emailError || "Please enter a valid email address.";
          errorEl.style.display = "block";
          jsonData[key] = [];
        } else {
          errorEl.style.display = "none";
          jsonData[key] = emails;
        }
      } else if (key === "capacity") {
        if (value === "" || isNaN(Number(value))) {
          errorEl.textContent = t.capacityError || "Capacity must be a number.";
          errorEl.style.display = "block";
          jsonData[key] = 0;
        } else {
          errorEl.style.display = "none";
          jsonData[key] = Number(value);
        }
      } else {
        if (value === "") {
          errorEl.textContent = t.pastDateError || "This field is required.";
          errorEl.style.display = "block";
        } else {
          errorEl.style.display = "none";
        }
        jsonData[key] = value;
      }

      updateDescription(textarea, jsonData);
      validateForm(inputs, saveButton);
    });

    fieldWrapper.appendChild(labelEl);
    fieldWrapper.appendChild(input);
    fieldWrapper.appendChild(errorEl);
    wrapper.appendChild(fieldWrapper);
  });

  injectTarget.appendChild(wrapper);
  validateForm(inputs, saveButton);
  updateDescription(textarea, jsonData);
  console.log("✅ UI met velden en bestaande data toegevoegd");
}

observeURLandInject();

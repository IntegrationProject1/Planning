// 🌐 Detecteer taal en haal vertalingen op
const userLang = navigator.language.slice(0, 2);
const t = window.translations[userLang] || window.translations["en"];

console.log("🌐 Gedetecteerde taal:", navigator.language);
console.log("🌐 Gebruikte taalcode:", userLang);
console.log("🔍 Beschikbare vertalingen:", Object.keys(window.translations));
console.log("📅 Agenda Extender actief");

let hasInjected = false;
let lastURL = location.href;


function formatToMilliseconds(date) {
  const iso = date.toISOString();
  return iso.replace(/\.\d+Z$/, '.000Z');
}


function formatToMicroseconds(date) {
  const iso = date.toISOString(); // "2025-05-25T17:05:29.129Z"
  const match = iso.match(/^(.+\.\d{3})Z$/); // match exacte vorm met 3 ms
  if (match) {
    return `${match[1]}000Z`; // voeg 3 nullen toe vóór de Z
  } else {
    return iso.replace('Z', '000Z'); // fallback als geen match
  }
}


function updateDescription(textarea, data) {
  textarea.value = JSON.stringify(data, null, 2);
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function validateForm(inputs, requiredFields, createButton) {
  let isValid = true;

  for (const key of requiredFields) {
    const value = inputs[key]?.value?.trim();
    if (!value) {
      isValid = false;
      break;
    }

    if (key === "organizer") {
      const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      if (!emailValid) {
        isValid = false;
        break;
      }
    }

    if (key === "capacity" && isNaN(Number(value))) {
      isValid = false;
      break;
    }
  }

  createButton.disabled = !isValid;
  createButton.style.cursor = isValid ? "pointer" : "not-allowed";
}

function tryInjectUI() {
  const descriptionField = document.querySelector("textarea");
  const settingsBlock = document.querySelector("form") || descriptionField?.parentElement;
  const createButton = document.querySelector('button[jsname="zqs2Af"]');

  if (!descriptionField || !settingsBlock || !createButton) return false;
  if (document.querySelector(".custom-extension")) {
    hasInjected = true;
    return true;
  }

  injectUI(descriptionField, settingsBlock, createButton);
  hasInjected = true;
  return true;
}

function injectUI(descriptionField, settingsBlock, createButton) {
  descriptionField.style.display = "none";

  const container = document.createElement("div");
  container.className = "custom-extension";

  const jsonData = {
    uuid: formatToMicroseconds(new Date()),
    createdAt: formatToMicroseconds(new Date()),
    startDateTime: "",
    endDateTime: "",
    description: "",
    capacity: "",
    organizer: "",
    eventType: "",
    location: "",
  };

  const requiredFields = [
    "startDateTime",
    "endDateTime",
    "description",
    "capacity",
    "organizer",
    "eventType",
    "location"
  ];

  const inputs = {};

  // Datumvelden
  const dateWrapper = document.createElement("div");
  dateWrapper.className = "date-wrapper";

  [
    { key: "startDateTime", label: t.startTime },
    { key: "endDateTime", label: t.endTime }
  ].forEach(({ key, label }) => {
    const fieldWrapper = document.createElement("div");
    fieldWrapper.className = "date-field";

    const labelEl = document.createElement("div");
    labelEl.className = "date-label";
    labelEl.innerText = label;

    const input = document.createElement("input");
    input.type = "datetime-local";
    input.className = "custom-input";

    const now = new Date();
    const maxDate = new Date();
    maxDate.setFullYear(now.getFullYear() + 5);
    input.min = now.toISOString().slice(0, 16);
    input.max = maxDate.toISOString().slice(0, 16);

    const errorEl = document.createElement("div");
    errorEl.className = "validation-error";
    errorEl.style.display = "none";

    input.addEventListener("input", () => {
      const selectedDate = new Date(input.valueAsNumber);
      let showError = false;

      if (selectedDate < now) {
        errorEl.innerText = t.pastDateError || "De gekozen datum mag niet in het verleden liggen.";
        showError = true;
        input.value = "";
      } else if (selectedDate > maxDate) {
        errorEl.innerText = t.maxDateError || "De gekozen datum ligt meer dan 5 jaar in de toekomst.";
        showError = true;
        input.value = "";
      } else {
        jsonData[key] = input.value ? formatToMilliseconds(selectedDate) : "";
      }

      errorEl.style.display = showError ? "block" : "none";
      updateDescription(descriptionField, jsonData);
      validateForm(inputs, requiredFields, createButton);
    });

    inputs[key] = input;
    fieldWrapper.appendChild(labelEl);
    fieldWrapper.appendChild(input);
    fieldWrapper.appendChild(errorEl);
    dateWrapper.appendChild(fieldWrapper);
  });

  container.appendChild(dateWrapper);

  // Extra velden
  const fields = [
    { key: "description", type: "text", placeholder: t.description },
    { key: "capacity", type: "text", placeholder: t.capacity },
    { key: "organizer", type: "email", placeholder: t.organizer },
    { key: "eventType", type: "text", placeholder: t.eventType },
    { key: "location", type: "text", placeholder: t.location },
  ];

  fields.forEach(({ key, type, placeholder }) => {
    const wrapper = document.createElement("div");
    wrapper.style.display = "flex";
    wrapper.style.flexDirection = "column";

    const input = document.createElement("input");
    input.type = type;
    input.placeholder = placeholder;
    input.className = "custom-input";

    const errorEl = document.createElement("div");
    errorEl.className = "validation-error";
    errorEl.style.display = "none";

    input.addEventListener("input", () => {
      const value = input.value.trim();
      let showError = false;

      if (key === "capacity" && isNaN(Number(value))) {
        errorEl.innerText = t.capacityError;
        showError = true;
      } else if (key === "organizer" && value !== "") {
        const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
        if (!emailValid) {
          errorEl.innerText = t.emailError;
          showError = true;
        }
      }

      errorEl.style.display = showError ? "block" : "none";
      jsonData[key] = value;
      updateDescription(descriptionField, jsonData);
      validateForm(inputs, requiredFields, createButton);
    });

    inputs[key] = input;
    wrapper.appendChild(input);
    wrapper.appendChild(errorEl);
    container.appendChild(wrapper);
  });

  createButton.disabled = true;
  createButton.style.cursor = "not-allowed";

  if (createButton.parentElement) {
    createButton.parentElement.insertBefore(container, createButton);
  } else {
    settingsBlock.appendChild(container);
  }

  console.log("UI succesvol geïnjecteerd");
}

function observeURLandInject() {
  const checkPage = () => {
    const currentURL = location.href;
    if (currentURL !== lastURL) {
      lastURL = currentURL;
      hasInjected = false;
      console.log("Navigatie gedetecteerd:", currentURL);
    }

    if (currentURL.includes("/settings/createcalendar") && !hasInjected) {
      const injectInterval = setInterval(() => {
        const success = tryInjectUI();
        if (success) {
          clearInterval(injectInterval);
          console.log("Injectie gelukt");
        }
      }, 300);
    }
  };

  setInterval(checkPage, 500);
}

observeURLandInject();

if (location.href.includes("/settings/createcalendar")) {
  const interval = setInterval(() => {
    const success = tryInjectUI();
    if (success) clearInterval(interval);
  }, 300);
}

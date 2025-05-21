// 🌐 Detecteer taal en haal vertalingen op
const userLang = navigator.language.slice(0, 2);
const t = window.translations[userLang] || window.translations["en"];

console.log("🛠️ Edit Mode: Agenda Extender actief");

function isValidJson(raw) {
  if (!raw) return false;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && parsed.uuid && parsed.createdAt;
  } catch {
    return false;
  }
}

function updateDescription(textarea, data) {
  textarea.value = JSON.stringify(data, null, 2);
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function injectEditUI() {
  const descriptionField = document.querySelector('textarea[jsname="YPqjbf"]');
  if (!descriptionField) return console.warn("❌ Geen textarea gevonden.");
  const value = descriptionField.value?.trim();

  if (!isValidJson(value)) {
    console.log("📭 Geen geldige JSON, niets injecteren.");
    return;
  }

  const descriptionWrapper = descriptionField.closest(".yEkFYd");
  if (descriptionWrapper) {
    descriptionWrapper.style.display = "none";
    console.log("👻 Omschrijving-wrapper verborgen.");
  }

  const container = document.createElement("div");
  container.className = "custom-extension";

  const jsonData = JSON.parse(value);

  const fields = [
    { key: "uuid", readonly: true },
    { key: "createdAt", readonly: true },
    { key: "startDateTime", label: t.startTime, type: "datetime-local" },
    { key: "endDateTime", label: t.endTime, type: "datetime-local" },
    { key: "description", label: t.description, type: "text" },
    { key: "capacity", label: t.capacity, type: "text" },
    { key: "organizer", label: t.organizer, type: "email" },
    { key: "eventType", label: t.eventType, type: "text" },
    { key: "location", label: t.location, type: "text" },
  ];

  fields.forEach(({ key, label, type = "text", readonly = false }) => {
    const wrapper = document.createElement("div");
    wrapper.className = "date-field";

    const input = document.createElement("input");
    input.type = type;
    input.className = "custom-input";
    input.placeholder = " ";
    if (readonly) input.readOnly = true;

    if (jsonData[key]) {
      input.value = type === "datetime-local"
        ? new Date(jsonData[key]).toISOString().slice(0, 16)
        : jsonData[key];
    }

    const labelEl = document.createElement("div");
    labelEl.className = "date-label";
    labelEl.innerText = label || key;

    const errorEl = document.createElement("div");
    errorEl.className = "validation-error";
    errorEl.style.display = "none";

    input.addEventListener("blur", () => {
      const value = input.value.trim();
      let isValid = true;
      let errorMsg = "";

      if (key === "organizer") {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(value)) {
          isValid = false;
          errorMsg = t.emailError || "Geef een geldig e-mailadres op.";
        }
      }

      if (key === "capacity" && isNaN(Number(value))) {
        isValid = false;
        errorMsg = t.capacityError || "Capaciteit moet een getal zijn.";
      }

      if (key === "startDateTime" || key === "endDateTime") {
        const selectedDate = new Date(value);
        const now = new Date();
        const maxDate = new Date();
        maxDate.setFullYear(now.getFullYear() + 5);

        if (selectedDate < now) {
          isValid = false;
          errorMsg = t.pastDateError || "De gekozen datum mag niet in het verleden liggen.";
        } else if (selectedDate > maxDate) {
          isValid = false;
          errorMsg = t.maxDateError || "De gekozen datum ligt meer dan 5 jaar in de toekomst.";
        }
      }

      if (!isValid) {
        errorEl.innerText = errorMsg;
        errorEl.style.display = "block";
        return;
      } else {
        errorEl.style.display = "none";
        jsonData[key] = type === "datetime-local"
          ? new Date(input.value).toISOString()
          : input.value;
        updateDescription(descriptionField, jsonData);
      }
    });

    wrapper.appendChild(input);
    wrapper.appendChild(labelEl);
    wrapper.appendChild(errorEl);
    container.appendChild(wrapper);
  });

  const exportTarget = document.querySelector('.yEkFYd[jsaction="A8Wr0d:N3Jh3c"]');
  if (exportTarget && exportTarget.parentElement) {
    exportTarget.parentElement.insertBefore(container, exportTarget);
    console.log("✅ Edit UI succesvol geïnjecteerd.");
  } else {
    console.warn("⚠️ Geen injectiepositie gevonden.");
  }
}

const observer = new MutationObserver(() => {
  const description = document.querySelector('textarea[jsname="YPqjbf"]');
  if (description && isValidJson(description.value?.trim())) {
    injectEditUI();
    observer.disconnect();
  }
});

observer.observe(document.body, { childList: true, subtree: true });

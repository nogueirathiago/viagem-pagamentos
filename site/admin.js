const editor = document.querySelector("[data-payment-editor]");
const saveButton = document.querySelector("[data-save-json]");
const copyButton = document.querySelector("[data-copy-json]");
let paymentData;

function paidLabels(member, months) {
  const normalPaid = months.slice(0, member.paid_installments || 0).map((month) => month.label);
  return new Set([...normalPaid, ...(member.prepaid_installments || [])]);
}

function memberFromChecked(name, checkedLabels, months) {
  let paidInstallments = 0;
  for (const month of months) {
    if (!checkedLabels.has(month.label)) break;
    paidInstallments += 1;
  }

  const prepaidInstallments = months
    .slice(paidInstallments)
    .map((month) => month.label)
    .filter((label) => checkedLabels.has(label));

  const member = {
    name,
    paid_installments: paidInstallments,
  };

  if (prepaidInstallments.length) {
    member.prepaid_installments = prepaidInstallments;
  }

  return member;
}

function renderEditor(data) {
  const months = data.payment_rule.months;
  editor.innerHTML = data.couples.map((couple, coupleIndex) => `
    <section class="editor-couple">
      <h2>${couple.name}</h2>
      ${couple.members.map((member, memberIndex) => {
        const labels = paidLabels(member, months);
        return `
          <article class="editor-person">
            <strong>${member.name}</strong>
            <div class="month-checks">
              ${months.map((month) => {
                const id = `c${coupleIndex}-m${memberIndex}-${month.label.replace(/[^a-z0-9]/gi, "")}`;
                const checked = labels.has(month.label) ? "checked" : "";
                return `
                  <label for="${id}">
                    <input id="${id}" type="checkbox" data-couple-index="${coupleIndex}" data-member-index="${memberIndex}" data-month-label="${month.label}" ${checked}>
                    <span>${month.label.split("/")[0]}</span>
                  </label>
                `;
              }).join("")}
            </div>
          </article>
        `;
      }).join("")}
    </section>
  `).join("");
}

function buildUpdatedData() {
  const months = paymentData.payment_rule.months;
  const updated = structuredClone(paymentData);

  updated.couples = paymentData.couples.map((couple, coupleIndex) => ({
    ...couple,
    members: couple.members.map((member, memberIndex) => {
      const checkedLabels = new Set(
        [...document.querySelectorAll(`input[data-couple-index="${coupleIndex}"][data-member-index="${memberIndex}"]:checked`)]
          .map((input) => input.dataset.monthLabel)
      );
      return memberFromChecked(member.name, checkedLabels, months);
    }),
  }));

  return updated;
}

function downloadJson(data) {
  const blob = new Blob([`${JSON.stringify(data, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "data.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function copyJson(data) {
  await navigator.clipboard.writeText(`${JSON.stringify(data, null, 2)}\n`);
  copyButton.textContent = "JSON copiado";
  window.setTimeout(() => {
    copyButton.textContent = "Copiar JSON";
  }, 1800);
}

async function init() {
  const response = await fetch("./data.json");
  if (!response.ok) throw new Error("Nao foi possivel carregar data.json.");
  paymentData = await response.json();
  renderEditor(paymentData);

  saveButton.addEventListener("click", () => downloadJson(buildUpdatedData()));
  copyButton.addEventListener("click", () => copyJson(buildUpdatedData()));
}

init().catch((error) => {
  editor.innerHTML = `<p>${error.message}</p>`;
});

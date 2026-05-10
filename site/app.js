const dataUrl = "./data.json";
const sheetUrl = window.PAYMENT_DATA_SOURCE || "";

const money = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "UTC",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function brl(value) {
  return money.format(roundCents(value));
}

function roundCents(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function totalPaid(member) {
  return (member.paid_installments || 0) + (member.prepaid_installments || []).length;
}

function paidLabels(member, months) {
  const normalPaid = months.slice(0, member.paid_installments || 0).map((month) => month.label);
  return new Set([...normalPaid, ...(member.prepaid_installments || [])]);
}

function coupleTotal(months) {
  return roundCents(months.reduce((sum, month) => sum + month.couple_amount, 0));
}

function couplePaid(couple, months) {
  const labelsByMember = couple.members.map((member) => paidLabels(member, months));
  const paid = months.reduce((sum, month) => {
    const paidCount = labelsByMember.filter((labels) => labels.has(month.label)).length;
    return sum + (month.couple_amount * paidCount) / couple.members.length;
  }, 0);
  return roundCents(paid);
}

function coupleBalance(couple, months) {
  return Math.max(0, roundCents(coupleTotal(months) - couplePaid(couple, months)));
}

function compactPrepaidLabel(label) {
  return `${label.split("/")[0].slice(0, 3)} OK`;
}

function memberProgress(member, installmentsTotal) {
  const status = `${totalPaid(member)}/${installmentsTotal}`;
  const prepaid = member.prepaid_installments || [];
  if (!prepaid.length) return status;
  return `${status} ${prepaid.map(compactPrepaidLabel).join(", ")}`;
}

function coupleProgress(couple, installmentsTotal) {
  const statuses = couple.members.map((member) => memberProgress(member, installmentsTotal));
  if (new Set(statuses).size === 1) return statuses[0];
  return couple.members.map((member) => `${member.name} ${memberProgress(member, installmentsTotal)}`).join(" | ");
}

function averageProgress(couple, installmentsTotal) {
  const paid = couple.members.reduce((sum, member) => sum + totalPaid(member), 0);
  return paid / couple.members.length / installmentsTotal;
}

function formatDate(value) {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function monthName(label) {
  return label.split("/")[0];
}

function progressColor(progress) {
  const hue = Math.round(progress * 128);
  return `hsl(${hue} 72% 48%)`;
}

function progressLightColor(progress) {
  const hue = Math.round(progress * 128);
  return `hsl(${hue} 78% 90%)`;
}

function paidInstallmentCount(data) {
  return data.couples.reduce(
    (sum, couple) => sum + couple.members.reduce((memberSum, member) => memberSum + totalPaid(member), 0),
    0
  );
}

function parseCsvLine(line) {
  const cells = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(cell.trim());
      cell = "";
    } else {
      cell += char;
    }
  }

  cells.push(cell.trim());
  return cells;
}

function parseCsv(text) {
  const [headerLine, ...lines] = text.trim().split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(headerLine).map((header) => header.toLowerCase());
  return lines.map((line) => {
    const cells = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, cells[index] || ""]));
  });
}

function applySheetRows(data, rows) {
  const byCoupleAndName = new Map();
  data.couples.forEach((couple) => {
    couple.members.forEach((member) => {
      byCoupleAndName.set(`${couple.name.toLowerCase()}::${member.name.toLowerCase()}`, member);
      byCoupleAndName.set(member.name.toLowerCase(), member);
    });
  });

  rows.forEach((row) => {
    const name = (row.nome || row.name || "").trim();
    const coupleName = (row.casal || row.couple || "").trim();
    const key = coupleName ? `${coupleName.toLowerCase()}::${name.toLowerCase()}` : name.toLowerCase();
    const member = byCoupleAndName.get(key);
    if (!member) return;

    member.paid_installments = Number(row.parcelas_pagas || row.paid_installments || 0);
    member.prepaid_installments = (row.parcelas_antecipadas || row.prepaid_installments || "")
      .split(";")
      .map((label) => label.trim())
      .filter(Boolean);
  });
}

async function loadData() {
  const response = await fetch(`${dataUrl}?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Nao foi possivel carregar data.json.");
  const data = await response.json();

  if (sheetUrl) {
    const sheetResponse = await fetch(sheetUrl);
    if (!sheetResponse.ok) throw new Error("Nao foi possivel carregar a planilha publicada.");
    applySheetRows(data, parseCsv(await sheetResponse.text()));
  }

  return data;
}

function renderDueDates(months) {
  const target = document.querySelector("[data-due-grid]");
  target.innerHTML = months.map((month, index) => `
    <article class="due-card" style="--delay: ${index * 55}ms">
      <span class="due-index">${String(index + 1).padStart(2, "0")}</span>
      <div>
        <strong>${monthName(month.label)}</strong>
        <span>${formatDate(month.due_date)}</span>
      </div>
      <b class="pill">${brl(month.couple_amount)}</b>
    </article>
  `).join("");
}

function renderCouples(data) {
  const months = data.payment_rule.months;
  const target = document.querySelector("[data-couple-list]");
  target.innerHTML = data.couples.map((couple) => {
    const progress = coupleProgress(couple, data.installments_total);
    const ratio = Math.max(0, Math.min(1, averageProgress(couple, data.installments_total)));
    const color = progressColor(ratio);
    const lightColor = progressLightColor(ratio);
    return `
      <article class="couple-row" style="--progress: ${ratio * 100}%; --progress-color: ${color}; --progress-soft: ${lightColor}">
        <div class="couple-title">
          <span>${Math.round(ratio * 100)}%</span>
          <h3>${couple.name}</h3>
        </div>
        <div class="couple-progress">
          <span class="couple-members">${couple.members.map((member) => member.name).join(" + ")} - ${progress}</span>
          <div class="bar" aria-label="${Math.round(ratio * 100)}% pago"><span style="width: ${ratio * 100}%"></span></div>
        </div>
        <div class="balance">
          <span>Falta</span>
          <strong>${brl(coupleBalance(couple, months))}</strong>
        </div>
      </article>
    `;
  }).join("");
}

function renderPeople(data) {
  const target = document.querySelector("[data-people-grid]");
  target.innerHTML = data.couples.flatMap((couple) => couple.members.map((member) => {
    const ratio = Math.max(0, Math.min(1, totalPaid(member) / data.installments_total));
    const status = memberProgress(member, data.installments_total);
    const color = progressColor(ratio);
    return `
      <article class="person-card" style="--progress: ${ratio * 100}%; --progress-color: ${color}">
        <span>${couple.name}</span>
        <strong>${member.name}</strong>
        <div class="status">${status}</div>
        <div class="bar" aria-label="${Math.round(ratio * 100)}% pago"><span style="width: ${ratio * 100}%"></span></div>
      </article>
    `;
  })).join("");
}

function renderSummary(data) {
  const months = data.payment_rule.months;
  const totalPaidGroup = data.couples.reduce((sum, couple) => sum + couplePaid(couple, months), 0);
  const paidCount = paidInstallmentCount(data);
  const totalCount = data.couples.length * 2 * data.installments_total;
  const progress = Math.max(0, Math.min(100, Math.round((paidCount / totalCount) * 100)));
  const progressRatio = progress / 100;
  const color = progressColor(progressRatio);
  const lightColor = progressLightColor(progressRatio);
  document.querySelector("[data-total-amount]").textContent = brl(data.total_amount);
  document.querySelector("[data-couple-total]").textContent = brl(coupleTotal(months));
  document.querySelector("[data-group-paid]").textContent = brl(totalPaidGroup);
  document.querySelector("[data-group-balance]").textContent = brl(data.total_amount - totalPaidGroup);
  document.querySelector("[data-group-paid-compact]").textContent = brl(totalPaidGroup);
  document.querySelector("[data-group-balance-compact]").textContent = brl(data.total_amount - totalPaidGroup);
  document.querySelector("[data-overall-percent]").textContent = `${progress}%`;
  document.querySelector("[data-donut-percent]").textContent = `${progress}%`;
  document.querySelector("[data-overall-meter]").style.width = `${progress}%`;
  document.querySelector("[data-donut]").style.setProperty("--progress", progress);
  document.documentElement.style.setProperty("--progress-color", color);
  document.documentElement.style.setProperty("--progress-soft", lightColor);
}

function validateData(data) {
  const calculatedTotal = coupleTotal(data.payment_rule.months) * data.couples.length;
  if (roundCents(calculatedTotal) !== roundCents(data.total_amount)) {
    throw new Error(`Total inconsistente: ${brl(calculatedTotal)} calculado para ${brl(data.total_amount)} informado.`);
  }
}

async function init() {
  const data = await loadData();
  validateData(data);
  renderSummary(data);
  renderDueDates(data.payment_rule.months);
  renderCouples(data);
  renderPeople(data);
}

init().catch((error) => {
  document.body.innerHTML = `<main class="page-shell"><section class="panel"><h1>Erro ao carregar painel</h1><p>${error.message}</p></section></main>`;
});

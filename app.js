const DATA_URL = "./data.json";

let stocks = [];
let filteredStocks = [];

const tbody = document.getElementById("stockTableBody");
const searchInput = document.getElementById("searchInput");
const signalFilter = document.getElementById("signalFilter");
const sortSelect = document.getElementById("sortSelect");

async function loadData() {
    try {
        const response = await fetch(DATA_URL + "?v=" + Date.now());

        if (!response.ok) {
            throw new Error("data.json yüklenemedi");
        }

        stocks = await response.json();

        stocks = stocks
            .filter(x => x && x.code)
            .map(x => ({
                ...x,
                score: Number(x.score || 0),
                technical: Number(x.technical || 0),
                momentum: Number(x.momentum || 0),
                flow: Number(x.flow || 0),
                relativeStrength: Number(x.relativeStrength || 0),
                riskScore: Number(x.riskScore || 0),
                rsi: Number(x.rsi || 0),
                adx: Number(x.adx || 0),
                volumeRatio: Number(x.volumeRatio || 0),
                ret21: Number(x.ret21 || 0),
                ret63: Number(x.ret63 || 0),
                ret126: Number(x.ret126 || 0),
                distance52High: Number(x.distance52High || 0)
            }));

        filteredStocks = [...stocks];

        updateSummary();
        render();

    } catch (error) {
        console.error(error);

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10">
                        Veri yüklenemedi.
                    </td>
                </tr>
            `;
        }
    }
}


// --------------------------------------------------
// RENK
// --------------------------------------------------

function scoreClass(score) {

    if (score >= 85) return "very-good";
    if (score >= 75) return "good";
    if (score >= 65) return "positive";
    if (score >= 55) return "neutral";
    if (score >= 45) return "weak";

    return "danger";
}


function signalClass(signal) {

    if (!signal) return "";

    if (signal.includes("ÇOK")) return "very-good";
    if (signal.includes("GÜÇLÜ")) return "good";
    if (signal.includes("POZİTİF")) return "positive";
    if (signal.includes("NÖTR")) return "neutral";

    return "danger";
}


// --------------------------------------------------
// SAYI
// --------------------------------------------------

function formatNumber(value, digits = 2) {

    if (!Number.isFinite(Number(value))) {
        return "-";
    }

    return Number(value).toFixed(digits);
}


function formatPercent(value) {

    const n = Number(value);

    if (!Number.isFinite(n)) {
        return "-";
    }

    const sign = n > 0 ? "+" : "";

    return `${sign}${n.toFixed(2)}%`;
}


// --------------------------------------------------
// TABLO
// --------------------------------------------------

function render() {

    if (!tbody) return;

    tbody.innerHTML = "";

    const fragment = document.createDocumentFragment();

    filteredStocks.forEach((stock, index) => {

        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>
                <strong>${index + 1}</strong>
            </td>

            <td>
                <strong>${stock.code}</strong>
                <div class="stock-name">
                    ${stock.name || ""}
                </div>
            </td>

            <td>
                ${formatNumber(stock.price)}
            </td>

            <td>
                <span class="score ${scoreClass(stock.score)}">
                    ${stock.score}
                </span>
            </td>

            <td>
                ${stock.technical}
            </td>

            <td>
                ${stock.momentum}
            </td>

            <td>
                ${stock.flow}
            </td>

            <td>
                ${stock.relativeStrength}
            </td>

            <td>
                ${stock.riskScore}
            </td>

            <td>
                <span class="signal ${signalClass(stock.signal)}">
                    ${stock.signal || "-"}
                </span>
            </td>
        `;

        tr.addEventListener("click", () => {
            showStockDetails(stock);
        });

        fragment.appendChild(tr);
    });

    tbody.appendChild(fragment);

    updateCount();
}


// --------------------------------------------------
// SIRALAMA
// --------------------------------------------------

function sortStocks() {

    const sort = sortSelect?.value || "score";

    filteredStocks.sort((a, b) => {

        switch (sort) {

            case "technical":
                return b.technical - a.technical;

            case "momentum":
                return b.momentum - a.momentum;

            case "flow":
                return b.flow - a.flow;

            case "relative":
                return b.relativeStrength - a.relativeStrength;

            case "risk":
                return b.riskScore - a.riskScore;

            case "ret21":
                return b.ret21 - a.ret21;

            case "volume":
                return b.volumeRatio - a.volumeRatio;

            case "score":
            default:
                return b.score - a.score;
        }
    });

    render();
}


// --------------------------------------------------
// FİLTRE
// --------------------------------------------------

function applyFilters() {

    const search =
        searchInput?.value
            ?.toLowerCase()
            .trim() || "";

    const signal =
        signalFilter?.value || "all";

    filteredStocks = stocks.filter(stock => {

        const matchesSearch =
            !search ||
            stock.code.toLowerCase().includes(search) ||
            (stock.name || "")
                .toLowerCase()
                .includes(search);

        let matchesSignal = true;

        if (signal === "very") {
            matchesSignal = stock.score >= 85;
        }

        if (signal === "strong") {
            matchesSignal =
                stock.score >= 75 &&
                stock.score < 85;
        }

        if (signal === "positive") {
            matchesSignal =
                stock.score >= 65 &&
                stock.score < 75;
        }

        if (signal === "neutral") {
            matchesSignal =
                stock.score >= 55 &&
                stock.score < 65;
        }

        if (signal === "weak") {
            matchesSignal = stock.score < 55;
        }

        return (
            matchesSearch &&
            matchesSignal
        );
    });

    sortStocks();
}


// --------------------------------------------------
// ÖZET
// --------------------------------------------------

function updateSummary() {

    const total =
        document.getElementById("totalStocks");

    const strong =
        document.getElementById("strongStocks");

    const positive =
        document.getElementById("positiveStocks");

    const average =
        document.getElementById("averageScore");

    if (total) {
        total.textContent = stocks.length;
    }

    if (strong) {
        strong.textContent =
            stocks.filter(x => x.score >= 75).length;
    }

    if (positive) {
        positive.textContent =
            stocks.filter(x => x.score >= 65).length;
    }

    if (average) {

        const avg =
            stocks.length
                ? stocks.reduce(
                    (sum, x) => sum + x.score,
                    0
                ) / stocks.length
                : 0;

        average.textContent =
            avg.toFixed(1);
    }
}


// --------------------------------------------------
// DETAY PANELİ
// --------------------------------------------------

function showStockDetails(stock) {

    let modal =
        document.getElementById("stockModal");

    if (!modal) {

        modal =
            document.createElement("div");

        modal.id = "stockModal";

        modal.className = "stock-modal";

        document.body.appendChild(modal);
    }

    modal.innerHTML = `

        <div class="stock-modal-content">

            <button
                class="modal-close"
                onclick="closeStockDetails()">
                ×
            </button>

            <h2>
                ${stock.code}
            </h2>

            <p class="modal-company">
                ${stock.name || ""}
            </p>

            <div class="big-score ${scoreClass(stock.score)}">
                ${stock.score}
            </div>

            <div class="modal-signal">
                ${stock.signal || "-"}
            </div>

            <div class="detail-grid">

                <div>
                    <span>Fiyat</span>
                    <strong>${formatNumber(stock.price)} ₺</strong>
                </div>

                <div>
                    <span>Teknik</span>
                    <strong>${stock.technical}</strong>
                </div>

                <div>
                    <span>Momentum</span>
                    <strong>${stock.momentum}</strong>
                </div>

                <div>
                    <span>Para Akışı</span>
                    <strong>${stock.flow}</strong>
                </div>

                <div>
                    <span>Relatif Güç</span>
                    <strong>${stock.relativeStrength}</strong>
                </div>

                <div>
                    <span>Risk</span>
                    <strong>${stock.riskScore}</strong>
                </div>

                <div>
                    <span>RSI</span>
                    <strong>${formatNumber(stock.rsi)}</strong>
                </div>

                <div>
                    <span>ADX</span>
                    <strong>${formatNumber(stock.adx)}</strong>
                </div>

                <div>
                    <span>Hacim</span>
                    <strong>${formatNumber(stock.volumeRatio)}x</strong>
                </div>

                <div>
                    <span>21 Gün</span>
                    <strong>${formatPercent(stock.ret21)}</strong>
                </div>

                <div>
                    <span>3 Ay</span>
                    <strong>${formatPercent(stock.ret63)}</strong>
                </div>

                <div>
                    <span>6 Ay</span>
                    <strong>${formatPercent(stock.ret126)}</strong>
                </div>

                <div>
                    <span>52H Zirve</span>
                    <strong>${formatNumber(stock.distance52High)}%</strong>
                </div>

            </div>

        </div>
    `;

    modal.style.display = "flex";
}


function closeStockDetails() {

    const modal =
        document.getElementById("stockModal");

    if (modal) {
        modal.style.display = "none";
    }
}


// --------------------------------------------------
// SAYI
// --------------------------------------------------

function updateCount() {

    const element =
        document.getElementById("stockCount");

    if (element) {
        element.textContent =
            `${filteredStocks.length} hisse`;
    }
}


// --------------------------------------------------
// EVENTLER
// --------------------------------------------------

if (searchInput) {

    searchInput.addEventListener(
        "input",
        applyFilters
    );
}

if (signalFilter) {

    signalFilter.addEventListener(
        "change",
        applyFilters
    );
}

if (sortSelect) {

    sortSelect.addEventListener(
        "change",
        sortStocks
    );
}


// --------------------------------------------------
// BAŞLAT
// --------------------------------------------------

loadData();

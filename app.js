const DATA_URL = "./data.json";

let stocks = [];
let filteredStocks = [];

const tbody = document.getElementById("stockTableBody");
const searchInput = document.getElementById("searchInput");
const signalFilter = document.getElementById("signalFilter");
const sortSelect = document.getElementById("sortSelect");


// ==================================================
// VERİ
// ==================================================

async function loadData() {

    try {

        const response =
            await fetch(DATA_URL + "?v=" + Date.now());

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

                distance52High:
                    Number(x.distance52High || 0),

                // ==============================
                // MaT-R
                // ==============================

                matrSignal:
                    x.matrSignal || "BEKLE",

                matrEntry:
                    Number(x.matrEntry || 0),

                matrTP1:
                    Number(x.matrTP1 || 0),

                matrTP2:
                    Number(x.matrTP2 || 0),

                matrSL:
                    Number(x.matrSL || 0),

                matrATR:
                    Number(x.matrATR || 0),

                matrEMA34:
                    Number(x.matrEMA34 || 0),

                matrSMA34:
                    Number(x.matrSMA34 || 0),

                matrMACD:
                    Number(x.matrMACD || 0),

                matrSignalLine:
                    Number(x.matrSignalLine || 0),

                matrTrend:
                    x.matrTrend || "-"

            }));


        filteredStocks = [...stocks];

        updateSummary();

        updateTableHeaders();

        render();

    }
    catch (error) {

        console.error(error);

        if (tbody) {

            tbody.innerHTML = `
                <tr>
                    <td colspan="20">
                        Veri yüklenemedi.
                    </td>
                </tr>
            `;
        }
    }
}


// ==================================================
// TABLO BAŞLIKLARI
// ==================================================

function updateTableHeaders() {

    const table =
        document.querySelector("#stockTableBody")?.closest("table");

    if (!table) return;

    const header =
        table.querySelector("thead tr");

    if (!header) return;

    // Daha önce eklenmişse tekrar ekleme
    if (header.querySelector(".matr-header")) {
        return;
    }

    const th =
        document.createElement("th");

    th.className = "matr-header";

    th.textContent = "MaT-R";

    header.appendChild(th);
}


// ==================================================
// RENK
// ==================================================

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

    if (signal.includes("ÇOK")) {
        return "very-good";
    }

    if (signal.includes("GÜÇLÜ")) {
        return "good";
    }

    if (signal.includes("POZİTİF")) {
        return "positive";
    }

    if (signal.includes("NÖTR")) {
        return "neutral";
    }

    return "danger";
}


// ==================================================
// MaT-R RENK
// ==================================================

function matrClass(signal) {

    if (signal === "AL") {
        return "good";
    }

    if (signal === "BEKLE") {
        return "neutral";
    }

    if (signal === "SAT") {
        return "danger";
    }

    return "neutral";
}


// ==================================================
// SAYI
// ==================================================

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


// ==================================================
// TABLO
// ==================================================

function render() {

    if (!tbody) return;

    tbody.innerHTML = "";

    const fragment =
        document.createDocumentFragment();


    filteredStocks.forEach((stock, index) => {

        const tr =
            document.createElement("tr");


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


            <!-- MaT-R -->

            <td>

                <span class="signal ${matrClass(stock.matrSignal)}">
                    ${stock.matrSignal}
                </span>

            </td>

        `;


        tr.addEventListener(
            "click",
            () => showStockDetails(stock)
        );


        fragment.appendChild(tr);

    });


    tbody.appendChild(fragment);

    updateCount();
}


// ==================================================
// SIRALAMA
// ==================================================

function sortStocks() {

    const sort =
        sortSelect?.value || "score";


    filteredStocks.sort((a, b) => {

        switch (sort) {

            case "technical":
                return b.technical - a.technical;

            case "momentum":
                return b.momentum - a.momentum;

            case "flow":
                return b.flow - a.flow;

            case "relative":
                return b.relativeStrength -
                       a.relativeStrength;

            case "risk":
                return b.riskScore -
                       a.riskScore;

            case "ret21":
                return b.ret21 - a.ret21;

            case "volume":
                return b.volumeRatio -
                       a.volumeRatio;

            case "matr":

                return (
                    (b.matrSignal === "AL" ? 1 : 0) -
                    (a.matrSignal === "AL" ? 1 : 0)
                );

            case "score":
            default:
                return b.score - a.score;
        }

    });


    render();
}


// ==================================================
// FİLTRE
// ==================================================

function applyFilters() {

    const search =
        searchInput?.value
            ?.toLowerCase()
            .trim() || "";


    const signal =
        signalFilter?.value || "all";


    filteredStocks =
        stocks.filter(stock => {


            const matchesSearch =

                !search ||

                stock.code
                    .toLowerCase()
                    .includes(search) ||

                (stock.name || "")
                    .toLowerCase()
                    .includes(search);


            let matchesSignal = true;


            if (signal === "very") {

                matchesSignal =
                    stock.score >= 85;

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

                matchesSignal =
                    stock.score < 55;

            }


            return (
                matchesSearch &&
                matchesSignal
            );

        });


    sortStocks();
}


// ==================================================
// ÖZET
// ==================================================

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

        total.textContent =
            stocks.length;

    }


    if (strong) {

        strong.textContent =
            stocks.filter(
                x => x.score >= 75
            ).length;

    }


    if (positive) {

        positive.textContent =
            stocks.filter(
                x => x.score >= 65
            ).length;

    }


    if (average) {

        const avg =
            stocks.length

                ? stocks.reduce(
                    (sum, x) =>
                        sum + x.score,
                    0
                ) / stocks.length

                : 0;


        average.textContent =
            avg.toFixed(1);
    }
}


// ==================================================
// DETAY PANELİ
// ==================================================

function showStockDetails(stock) {

    let modal =
        document.getElementById("stockModal");


    if (!modal) {

        modal =
            document.createElement("div");

        modal.id =
            "stockModal";

        modal.className =
            "stock-modal";

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


            <!-- ==========================
                 MaT-R
                 ========================== -->

            <div class="matr-panel">

                <h3>
                    MaT-R Stratejisi
                </h3>


                <div class="matr-main">

                    <span class="signal ${matrClass(stock.matrSignal)}">

                        ${stock.matrSignal}

                    </span>


                    <strong>
                        Trend: ${stock.matrTrend}
                    </strong>

                </div>


                <div class="detail-grid">

                    <div>
                        <span>Giriş</span>
                        <strong>
                            ${stock.matrEntry
                                ? formatNumber(stock.matrEntry) + " ₺"
                                : "-"
                            }
                        </strong>
                    </div>


                    <div>
                        <span>Kar 1 %12</span>
                        <strong>
                            ${stock.matrTP1
                                ? formatNumber(stock.matrTP1) + " ₺"
                                : "-"
                            }
                        </strong>
                    </div>


                    <div>
                        <span>Kar 2 %20</span>
                        <strong>
                            ${stock.matrTP2
                                ? formatNumber(stock.matrTP2) + " ₺"
                                : "-"
                            }
                        </strong>
                    </div>


                    <div>
                        <span>Zarar Kes</span>
                        <strong>
                            ${stock.matrSL
                                ? formatNumber(stock.matrSL) + " ₺"
                                : "-"
                            }
                        </strong>
                    </div>


                    <div>
                        <span>ATR 17</span>
                        <strong>
                            ${formatNumber(stock.matrATR)}
                        </strong>
                    </div>


                    <div>
                        <span>EMA 34</span>
                        <strong>
                            ${formatNumber(stock.matrEMA34)}
                        </strong>
                    </div>


                    <div>
                        <span>SMA 34</span>
                        <strong>
                            ${formatNumber(stock.matrSMA34)}
                        </strong>
                    </div>


                    <div>
                        <span>MACD</span>
                        <strong>
                            ${formatNumber(stock.matrMACD, 4)}
                        </strong>
                    </div>


                    <div>
                        <span>Sinyal Çizgisi</span>
                        <strong>
                            ${formatNumber(
                                stock.matrSignalLine,
                                4
                            )}
                        </strong>
                    </div>

                </div>

            </div>


            <!-- ==========================
                 GENEL ANALİZ
                 ========================== -->

            <h3>
                Genel Analiz
            </h3>


            <div class="detail-grid">


                <div>
                    <span>Fiyat</span>

                    <strong>
                        ${formatNumber(stock.price)} ₺
                    </strong>
                </div>


                <div>
                    <span>Teknik</span>

                    <strong>
                        ${stock.technical}
                    </strong>
                </div>


                <div>
                    <span>Momentum</span>

                    <strong>
                        ${stock.momentum}
                    </strong>
                </div>


                <div>
                    <span>Para Akışı</span>

                    <strong>
                        ${stock.flow}
                    </strong>
                </div>


                <div>
                    <span>Relatif Güç</span>

                    <strong>
                        ${stock.relativeStrength}
                    </strong>
                </div>


                <div>
                    <span>Risk</span>

                    <strong>
                        ${stock.riskScore}
                    </strong>
                </div>


                <div>
                    <span>RSI</span>

                    <strong>
                        ${formatNumber(stock.rsi)}
                    </strong>
                </div>


                <div>
                    <span>ADX</span>

                    <strong>
                        ${formatNumber(stock.adx)}
                    </strong>
                </div>


                <div>
                    <span>Hacim</span>

                    <strong>
                        ${formatNumber(stock.volumeRatio)}x
                    </strong>
                </div>


                <div>
                    <span>21 Gün</span>

                    <strong>
                        ${formatPercent(stock.ret21)}
                    </strong>
                </div>


                <div>
                    <span>3 Ay</span>

                    <strong>
                        ${formatPercent(stock.ret63)}
                    </strong>
                </div>


                <div>
                    <span>6 Ay</span>

                    <strong>
                        ${formatPercent(stock.ret126)}
                    </strong>
                </div>


                <div>
                    <span>52H Zirve</span>

                    <strong>
                        ${formatNumber(stock.distance52High)}%
                    </strong>
                </div>


            </div>

        </div>

    `;


    modal.style.display =
        "flex";
}


function closeStockDetails() {

    const modal =
        document.getElementById("stockModal");


    if (modal) {

        modal.style.display =
            "none";

    }
}


// ==================================================
// SAYI
// ==================================================

function updateCount() {

    const element =
        document.getElementById("stockCount");


    if (element) {

        element.textContent =
            `${filteredStocks.length} hisse`;

    }
}


// ==================================================
// EVENTLER
// ==================================================

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


// ==================================================
// BAŞLAT
// ==================================================

loadData();

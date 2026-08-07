let DATA = [];

function sig(s) {
    return s >= 70 ? "GÜÇLÜ" : s >= 55 ? "İZLE" : s >= 40 ? "NÖTR" : "ZAYIF";
}

function fmt(n, d = 2) {
    return Number(n).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function render() {
    const q = document.querySelector("#search").value.toUpperCase().trim();
    const sg = document.querySelector("#signal").value;
    const so = document.querySelector("#sort").value;

    let rows = DATA.map(x => ({
        code: x.code,
        price: x.price,
        day: x.day || 0,
        ret21: x.ret21,
        rsi: x.rsi,
        volume: x.volumeRatio,
        score: x.score,
        signal: sig(x.score)
    })).filter(x => (!q || x.code.includes(q)) && (!sg || x.signal === sg));

    rows.sort((a, b) => 
        so === "ret21" ? b.ret21 - a.ret21 : 
        so === "volume" ? b.volume - a.volume : 
        so === "rsi" ? b.rsi - a.rsi : 
        b.score - a.score
    );

    document.querySelector("#tbody").innerHTML = rows.map(x => `
        <tr class="click">
            <td>${x.code}</td>
            <td>${fmt(x.price)} TL</td>
            <td class="${x.day >= 0 ? "pos" : "neg"}">${x.day >= 0 ? "+" : ""}${fmt(x.day)}%</td>
            <td class="${x.ret21 >= 0 ? "pos" : "neg"}">${x.ret21 >= 0 ? "+" : ""}${fmt(x.ret21)}%</td>
            <td>${fmt(x.rsi, 1)}</td>
            <td>${fmt(x.volume, 2)}x</td>
            <td class="score">${x.score}</td>
            <td><span class="badge ${x.signal === "GÜÇLÜ" ? "guc" : x.signal === "İZLE" ? "izle" : x.signal === "NÖTR" ? "notr" : "zayif"}">${x.signal}</span></td>
        </tr>
    `).join("");

    document.querySelector("#count").textContent = rows.length;
    document.querySelector("#strong").textContent = rows.filter(x => x.signal === "GÜÇLÜ").length;
    document.querySelector("#watch").textContent = rows.filter(x => x.signal === "İZLE").length;
    document.querySelector("#avg").textContent = rows.length ? Math.round(rows.reduce((a, b) => a + b.score, 0) / rows.length) : 0;
    
    const best = [...rows].sort((a, b) => b.ret21 - a.ret21)[0];
    document.querySelector("#best21").textContent = best ? best.code + " " + (best.ret21 >= 0 ? "+" : "") + fmt(best.ret21) + "%" : "-";
}

document.addEventListener("DOMContentLoaded", () => {
    // data.json dosyasından canlı BIST verisini çek
    fetch("data.json")
        .then(res => {
            if (!res.ok) throw new Error("JSON dosyası bulunamadı");
            return res.json();
        })
        .then(data => {
            DATA = data; // Arka planda taranan tüm hisseleri ata
            document.getElementById("updated").textContent = "Canlı Veri • " + new Date().toLocaleDateString("tr-TR");
            render();
        })
        .catch(err => {
            console.error("Veri yükleme hatası:", err);
            document.getElementById("updated").textContent = "Veri okuma hatası (data.json)";
        });

    ["search", "signal", "sort"].forEach(id => document.getElementById(id).addEventListener("input", render));
});

const DATA=[
["ASELS",128.4,1.72,12.8,64.2,1.58,86],
["FROTO",152.7,0.84,8.9,61.4,1.31,82],
["TCELL",168.1,0.55,6.7,58.7,1.16,78],
["TURSG",6.21,0.32,5.9,57.2,1.24,77],
["GWIND",24.02,-0.48,4.2,55.1,1.41,74],
["HTTBT",38.35,1.05,3.8,62.5,1.08,72],
["DOAS",190.4,-0.31,2.2,51.8,1.19,68],
["ENTRA",4.79,0.21,1.9,54.4,1.03,64],
["ALGYO",3.35,-0.62,-1.7,46.9,1.27,58],
["AYEN",34.05,0.44,-2.1,48.8,0.92,55],
["GOODY",2.57,-1.18,-4.8,42.1,1.11,43],
["SKTAS",3.17,-0.95,-6.4,39.8,0.88,36],
["TRILC",1.21,-1.63,-8.7,34.6,1.03,29]
];
function sig(s){return s>=70?"GÜÇLÜ":s>=55?"İZLE":s>=40?"NÖTR":"ZAYIF"}
function fmt(n,d=2){return Number(n).toLocaleString("tr-TR",{minimumFractionDigits:d,maximumFractionDigits:d})}
function render(){
 const q=document.querySelector("#search").value.toUpperCase().trim(), sg=document.querySelector("#signal").value, so=document.querySelector("#sort").value;
 let rows=DATA.map(x=>({code:x[0],price:x[1],day:x[2],ret21:x[3],rsi:x[4],volume:x[5],score:x[6],signal:sig(x[6])}))
 .filter(x=>(!q||x.code.includes(q))&&(!sg||x.signal===sg));
 rows.sort((a,b)=>so==="ret21"?b.ret21-a.ret21:so==="volume"?b.volume-a.volume:so==="rsi"?b.rsi-a.rsi:b.score-a.score);
 document.querySelector("#tbody").innerHTML=rows.map(x=>`<tr class="click"><td>${x.code}</td><td>${fmt(x.price)}</td><td class="${x.day>=0?"pos":"neg"}">${x.day>=0?"+":""}${fmt(x.day)}%</td><td class="${x.ret21>=0?"pos":"neg"}">${x.ret21>=0?"+":""}${fmt(x.ret21)}%</td><td>${fmt(x.rsi,1)}</td><td>${fmt(x.volume,2)}x</td><td class="score">${x.score}</td><td><span class="badge ${x.signal==="GÜÇLÜ"?"guc":x.signal==="İZLE"?"izle":x.signal==="NÖTR"?"notr":"zayif"}">${x.signal}</span></td></tr>`).join("");
 document.querySelector("#count").textContent=rows.length;
 document.querySelector("#strong").textContent=rows.filter(x=>x.signal==="GÜÇLÜ").length;
 document.querySelector("#watch").textContent=rows.filter(x=>x.signal==="İZLE").length;
 document.querySelector("#avg").textContent=rows.length?Math.round(rows.reduce((a,b)=>a+b.score,0)/rows.length):0;
 const best=[...rows].sort((a,b)=>b.ret21-a.ret21)[0]; document.querySelector("#best21").textContent=best?best.code+" "+(best.ret21>=0?"+":"")+fmt(best.ret21)+"%":"-";
}
["search","signal","sort"].forEach(id=>document.getElementById(id).addEventListener("input",render));
document.getElementById("updated").textContent="Demo veri • "+new Date().toLocaleDateString("tr-TR");
render();
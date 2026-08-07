import io
import json
import time
import math
import requests
import numpy as np
import pandas as pd
import yfinance as yf

SYMBOL_URL = "https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/bist.csv"
BATCH_SIZE = 25


def get_symbols():
    r = requests.get(SYMBOL_URL, timeout=30)
    r.raise_for_status()

    df = pd.read_csv(io.StringIO(r.text))

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
        .str.replace(r"[^A-Z0-9]", "", regex=True)
    )

    df = df[
        df["symbol"].str.len().between(2, 6)
    ].drop_duplicates("symbol")

    return dict(zip(df["symbol"], df["name"]))


def num(x, default=0.0):
    try:
        x = float(x)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def clip(x, lo=0, hi=100):
    return int(round(max(lo, min(hi, num(x, lo)))))


def pct_change(c, n):
    if len(c) <= n:
        return 0.0

    try:
        return num((c.iloc[-1] / c.iloc[-n - 1] - 1) * 100)
    except Exception:
        return 0.0


# ---------------------------------------------------------
# RSI
# ---------------------------------------------------------
def rsi(c, n=14):
    d = c.diff()

    gain = d.clip(lower=0).ewm(
        alpha=1 / n,
        adjust=False
    ).mean()

    loss = (-d.clip(upper=0)).ewm(
        alpha=1 / n,
        adjust=False
    ).mean()

    rs = gain / loss.replace(0, np.nan)

    result = 100 - 100 / (1 + rs)

    return (
        result
        .replace([np.inf, -np.inf], np.nan)
        .fillna(50)
    )


# ---------------------------------------------------------
# ATR
# ---------------------------------------------------------
def atr(d, n=14):
    h = d["High"]
    l = d["Low"]
    c = d["Close"]

    previous_close = c.shift(1)

    tr = pd.concat(
        [
            h - l,
            (h - previous_close).abs(),
            (l - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / n,
        adjust=False
    ).mean()


# ---------------------------------------------------------
# ADX
# ---------------------------------------------------------
def adx(d, n=14):

    h = d["High"]
    l = d["Low"]
    c = d["Close"]

    up = h.diff()
    down = -l.diff()

    plus = up.where(
        (up > down) & (up > 0),
        0.0
    )

    minus = down.where(
        (down > up) & (down > 0),
        0.0
    )

    previous_close = c.shift(1)

    tr = pd.concat(
        [
            h - l,
            (h - previous_close).abs(),
            (l - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr_value = tr.ewm(
        alpha=1 / n,
        adjust=False
    ).mean().replace(0, np.nan)

    plus_di = (
        100
        * plus.ewm(alpha=1 / n, adjust=False).mean()
        / atr_value
    )

    minus_di = (
        100
        * minus.ewm(alpha=1 / n, adjust=False).mean()
        / atr_value
    )

    dx = (
        100
        * (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
    )

    return (
        dx.ewm(alpha=1 / n, adjust=False)
        .mean()
        .fillna(0)
    )


# ---------------------------------------------------------
# OBV
# ---------------------------------------------------------
def obv(c, v):
    direction = np.sign(c.diff()).fillna(0)
    return (direction * v).cumsum()


# ---------------------------------------------------------
# Trend eğimi
# ---------------------------------------------------------
def slope_score(series, lookback=20):

    s = pd.to_numeric(
        series,
        errors="coerce"
    ).dropna()

    if len(s) < lookback + 5:
        return 50

    y = s.iloc[-lookback:].values
    x = np.arange(len(y))

    slope = np.polyfit(x, y, 1)[0]

    base = abs(np.mean(y))

    if base == 0:
        return 50

    relative_slope = slope / base * 100

    return clip(
        50 + relative_slope * 35
    )


# =========================================================
# ANA SKOR MOTORU
# =========================================================
def score(sym, name, d):

    required = {
        "Close",
        "High",
        "Low",
        "Volume"
    }

    if (
        d is None
        or d.empty
        or not required.issubset(d.columns)
    ):
        return None

    d = d.copy()

    for col in required:
        d[col] = pd.to_numeric(
            d[col],
            errors="coerce"
        )

    d = d.dropna(
        subset=[
            "Close",
            "High",
            "Low"
        ]
    )

    if len(d) < 220:
        return None

    c = d["Close"]
    h = d["High"]
    l = d["Low"]
    v = d["Volume"]

    price = num(c.iloc[-1])

    # -----------------------------------------------------
    # HAREKETLİ ORTALAMALAR
    # -----------------------------------------------------
    e20 = c.ewm(
        span=20,
        adjust=False
    ).mean()

    e50 = c.ewm(
        span=50,
        adjust=False
    ).mean()

    m50 = c.rolling(50).mean()
    m200 = c.rolling(200).mean()

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------
    rsi_value = num(
        rsi(c).iloc[-1],
        50
    )

    # -----------------------------------------------------
    # MACD
    # -----------------------------------------------------
    e12 = c.ewm(
        span=12,
        adjust=False
    ).mean()

    e26 = c.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = e12 - e26

    signal_line = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    macd_hist = num(
        macd.iloc[-1] -
        signal_line.iloc[-1]
    )

    # -----------------------------------------------------
    # ADX
    # -----------------------------------------------------
    adx_value = num(
        adx(d).iloc[-1],
        0
    )

    # -----------------------------------------------------
    # GETİRİLER
    # -----------------------------------------------------
    ret5 = pct_change(c, 5)
    ret21 = pct_change(c, 21)
    ret63 = pct_change(c, 63)

    # -----------------------------------------------------
    # HACİM
    # -----------------------------------------------------
    volume_average = num(
        v.rolling(20).mean().iloc[-1],
        1
    )

    if volume_average > 0:
        volume_ratio = num(
            v.iloc[-1] / volume_average,
            1
        )
    else:
        volume_ratio = 1

    # -----------------------------------------------------
    # ATR
    # -----------------------------------------------------
    atr_value = num(
        atr(d).iloc[-1]
    )

    atr_pct = (
        atr_value / price * 100
        if price > 0
        else 0
    )

    # -----------------------------------------------------
    # VOLATİLİTE
    # -----------------------------------------------------
    volatility = num(
        c.pct_change()
        .rolling(20)
        .std()
        .iloc[-1]
        * np.sqrt(252)
        * 100
    )

    # -----------------------------------------------------
    # KIRILIM
    # -----------------------------------------------------
    high20 = num(
        c.iloc[-21:-1].max(),
        price
    )

    high60 = num(
        c.iloc[-61:-1].max(),
        price
    )

    breakout20 = (
        price >= high20 * 0.995
        if high20
        else False
    )

    breakout60 = (
        price >= high60 * 0.995
        if high60
        else False
    )

    # -----------------------------------------------------
    # 60 GÜNLÜK ZİRVE
    # -----------------------------------------------------
    peak60 = num(
        c.rolling(60).max().iloc[-1],
        price
    )

    drawdown60 = (
        (price / peak60 - 1) * 100
        if peak60
        else 0
    )

    # -----------------------------------------------------
    # OBV
    # -----------------------------------------------------
    obv_series = obv(c, v)

    obv_score = slope_score(
        obv_series,
        20
    )

    # -----------------------------------------------------
    # POZİTİF GÜN ORANI
    # -----------------------------------------------------
    daily_returns = (
        c.pct_change()
        .dropna()
    )

    positive_days = num(
        (
            daily_returns.tail(20) > 0
        ).mean() * 100,
        50
    )

    # =====================================================
    # 1 — TREND
    # =====================================================
    trend = 0

    trend += (
        18
        if price > e20.iloc[-1]
        else 5
    )

    trend += (
        16
        if e20.iloc[-1] > e50.iloc[-1]
        else 5
    )

    trend += (
        16
        if m50.iloc[-1] > m200.iloc[-1]
        else 5
    )

    trend += (
        12
        if price > m200.iloc[-1]
        else 3
    )

    trend += (
        10
        if adx_value >= 25
        else 7
        if adx_value >= 18
        else 3
    )

    trend += (
        10
        if macd.iloc[-1] > signal_line.iloc[-1]
        else 4
    )

    trend += (
        8
        if macd_hist > 0
        else 3
    )

    trend += (
        10
        if slope_score(e20, 20) >= 55
        else 3
    )

    technical = clip(trend)

    # =====================================================
    # 2 — MOMENTUM
    # =====================================================
    momentum = 0

    momentum += np.interp(
        ret5,
        [-6, -1, 1, 3, 6],
        [0, 4, 8, 12, 16]
    )

    momentum += np.interp(
        ret21,
        [-15, -3, 3, 8, 18],
        [0, 5, 10, 15, 20]
    )

    momentum += np.interp(
        ret63,
        [-25, -5, 5, 15, 35],
        [0, 5, 10, 15, 20]
    )

    # RSI
    if 52 <= rsi_value <= 68:
        momentum += 12
    elif 45 <= rsi_value < 52:
        momentum += 9
    elif 68 < rsi_value <= 74:
        momentum += 9
    elif 40 <= rsi_value < 45:
        momentum += 5
    elif 74 < rsi_value <= 78:
        momentum += 5
    else:
        momentum += 2

    momentum = clip(momentum)

    # =====================================================
    # 3 — HACİM / PARA AKIŞI
    # =====================================================
    flow = 50

    flow += (
        volume_ratio - 1
    ) * 28

    flow += max(
        0,
        ret5
    ) * 1.2

    flow += (
        obv_score - 50
    ) * 0.20

    if (
        breakout20
        and volume_ratio >= 1.20
    ):
        flow += 10

    flow = clip(flow)

    # =====================================================
    # 4 — KIRILIM SKORU
    # =====================================================
    breakout = 0

    breakout += (
        40 if breakout20 else 8
    )

    breakout += (
        25 if breakout60 else 5
    )

    breakout += (
        20
        if volume_ratio >= 1.20
        else 10
        if volume_ratio >= 1
        else 3
    )

    breakout += (
        15
        if (
            price > e20.iloc[-1]
            and e20.iloc[-1] > e50.iloc[-1]
        )
        else 5
    )

    breakout = clip(breakout)

    # =====================================================
    # 5 — RİSK
    # =====================================================
    risk = 100

    risk -= max(
        0,
        volatility - 18
    ) * 2

    risk -= max(
        0,
        atr_pct - 4
    ) * 4

    risk -= max(
        0,
        -drawdown60 - 12
    ) * 1.5

    risk = clip(
        risk,
        20,
        100
    )

    # =====================================================
    # 6 — İSTİKRAR
    # =====================================================
    stability = (
        positive_days * 0.55
        + (
            50
            if 8 <= volatility <= 28
            else 35
        )
        + (
            15
            if adx_value >= 20
            else 5
        )
    )

    stability = clip(
        stability / 1.2
    )

    # -----------------------------------------------------
    # Temel/KAP verisi henüz harici kaynaktan alınmadığı
    # için sahte avantaj oluşturmamak adına nötr.
    # -----------------------------------------------------
    fundamental = 50
    valuation = 50
    kap = 50

    # =====================================================
    # ANA SKOR
    # =====================================================
    total = (
        technical * 0.30
        + momentum * 0.23
        + flow * 0.15
        + breakout * 0.10
        + risk * 0.10
        + stability * 0.07
        + fundamental * 0.025
        + valuation * 0.025
    )

    total = clip(total)

    # =====================================================
    # SİNYAL
    # =====================================================
    if total >= 75:
        signal = "GÜÇLÜ"
    elif total >= 60:
        signal = "İZLE"
    elif total >= 45:
        signal = "NÖTR"
    else:
        signal = "ZAYIF"

    return {
        "code": sym,
        "name": name,
        "price": round(price, 2),

        "technical": technical,
        "momentum": momentum,

        "fundamental": fundamental,
        "valuation": valuation,
        "kap": kap,

        "flow": flow,
        "breakoutScore": breakout,
        "stability": stability,
        "riskScore": risk,

        "score": total,
        "signal": signal,

        "ret5": round(ret5, 2),
        "ret21": round(ret21, 2),
        "ret63": round(ret63, 2),

        "volumeRatio": round(
            volume_ratio,
            2
        ),

        "rsi": round(
            rsi_value,
            2
        ),

        "adx": round(
            adx_value,
            2
        ),

        "atrPct": round(
            atr_pct,
            2
        ),

        "volatility": round(
            volatility,
            2
        ),

        "drawdown60": round(
            drawdown60,
            2
        ),

        "positiveDays20": round(
            positive_days,
            1
        ),

        "breakout20": breakout20,
        "breakout60": breakout60
    }


# =========================================================
# VERİ GÜNCELLEME
# =========================================================
def main():

    names = get_symbols()
    syms = list(names)

    print(
        "BIST sembol sayısı:",
        len(syms)
    )

    out = []
    failed = []

    for i in range(
        0,
        len(syms),
        BATCH_SIZE
    ):

        batch = syms[
            i:i + BATCH_SIZE
        ]

        print(
            f"[{i + 1}-{i + len(batch)} / {len(syms)}]"
        )

        try:

            raw = yf.download(
                [
                    s + ".IS"
                    for s in batch
                ],
                period="1y",
                interval="1d",
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=30
            )

        except Exception as e:

            print(
                "BATCH ERROR:",
                e
            )

            raw = None

        for s in batch:

            try:

                d = None
                ticker = s + ".IS"

                if (
                    raw is not None
                    and not raw.empty
                    and isinstance(
                        raw.columns,
                        pd.MultiIndex
                    )
                ):

                    if (
                        ticker
                        in raw.columns.get_level_values(0)
                    ):

                        d = raw[
                            ticker
                        ].copy()

                    elif (
                        ticker
                        in raw.columns.get_level_values(1)
                    ):

                        d = raw.xs(
                            ticker,
                            axis=1,
                            level=1
                        ).copy()

                x = score(
                    s,
                    names[s],
                    d
                )

                if x:
                    out.append(x)
                else:
                    failed.append(s)

            except Exception as e:

                print(
                    "SKIP",
                    s,
                    e
                )

                failed.append(s)

        time.sleep(1)

    # -----------------------------------------------------
    # SKOR SIRALAMASI
    # -----------------------------------------------------
    out.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # -----------------------------------------------------
    # JSON
    # -----------------------------------------------------
    with open(
        "data.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            out,
            f,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )

    print(
        "BAŞARILI:",
        len(out)
    )

    print(
        "VERİ YOK:",
        len(failed)
    )

    print(
        "İLK 20:",
        [
            x["code"]
            for x in out[:20]
        ]
    )

    # -----------------------------------------------------
    # GÜÇLÜ HİSSELER
    # -----------------------------------------------------
    strong = [
        x for x in out
        if x["score"] >= 75
    ]

    print(
        "GÜÇLÜ SİNYAL:",
        len(strong)
    )

    print(
        "GÜÇLÜ İLK 20:",
        [
            x["code"]
            for x in strong[:20]
        ]
    )

    # Güvenlik kontrolü
    if len(out) < 400:

        raise RuntimeError(
            f"Çok az hisse döndü: {len(out)}"
        )


if __name__ == "__main__":
    main()

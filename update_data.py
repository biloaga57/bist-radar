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


def safe(value, default=0.0):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

        return default

    except Exception:
        return default


def clamp(value, minimum=0, maximum=100):
    return int(
        max(
            minimum,
            min(
                maximum,
                round(safe(value))
            )
        )
    )


# ---------------------------------------------------------
# RSI
# ---------------------------------------------------------

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    result = 100 - (
        100 / (1 + rs)
    )

    return result.fillna(50)


# ---------------------------------------------------------
# ADX
# ---------------------------------------------------------

def calculate_adx(high, low, close, period=14):

    up_move = high.diff()

    down_move = -low.diff()

    plus_dm = up_move.where(
        (up_move > down_move) &
        (up_move > 0),
        0
    )

    minus_dm = down_move.where(
        (down_move > up_move) &
        (down_move > 0),
        0
    )

    previous_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    plus_di = (
        100 *
        plus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        / atr.replace(0, np.nan)
    )

    minus_di = (
        100 *
        minus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean()
        / atr.replace(0, np.nan)
    )

    dx = (
        100 *
        (plus_di - minus_di).abs()
        /
        (plus_di + minus_di).replace(0, np.nan)
    )

    return dx.ewm(
        alpha=1 / period,
        adjust=False
    ).mean().fillna(0)


# ---------------------------------------------------------
# ANA SKOR MOTORU
# ---------------------------------------------------------

def score_stock(sym, name, d):

    if d is None or d.empty:
        return None

    required = {
        "Close",
        "High",
        "Low",
        "Volume"
    }

    if not required.issubset(d.columns):
        return None

    close = pd.to_numeric(
        d["Close"],
        errors="coerce"
    )

    high = pd.to_numeric(
        d["High"],
        errors="coerce"
    )

    low = pd.to_numeric(
        d["Low"],
        errors="coerce"
    )

    volume = pd.to_numeric(
        d["Volume"],
        errors="coerce"
    ).fillna(0)

    valid = close.notna()

    close = close[valid]
    high = high[valid]
    low = low[valid]
    volume = volume[valid]

    # En az yaklaşık 1 yıllık veri
    if len(close) < 220:
        return None

    price = safe(close.iloc[-1])

    # -----------------------------------------------------
    # ORTALAMALAR
    # -----------------------------------------------------

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()
    sma200 = close.rolling(200).mean()

    ema20 = close.ewm(
        span=20,
        adjust=False
    ).mean()

    ema50 = close.ewm(
        span=50,
        adjust=False
    ).mean()

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    rsi_series = calculate_rsi(close)
    rsi = safe(rsi_series.iloc[-1], 50)

    # -----------------------------------------------------
    # MACD
    # -----------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    macd_signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    macd_histogram = (
        macd.iloc[-1] -
        macd_signal.iloc[-1]
    )

    # -----------------------------------------------------
    # ADX
    # -----------------------------------------------------

    adx_series = calculate_adx(
        high,
        low,
        close
    )

    adx = safe(
        adx_series.iloc[-1],
        0
    )

    # -----------------------------------------------------
    # MOMENTUM
    # -----------------------------------------------------

    ret5 = safe(
        (price / close.iloc[-6] - 1) * 100
    )

    ret21 = safe(
        (price / close.iloc[-22] - 1) * 100
    )

    ret63 = safe(
        (price / close.iloc[-64] - 1) * 100
    )

    ret126 = safe(
        (price / close.iloc[-127] - 1) * 100
    )

    # -----------------------------------------------------
    # 52 HAFTALIK KONUM
    # -----------------------------------------------------

    high252 = safe(
        close.tail(252).max()
    )

    low252 = safe(
        close.tail(252).min()
    )

    distance_high = (
        (price / high252 - 1) * 100
        if high252 > 0
        else 0
    )

    distance_low = (
        (price / low252 - 1) * 100
        if low252 > 0
        else 0
    )

    # -----------------------------------------------------
    # HACİM
    # -----------------------------------------------------

    volume20 = volume.rolling(20).mean()
    volume60 = volume.rolling(60).mean()

    avg_volume20 = safe(
        volume20.iloc[-1],
        1
    )

    avg_volume60 = safe(
        volume60.iloc[-1],
        1
    )

    volume_ratio = (
        safe(volume.iloc[-1] / avg_volume20, 1)
        if avg_volume20 > 0
        else 1
    )

    volume_trend = (
        safe(avg_volume20 / avg_volume60, 1)
        if avg_volume60 > 0
        else 1
    )

    # -----------------------------------------------------
    # VOLATİLİTE
    # -----------------------------------------------------

    daily_returns = close.pct_change()

    volatility20 = safe(
        daily_returns
        .rolling(20)
        .std()
        .iloc[-1]
        *
        np.sqrt(252)
        *
        100
    )

    # -----------------------------------------------------
    # MAKSİMUM GERİ ÇEKİLME
    # -----------------------------------------------------

    rolling_high = close.cummax()

    drawdown = (
        close / rolling_high - 1
    ) * 100

    current_drawdown = safe(
        drawdown.iloc[-1]
    )

    # -----------------------------------------------------
    # 1 — TREND SKORU
    # -----------------------------------------------------

    trend = 0

    if price > sma20.iloc[-1]:
        trend += 20
    else:
        trend += 5

    if sma20.iloc[-1] > sma50.iloc[-1]:
        trend += 20
    else:
        trend += 5

    if sma50.iloc[-1] > sma200.iloc[-1]:
        trend += 25
    else:
        trend += 5

    if price > sma200.iloc[-1]:
        trend += 20
    else:
        trend += 5

    if ema20.iloc[-1] > ema50.iloc[-1]:
        trend += 15
    else:
        trend += 4

    trend = clamp(trend)

    # -----------------------------------------------------
    # 2 — MOMENTUM SKORU
    # -----------------------------------------------------

    momentum = 50

    momentum += max(
        -15,
        min(15, ret5 * 1.5)
    )

    momentum += max(
        -20,
        min(20, ret21 * 1.5)
    )

    momentum += max(
        -12,
        min(12, ret63 * 0.5)
    )

    momentum += max(
        -8,
        min(8, ret126 * 0.25)
    )

    # Sağlıklı momentum bölgesi
    if 50 <= rsi <= 68:
        momentum += 10

    elif 45 <= rsi < 50:
        momentum += 4

    elif 68 < rsi <= 75:
        momentum += 4

    # Aşırı alım
    elif rsi > 80:
        momentum -= 12

    # Çok zayıf
    elif rsi < 30:
        momentum -= 8

    momentum = clamp(momentum)

    # -----------------------------------------------------
    # 3 — TEKNİK SKOR
    # -----------------------------------------------------

    macd_score = (
        80
        if macd_histogram > 0
        else 35
    )

    adx_score = 50

    if adx >= 30:
        adx_score = 90

    elif adx >= 25:
        adx_score = 80

    elif adx >= 20:
        adx_score = 65

    elif adx < 15:
        adx_score = 35

    technical = clamp(
        trend * 0.45
        +
        momentum * 0.30
        +
        macd_score * 0.15
        +
        adx_score * 0.10
    )

    # -----------------------------------------------------
    # 4 — HACİM / PARA AKIŞI
    # -----------------------------------------------------

    flow = 50

    flow += max(
        -20,
        min(
            20,
            (volume_ratio - 1) * 30
        )
    )

    flow += max(
        -15,
        min(
            15,
            (volume_trend - 1) * 30
        )
    )

    flow += max(
        -15,
        min(
            15,
            ret5 * 2
        )
    )

    # Fiyat yükseliyor + hacim artıyorsa bonus
    if ret5 > 0 and volume_ratio >= 1.25:
        flow += 10

    flow = clamp(flow)

    # -----------------------------------------------------
    # 5 — RİSK SKORU
    # -----------------------------------------------------

    risk = 100

    # Yüksek volatilite cezası
    risk -= max(
        0,
        min(
            45,
            volatility20 * 1.7
        )
    )

    # Büyük geri çekilme cezası
    risk -= max(
        0,
        min(
            30,
            abs(min(0, current_drawdown)) * 0.7
        )
    )

    # Aşırı RSI
    if rsi > 80:
        risk -= 10

    if rsi < 30:
        risk -= 5

    risk = clamp(
        risk,
        10,
        95
    )

    # -----------------------------------------------------
    # 6 — TEMEL / DEĞERLEME / KAP
    # -----------------------------------------------------

    # Şimdilik gerçek veri kaynağı bağlanmadığı için
    # finansal veri UYDURMUYORUZ.
    fundamental = 50
    valuation = 50
    kap = 50

    # -----------------------------------------------------
    # 7 — ANA SKOR
    # -----------------------------------------------------

    score = (
        technical * 0.25
        +
        momentum * 0.20
        +
        technical * 0.15
        +
        flow * 0.15
        +
        risk * 0.15
        +
        valuation * 0.05
        +
        kap * 0.05
    )

    # -----------------------------------------------------
    # 8 — KALİTE BONUSU
    # -----------------------------------------------------

    bonus = 0

    # Güçlü trend + hacim teyidi
    if (
        price > sma50.iloc[-1]
        and
        sma50.iloc[-1] > sma200.iloc[-1]
        and
        volume_ratio >= 1.20
    ):
        bonus += 3

    # ADX güçlü trend
    if adx >= 25 and price > sma200.iloc[-1]:
        bonus += 2

    # MACD pozitif
    if macd_histogram > 0:
        bonus += 1

    # Aşırı alım cezası
    if rsi > 82:
        bonus -= 5

    score = clamp(
        score + bonus
    )

    # -----------------------------------------------------
    # 9 — SİNYAL
    # -----------------------------------------------------

    if score >= 80:
        signal = "ÇOK GÜÇLÜ"

    elif score >= 70:
        signal = "GÜÇLÜ"

    elif score >= 60:
        signal = "İZLE"

    elif score >= 45:
        signal = "NÖTR"

    else:
        signal = "ZAYIF"

    return {
        "code": sym,
        "name": name,
        "price": round(price, 2),

        "score": int(score),
        "signal": signal,

        "technical": int(technical),
        "trend": int(trend),
        "momentum": int(momentum),

        "fundamental": fundamental,
        "valuation": valuation,
        "kap": kap,

        "flow": int(flow),
        "riskScore": int(risk),

        "rsi": round(rsi, 2),
        "adx": round(adx, 2),

        "ret5": round(ret5, 2),
        "ret21": round(ret21, 2),
        "ret63": round(ret63, 2),
        "ret126": round(ret126, 2),

        "volumeRatio": round(volume_ratio, 2),
        "volumeTrend": round(volume_trend, 2),

        "volatility": round(volatility20, 2),

        "distance52wHigh": round(
            distance_high,
            2
        ),

        "distance52wLow": round(
            distance_low,
            2
        ),

        "drawdown": round(
            current_drawdown,
            2
        ),

        "macdPositive": bool(
            macd_histogram > 0
        )
    }


# ---------------------------------------------------------
# ANA PROGRAM
# ---------------------------------------------------------

def main():

    names = get_symbols()

    symbols = list(names)

    print(
        "BIST sembol sayısı:",
        len(symbols)
    )

    results = []
    failed = []

    for i in range(
        0,
        len(symbols),
        BATCH_SIZE
    ):

        batch = symbols[
            i:i + BATCH_SIZE
        ]

        print(
            f"[{i+1}-{i+len(batch)} / {len(symbols)}]"
        )

        try:

            raw = yf.download(
                [
                    s + ".IS"
                    for s in batch
                ],
                period="2y",
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

                if (
                    raw is not None
                    and
                    not raw.empty
                ):

                    ticker = s + ".IS"

                    if isinstance(
                        raw.columns,
                        pd.MultiIndex
                    ):

                        if (
                            ticker
                            in
                            raw.columns.get_level_values(0)
                        ):

                            d = raw[
                                ticker
                            ].copy()

                        elif (
                            ticker
                            in
                            raw.columns.get_level_values(1)
                        ):

                            d = raw.xs(
                                ticker,
                                axis=1,
                                level=1
                            ).copy()

                    else:

                        d = raw.copy()

                item = score(
                    s,
                    names[s],
                    d
                )

                if item:
                    results.append(item)

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
    # SIRALAMA
    # -----------------------------------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # -----------------------------------------------------
    # GÜVENLİK
    # -----------------------------------------------------

    if len(results) < 400:

        raise RuntimeError(
            f"Çok az hisse üretildi: {len(results)}"
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
            results,
            f,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )

    print(
        "BAŞARILI:",
        len(results)
    )

    print(
        "VERİ YOK:",
        len(failed)
    )

    print(
        "İLK 20:"
    )

    print(
        [
            x["code"]
            for x in results[:20]
        ]
    )


if __name__ == "__main__":
    main()

import io
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf

SYMBOL_URL = "https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/bist.csv"

BATCH_SIZE = 10
RETRY_COUNT = 3
MIN_HISTORY = 220


# ---------------------------------------------------------
# BIST HİSSELERİNİ AL
# ---------------------------------------------------------

def get_symbols():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        SYMBOL_URL,
        headers=headers,
        timeout=30
    )

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


# ---------------------------------------------------------
# RSI
# ---------------------------------------------------------

def rsi(series, period=14):

    delta = series.diff()

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

    result = 100 - (100 / (1 + rs))

    return result.fillna(50)


# ---------------------------------------------------------
# STOCHASTIC RSI
# ---------------------------------------------------------

def stochastic_rsi(series, period=14):

    rr = rsi(series, period)

    low = rr.rolling(period).min()
    high = rr.rolling(period).max()

    stoch = (rr - low) / (high - low).replace(0, np.nan)

    return (stoch * 100).fillna(50)


# ---------------------------------------------------------
# TEKNİK SKOR
# ---------------------------------------------------------

def calculate_technical_score(c):

    if len(c) < MIN_HISTORY:
        return 0

    price = float(c.iloc[-1])

    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma100 = c.rolling(100).mean()
    sma200 = c.rolling(200).mean()

    s20 = float(sma20.iloc[-1])
    s50 = float(sma50.iloc[-1])
    s100 = float(sma100.iloc[-1])
    s200 = float(sma200.iloc[-1])

    rr = float(rsi(c).iloc[-1])

    # MACD
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()

    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()

    macd_now = float(macd.iloc[-1])
    signal_now = float(signal.iloc[-1])

    score = 0

    # -------------------------
    # Trend
    # -------------------------

    if price > s20:
        score += 8
    else:
        score += 2

    if price > s50:
        score += 8
    else:
        score += 2

    if price > s200:
        score += 10
    else:
        score += 2

    # SMA sıralaması
    if s20 > s50 > s200:
        score += 12
    elif s20 > s50:
        score += 7
    elif s50 > s200:
        score += 5

    # -------------------------
    # RSI
    # -------------------------

    if 52 <= rr <= 68:
        score += 12
    elif 45 <= rr < 52:
        score += 8
    elif 68 < rr <= 75:
        score += 7
    elif rr > 75:
        score += 3
    else:
        score += 4

    # -------------------------
    # MACD
    # -------------------------

    if macd_now > signal_now and macd_now > 0:
        score += 15
    elif macd_now > signal_now:
        score += 10
    else:
        score += 4

    return min(100, int(score))


# ---------------------------------------------------------
# MOMENTUM
# ---------------------------------------------------------

def calculate_momentum(c):

    if len(c) < 100:
        return 50

    ret5 = (c.iloc[-1] / c.iloc[-6] - 1) * 100
    ret21 = (c.iloc[-1] / c.iloc[-22] - 1) * 100
    ret63 = (c.iloc[-1] / c.iloc[-64] - 1) * 100

    score = 50

    if ret5 > 0:
        score += 5

    if ret5 > 3:
        score += 5

    if ret21 > 0:
        score += 10

    if ret21 > 10:
        score += 5

    if ret63 > 0:
        score += 10

    if ret63 > 20:
        score += 5

    if ret21 < -10:
        score -= 10

    return int(max(0, min(100, score)))


# ---------------------------------------------------------
# HACİM SKORU
# ---------------------------------------------------------

def calculate_flow(c, v):

    if len(v) < 30:
        return 50, 1

    avg20 = v.rolling(20).mean().iloc[-1]

    if avg20 <= 0:
        return 50, 1

    volume_ratio = float(v.iloc[-1] / avg20)

    price_change = float(
        (c.iloc[-1] / c.iloc[-2] - 1) * 100
    )

    score = 50

    if volume_ratio > 1.2:
        score += 10

    if volume_ratio > 1.5:
        score += 10

    if volume_ratio > 2:
        score += 10

    # Hacim artarken fiyat yükseliyorsa pozitif
    if price_change > 0 and volume_ratio > 1.2:
        score += 10

    # Hacim artarken fiyat düşüyorsa negatif
    if price_change < 0 and volume_ratio > 1.5:
        score -= 15

    return int(max(0, min(100, score))), round(volume_ratio, 2)


# ---------------------------------------------------------
# RİSK
# ---------------------------------------------------------

def calculate_risk(c):

    returns = c.pct_change().dropna()

    if len(returns) < 20:
        return 50, 0

    volatility = float(
        returns.tail(20).std() *
        np.sqrt(252) *
        100
    )

    # Volatilite düşükse daha yüksek puan
    risk_score = 100 - volatility * 1.5

    risk_score = int(
        max(20, min(95, risk_score))
    )

    return risk_score, round(volatility, 2)


# ---------------------------------------------------------
# KIRILIM SKORU
# ---------------------------------------------------------

def calculate_breakout(c):

    if len(c) < 65:
        return 50

    price = float(c.iloc[-1])

    high20 = float(
        c.iloc[-21:-1].max()
    )

    high60 = float(
        c.iloc[-61:-1].max()
    )

    score = 50

    if price > high20:
        score += 20

    if price > high60:
        score += 25

    return min(100, score)


# ---------------------------------------------------------
# 52 HAFTA KONUMU
# ---------------------------------------------------------

def calculate_position(c):

    if len(c) < 200:
        return 50

    year = c.tail(252)

    low = float(year.min())
    high = float(year.max())
    price = float(c.iloc[-1])

    if high <= low:
        return 50

    position = (price - low) / (high - low) * 100

    # Çok dipte olan hisselere değil,
    # güçlü ama aşırı şişmemiş hisselere avantaj
    if 55 <= position <= 85:
        return 90

    if 40 <= position < 55:
        return 70

    if 85 < position <= 95:
        return 65

    if position > 95:
        return 45

    return 50


# ---------------------------------------------------------
# ANA SKOR
# ---------------------------------------------------------

def score(sym, name, d):

    if d is None or d.empty:
        return None

    required = {"Close", "Volume"}

    if not required.issubset(d.columns):
        return None

    c = pd.to_numeric(
        d["Close"],
        errors="coerce"
    ).dropna()

    v = pd.to_numeric(
        d["Volume"],
        errors="coerce"
    ).fillna(0)

    if len(c) < MIN_HISTORY:
        return None

    price = float(c.iloc[-1])

    # Teknik
    technical = calculate_technical_score(c)

    # Momentum
    momentum = calculate_momentum(c)

    # Hacim
    flow, volume_ratio = calculate_flow(c, v)

    # Risk
    risk, volatility = calculate_risk(c)

    # Kırılım
    breakout = calculate_breakout(c)

    # 52 hafta konumu
    position = calculate_position(c)

    # RSI
    current_rsi = float(
        rsi(c).iloc[-1]
    )

    # 21 günlük getiri
    ret21 = float(
        (price / c.iloc[-22] - 1) * 100
    )

    # -----------------------------------------------------
    # TEMEL / DEĞERLEME
    #
    # Bunları daha sonra KAP + bilanço verisiyle gerçek
    # veriye bağlayacağız.
    # -----------------------------------------------------

    fundamental = 50
    valuation = 50
    kap = 50

    # -----------------------------------------------------
    # YENİ GENEL SKOR
    # -----------------------------------------------------

    total = (
        technical * 0.30 +
        momentum * 0.15 +
        flow * 0.15 +
        breakout * 0.10 +
        position * 0.10 +
        risk * 0.10 +
        fundamental * 0.05 +
        valuation * 0.05
    )

    # -----------------------------------------------------
    # AŞIRI RSI CEZASI
    # -----------------------------------------------------

    if current_rsi > 80:
        total -= 8

    elif current_rsi > 75:
        total -= 4

    # -----------------------------------------------------
    # ÇOK GÜÇLÜ TREND BONUSU
    # -----------------------------------------------------

    sma20 = c.rolling(20).mean().iloc[-1]
    sma50 = c.rolling(50).mean().iloc[-1]
    sma200 = c.rolling(200).mean().iloc[-1]

    if price > sma20 > sma50 > sma200:
        total += 5

    # Hacim + momentum birlikte
    if volume_ratio > 1.5 and ret21 > 5:
        total += 5

    total = int(
        max(0, min(100, round(total)))
    )

    return {
        "code": sym,
        "name": name,
        "price": round(price, 2),

        "technical": int(technical),
        "fundamental": int(fundamental),
        "valuation": int(valuation),
        "kap": int(kap),

        "momentum": int(momentum),
        "breakout": int(breakout),
        "position": int(position),

        "flow": int(flow),
        "riskScore": int(risk),

        "score": total,

        "ret21": round(ret21, 2),
        "volumeRatio": volume_ratio,
        "rsi": round(current_rsi, 2),
        "volatility": volatility
    }


# ---------------------------------------------------------
# YAHOO DOWNLOAD
# ---------------------------------------------------------

def download_batch(batch):

    tickers = [
        s + ".IS"
        for s in batch
    ]

    for attempt in range(1, RETRY_COUNT + 1):

        try:

            print(
                f"Yahoo deneme {attempt}/{RETRY_COUNT}: "
                f"{len(batch)} hisse"
            )

            raw = yf.download(
                tickers,
                period="1y",
                interval="1d",
                auto_adjust=True,
                group_by="ticker",
                threads=False,
                progress=False,
                timeout=60
            )

            if raw is not None and not raw.empty:
                return raw

        except Exception as e:

            print(
                "Yahoo hata:",
                repr(e)
            )

        time.sleep(3 * attempt)

    return None


# ---------------------------------------------------------
# DATAFRAME ÇIKAR
# ---------------------------------------------------------

def extract_symbol(raw, symbol):

    if raw is None or raw.empty:
        return None

    ticker = symbol + ".IS"

    try:

        if isinstance(raw.columns, pd.MultiIndex):

            level0 = raw.columns.get_level_values(0)
            level1 = raw.columns.get_level_values(1)

            if ticker in level0:
                return raw[ticker].copy()

            if ticker in level1:
                return raw.xs(
                    ticker,
                    axis=1,
                    level=1
                ).copy()

        else:

            return raw.copy()

    except Exception as e:

        print(
            "Dataframe çıkarma hatası",
            symbol,
            repr(e)
        )

    return None


# ---------------------------------------------------------
# TEK HİSSE FALLBACK
# ---------------------------------------------------------

def download_single(symbol):

    ticker = symbol + ".IS"

    for attempt in range(1, RETRY_COUNT + 1):

        try:

            d = yf.download(
                ticker,
                period="1y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=60
            )

            if d is not None and not d.empty:

                if isinstance(d.columns, pd.MultiIndex):

                    d.columns = d.columns.get_level_values(0)

                return d

        except Exception as e:

            print(
                "Tekil hata:",
                symbol,
                repr(e)
            )

        time.sleep(2 * attempt)

    return None


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    names = get_symbols()

    syms = list(names.keys())

    print(
        "BIST sembol sayısı:",
        len(syms)
    )

    out = []
    failed = []

    # -----------------------------------------------------
    # TOPLU İNDİR
    # -----------------------------------------------------

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

        raw = download_batch(batch)

        for s in batch:

            try:

                d = extract_symbol(
                    raw,
                    s
                )

                x = score(
                    s,
                    names[s],
                    d
                )

                if x is not None:

                    out.append(x)

                else:

                    failed.append(s)

            except Exception as e:

                print(
                    "SKIP:",
                    s,
                    repr(e)
                )

                failed.append(s)

        time.sleep(1)

    # -----------------------------------------------------
    # BAŞARISIZLARI TEK TEK DENE
    # -----------------------------------------------------

    if failed:

        print(
            "Tekrar denenecek:",
            len(failed)
        )

        retry_failed = failed[:]
        failed = []

        for s in retry_failed:

            try:

                d = download_single(s)

                x = score(
                    s,
                    names[s],
                    d
                )

                if x is not None:

                    out.append(x)

                else:

                    failed.append(s)

            except Exception as e:

                print(
                    "FINAL SKIP:",
                    s,
                    repr(e)
                )

                failed.append(s)

            time.sleep(0.5)

    # -----------------------------------------------------
    # DUPLICATE TEMİZLE
    # -----------------------------------------------------

    unique = {}

    for x in out:
        unique[x["code"]] = x

    out = list(unique.values())

    # -----------------------------------------------------
    # SKOR SIRALAMA
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
            separators=(",", ":")
        )

    # -----------------------------------------------------
    # RAPOR
    # -----------------------------------------------------

    print("")
    print("==============================")
    print("BIST RADAR TAMAMLANDI")
    print("==============================")

    print(
        "Başarılı:",
        len(out)
    )

    print(
        "Veri alınamayan:",
        len(failed)
    )

    print(
        "İlk 20:"
    )

    for x in out[:20]:

        print(
            x["code"],
            x["score"],
            x["price"]
        )

    # -----------------------------------------------------
    # KRİTİK KORUMA
    # -----------------------------------------------------

    if len(out) < 100:

        raise RuntimeError(
            "Çok az hisse üretildi: "
            + str(len(out))
        )


if __name__ == "__main__":
    main()

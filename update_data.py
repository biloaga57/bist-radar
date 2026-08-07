import io
import json
import math
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# BIST RADAR - GELİŞMİŞ SKOR MOTORU
# ============================================================

SYMBOL_URL = (
    "https://raw.githubusercontent.com/ahmeterenodaci/"
    "Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/"
    "main/bist.csv"
)

BATCH_SIZE = 25
MIN_HISTORY = 220


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def safe_float(x, default=None):
    try:
        if x is None:
            return default

        x = float(x)

        if not math.isfinite(x):
            return default

        return x
    except Exception:
        return default


def clamp(x, low=0, high=100):
    x = safe_float(x, low)
    return max(low, min(high, x))


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


# ============================================================
# TEKNİK İNDİKATÖRLER
# ============================================================

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


def atr(high, low, close, period=14):
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


def adx(high, low, close, period=14):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where(
        (up_move > down_move) & (up_move > 0),
        up_move,
        0
    )

    minus_dm = np.where(
        (down_move > up_move) & (down_move > 0),
        down_move,
        0
    )

    atr_value = atr(
        high,
        low,
        close,
        period
    )

    plus_di = (
        pd.Series(plus_dm, index=close.index)
        .ewm(alpha=1 / period, adjust=False)
        .mean()
        / atr_value.replace(0, np.nan)
        * 100
    )

    minus_di = (
        pd.Series(minus_dm, index=close.index)
        .ewm(alpha=1 / period, adjust=False)
        .mean()
        / atr_value.replace(0, np.nan)
        * 100
    )

    dx = (
        (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
        * 100
    )

    return dx.ewm(
        alpha=1 / period,
        adjust=False
    ).mean().fillna(0)


# ============================================================
# TEKNİK SKOR
# ============================================================

def technical_score(c, high, low, volume):

    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()

    r = rsi(c)
    a = adx(high, low, c)

    ema12 = c.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = c.ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26

    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    price = c.iloc[-1]

    score = 0
    signals = []

    # --------------------------------------------------------
    # SMA TREND
    # --------------------------------------------------------

    if price > sma20.iloc[-1]:
        score += 8
        signals.append("Fiyat SMA20 üzerinde")
    else:
        score += 2

    if sma20.iloc[-1] > sma50.iloc[-1]:
        score += 8
        signals.append("SMA20 > SMA50")
    else:
        score += 2

    if sma50.iloc[-1] > sma200.iloc[-1]:
        score += 8
        signals.append("SMA50 > SMA200")
    else:
        score += 2

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rv = safe_float(r.iloc[-1], 50)

    if 50 <= rv <= 68:
        score += 8
        signals.append("RSI sağlıklı bölgede")
    elif 68 < rv <= 75:
        score += 6
        signals.append("RSI güçlü")
    elif rv < 30:
        score += 3
        signals.append("RSI aşırı satım")
    elif rv > 75:
        score += 2
        signals.append("RSI aşırı alım")
    else:
        score += 4

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if macd.iloc[-1] > signal.iloc[-1]:
        score += 8
        signals.append("MACD pozitif")
    else:
        score += 2

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    adx_value = safe_float(a.iloc[-1], 0)

    if adx_value >= 30:
        score += 8
        signals.append("Güçlü trend")
    elif adx_value >= 20:
        score += 6
        signals.append("Trend oluşuyor")
    else:
        score += 3

    # --------------------------------------------------------
    # 52 HAFTALIK KONUM
    # --------------------------------------------------------

    high52 = c.tail(252).max()
    low52 = c.tail(252).min()

    if high52 > low52:
        position52 = (
            (price - low52)
            / (high52 - low52)
            * 100
        )
    else:
        position52 = 50

    if position52 >= 80:
        score += 7
        signals.append("52 hafta zirvesine yakın")
    elif position52 >= 60:
        score += 6
    elif position52 >= 40:
        score += 4
    else:
        score += 2

    return {
        "score": int(clamp(score, 0, 55)),
        "rsi": round(rv, 2),
        "adx": round(adx_value, 2),
        "position52": round(position52, 2),
        "signals": signals,
    }


# ============================================================
# MOMENTUM
# ============================================================

def momentum_score(c):

    price = safe_float(c.iloc[-1], 0)

    ret21 = (
        (price / c.iloc[-22] - 1) * 100
        if len(c) >= 22
        else 0
    )

    ret63 = (
        (price / c.iloc[-64] - 1) * 100
        if len(c) >= 64
        else 0
    )

    ret126 = (
        (price / c.iloc[-127] - 1) * 100
        if len(c) >= 127
        else 0
    )

    score = 0
    signals = []

    # 1 aylık momentum
    if ret21 >= 10:
        score += 8
        signals.append("1 aylık güçlü momentum")
    elif ret21 >= 5:
        score += 6
    elif ret21 > 0:
        score += 4
    else:
        score += 1

    # 3 aylık momentum
    if ret63 >= 20:
        score += 10
        signals.append("3 aylık güçlü momentum")
    elif ret63 >= 10:
        score += 8
    elif ret63 > 0:
        score += 5
    else:
        score += 1

    # 6 aylık momentum
    if ret126 >= 30:
        score += 10
        signals.append("6 aylık güçlü momentum")
    elif ret126 >= 15:
        score += 8
    elif ret126 > 0:
        score += 5
    else:
        score += 1

    return {
        "score": int(clamp(score, 0, 30)),
        "ret21": round(ret21, 2),
        "ret63": round(ret63, 2),
        "ret126": round(ret126, 2),
        "signals": signals,
    }


# ============================================================
# HACİM / PARA AKIŞI
# ============================================================

def flow_score(c, volume):

    volume = volume.fillna(0)

    vol20 = volume.rolling(20).mean()
    vol5 = volume.rolling(5).mean()

    latest20 = safe_float(vol20.iloc[-1], 0)
    latest5 = safe_float(vol5.iloc[-1], 0)
    latest = safe_float(volume.iloc[-1], 0)

    if latest20 > 0:
        volume_ratio = latest / latest20
    else:
        volume_ratio = 1

    if latest20 > 0:
        volume_momentum = latest5 / latest20
    else:
        volume_momentum = 1

    score = 0
    signals = []

    if volume_ratio >= 2:
        score += 8
        signals.append("Hacim patlaması")
    elif volume_ratio >= 1.5:
        score += 7
        signals.append("Hacim güçlü")
    elif volume_ratio >= 1.15:
        score += 5
    elif volume_ratio >= 0.8:
        score += 3
    else:
        score += 1

    if volume_momentum >= 1.3:
        score += 7
        signals.append("Hacim ivmeleniyor")
    elif volume_momentum >= 1.1:
        score += 5
    else:
        score += 2

    return {
        "score": int(clamp(score, 0, 15)),
        "volumeRatio": round(volume_ratio, 2),
        "volumeMomentum": round(volume_momentum, 2),
        "signals": signals,
    }


# ============================================================
# RİSK
# ============================================================

def risk_score(c):

    returns = c.pct_change().dropna()

    volatility = (
        returns.tail(20).std()
        * np.sqrt(252)
        * 100
    )

    volatility = safe_float(volatility, 50)

    drawdown_series = (
        c / c.cummax() - 1
    )

    max_drawdown = (
        abs(drawdown_series.tail(252).min())
        * 100
    )

    score = 10
    signals = []

    if volatility <= 20:
        score += 10
        signals.append("Düşük volatilite")
    elif volatility <= 30:
        score += 8
    elif volatility <= 45:
        score += 5
    elif volatility <= 60:
        score += 3
    else:
        score += 1
        signals.append("Yüksek volatilite")

    if max_drawdown <= 20:
        score += 5
    elif max_drawdown <= 35:
        score += 4
    elif max_drawdown <= 50:
        score += 2
    else:
        score += 1

    return {
        "score": int(clamp(score, 0, 15)),
        "volatility": round(volatility, 2),
        "maxDrawdown": round(max_drawdown, 2),
        "signals": signals,
    }


# ============================================================
# TEMEL / DEĞERLEME
# ============================================================

def fundamental_score(sym):

    """
    Yahoo Finance finansal verisi mevcutsa kullanılır.
    Veri alınamazsa puan uydurulmaz.
    """

    result = {
        "score": None,
        "valuation": None,
        "fundamentalData": False,
    }

    try:
        ticker = yf.Ticker(sym + ".IS")

        info = ticker.info or {}

        roe = safe_float(info.get("returnOnEquity"))
        debt = safe_float(info.get("debtToEquity"))
        margin = safe_float(info.get("profitMargins"))
        pe = safe_float(info.get("trailingPE"))
        pb = safe_float(info.get("priceToBook"))

        fundamental = 50
        valuation = 50

        fundamental_count = 0
        valuation_count = 0

        # ROE
        if roe is not None:
            fundamental_count += 1

            if roe >= 0.25:
                fundamental += 15
            elif roe >= 0.15:
                fundamental += 10
            elif roe >= 0.08:
                fundamental += 5
            elif roe < 0:
                fundamental -= 15

        # Borç / özkaynak
        if debt is not None:
            fundamental_count += 1

            if debt <= 50:
                fundamental += 15
            elif debt <= 100:
                fundamental += 8
            elif debt <= 200:
                fundamental += 2
            else:
                fundamental -= 10

        # Net kâr marjı
        if margin is not None:
            fundamental_count += 1

            if margin >= 0.20:
                fundamental += 10
            elif margin >= 0.10:
                fundamental += 7
            elif margin > 0:
                fundamental += 3
            else:
                fundamental -= 10

        # F/K
        if pe is not None and pe > 0:
            valuation_count += 1

            if pe < 8:
                valuation += 15
            elif pe < 12:
                valuation += 10
            elif pe < 18:
                valuation += 5
            elif pe > 35:
                valuation -= 15

        # PD/DD
        if pb is not None and pb > 0:
            valuation_count += 1

            if pb < 1:
                valuation += 15
            elif pb < 1.5:
                valuation += 10
            elif pb < 2.5:
                valuation += 5
            elif pb > 5:
                valuation -= 10

        if fundamental_count > 0:
            result["score"] = int(
                clamp(fundamental)
            )

        if valuation_count > 0:
            result["valuation"] = int(
                clamp(valuation)
            )

        result["fundamentalData"] = (
            fundamental_count > 0
        )

    except Exception as e:
        print("Temel veri alınamadı:", sym, e)

    return result


# ============================================================
# ANA SKOR
# ============================================================

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

    volume = pd.to_numeric(
        d["Volume"],
        errors="coerce"
    ).fillna(0)

    if len(c) < MIN_HISTORY:
        return None

    high = pd.to_numeric(
        d["High"],
        errors="coerce"
    ).reindex(c.index)

    low = pd.to_numeric(
        d["Low"],
        errors="coerce"
    ).reindex(c.index)

    high = high.fillna(c)
    low = low.fillna(c)

    technical = technical_score(
        c,
        high,
        low,
        volume
    )

    momentum = momentum_score(c)

    flow = flow_score(
        c,
        volume
    )

    risk = risk_score(c)

    fundamental = fundamental_score(sym)

    price = safe_float(c.iloc[-1], 0)

    # --------------------------------------------------------
    # AĞIRLIKLAR
    # --------------------------------------------------------

    tech100 = technical["score"] / 55 * 100
    momentum100 = momentum["score"] / 30 * 100
    flow100 = flow["score"] / 15 * 100
    risk100 = risk["score"] / 25 * 100

    fundamental100 = (
        fundamental["score"]
        if fundamental["score"] is not None
        else 50
    )

    valuation100 = (
        fundamental["valuation"]
        if fundamental["valuation"] is not None
        else 50
    )

    # Teknik + momentum + temel + değerleme
    total = (
        tech100 * 0.25
        + momentum100 * 0.20
        + fundamental100 * 0.15
        + valuation100 * 0.10
        + flow100 * 0.15
        + risk100 * 0.15
    )

    total = int(round(clamp(total)))

    # --------------------------------------------------------
    # SINIF
    # --------------------------------------------------------

    if total >= 85:
        rating = "Çok Güçlü"
    elif total >= 75:
        rating = "Güçlü"
    elif total >= 65:
        rating = "İzle"
    elif total >= 50:
        rating = "Nötr"
    else:
        rating = "Zayıf"

    signals = []

    signals.extend(technical["signals"])
    signals.extend(momentum["signals"])
    signals.extend(flow["signals"])
    signals.extend(risk["signals"])

    # --------------------------------------------------------
    # ÖZEL SİNYALLER
    # --------------------------------------------------------

    if (
        technical["position52"] >= 90
        and momentum["ret21"] > 5
    ):
        signals.append("Yeni zirve momentumu")

    if (
        flow["volumeRatio"] >= 1.5
        and momentum["ret21"] > 0
    ):
        signals.append("Hacim destekli yükseliş")

    if (
        technical["rsi"] >= 50
        and technical["rsi"] <= 70
        and technical["adx"] >= 20
    ):
        signals.append("Sağlıklı trend")

    return {
        "code": sym,
        "name": name,
        "price": round(price, 2),

        "technical": round(tech100),
        "momentum": round(momentum100),

        "fundamental": (
            int(fundamental100)
            if fundamental["fundamentalData"]
            else None
        ),

        "valuation": (
            int(valuation100)
            if fundamental["valuation"] is not None
            else None
        ),

        "flow": round(flow100),
        "riskScore": round(risk100),

        "score": total,
        "rating": rating,

        "ret21": momentum["ret21"],
        "ret63": momentum["ret63"],
        "ret126": momentum["ret126"],

        "volumeRatio": flow["volumeRatio"],
        "volumeMomentum": flow["volumeMomentum"],

        "rsi": technical["rsi"],
        "adx": technical["adx"],
        "position52": technical["position52"],

        "volatility": risk["volatility"],
        "maxDrawdown": risk["maxDrawdown"],

        "signals": signals[:12],
    }


# ============================================================
# ANA PROGRAM
# ============================================================

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

                if (
                    raw is not None
                    and not raw.empty
                    and isinstance(
                        raw.columns,
                        pd.MultiIndex
                    )
                ):

                    ticker = s + ".IS"

                    if ticker in raw.columns.get_level_values(0):

                        d = raw[ticker].copy()

                    elif ticker in raw.columns.get_level_values(1):

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

                if x is not None:
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

    # ========================================================
    # SIRALAMA
    # ========================================================

    out.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ========================================================
    # JSON
    # ========================================================

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

    # ========================================================
    # RAPOR
    # ========================================================

    print()
    print("=" * 60)
    print("BIST RADAR TAMAMLANDI")
    print("=" * 60)

    print(
        "Başarılı:",
        len(out)
    )

    print(
        "Veri yok:",
        len(failed)
    )

    print()

    print(
        "İLK 20 HİSSE:"
    )

    for i, x in enumerate(
        out[:20],
        start=1
    ):

        print(
            f"{i:2}. "
            f"{x['code']:6} "
            f"{x['score']:3} "
            f"{x['rating']:<12} "
            f"{x['price']}"
        )

    print("=" * 60)

    if len(out) < 400:
        raise RuntimeError(
            f"Çok az hisse döndü: {len(out)}"
        )


if __name__ == "__main__":
    main()

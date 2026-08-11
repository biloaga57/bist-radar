import io
import json
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf


SYMBOL_URL = (
    "https://raw.githubusercontent.com/ahmeterenodaci/"
    "Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/"
    "main/bist.csv"
)

BATCH_SIZE = 25


# =========================================================
# GENEL YARDIMCI FONKSİYONLAR
# =========================================================

def safe_float(x, default=0.0):
    try:
        x = float(x)
        if np.isfinite(x):
            return x
    except Exception:
        pass
    return default


def clamp(x, low=0, high=100):
    return int(max(low, min(high, safe_float(x))))


def pct_change(series, periods):
    if len(series) <= periods:
        return 0.0

    old = safe_float(series.iloc[-periods - 1])

    if old == 0:
        return 0.0

    return (
        safe_float(series.iloc[-1]) / old - 1
    ) * 100


# =========================================================
# HİSSE LİSTESİ
# =========================================================

def get_symbols():

    r = requests.get(
        SYMBOL_URL,
        timeout=30
    )

    r.raise_for_status()

    df = pd.read_csv(
        io.StringIO(r.text)
    )

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
        .str.replace(
            r"[^A-Z0-9]",
            "",
            regex=True
        )
    )

    df = (
        df[
            df["symbol"].str.len().between(2, 6)
        ]
        .drop_duplicates("symbol")
    )

    return dict(
        zip(
            df["symbol"],
            df["name"]
        )
    )


# =========================================================
# RSI
# =========================================================

def rsi(series, n=14):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / n,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / n,
        adjust=False
    ).mean()

    rs = (
        avg_gain /
        avg_loss.replace(
            0,
            np.nan
        )
    )

    result = 100 - (
        100 / (1 + rs)
    )

    return result.fillna(50)


# =========================================================
# ADX
# =========================================================

def adx(
    high,
    low,
    close,
    n=14
):

    high = pd.to_numeric(
        high,
        errors="coerce"
    )

    low = pd.to_numeric(
        low,
        errors="coerce"
    )

    close = pd.to_numeric(
        close,
        errors="coerce"
    )

    up_move = high.diff()

    down_move = -low.diff()

    plus_dm = np.where(
        (up_move > down_move)
        & (up_move > 0),
        up_move,
        0
    )

    minus_dm = np.where(
        (down_move > up_move)
        & (down_move > 0),
        down_move,
        0
    )

    tr1 = high - low

    tr2 = (
        high - close.shift()
    ).abs()

    tr3 = (
        low - close.shift()
    ).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr_value = tr.ewm(
        alpha=1 / n,
        adjust=False
    ).mean()

    plus_di = (
        100
        * pd.Series(
            plus_dm,
            index=close.index
        )
        .ewm(
            alpha=1 / n,
            adjust=False
        )
        .mean()
        / atr_value.replace(
            0,
            np.nan
        )
    )

    minus_di = (
        100
        * pd.Series(
            minus_dm,
            index=close.index
        )
        .ewm(
            alpha=1 / n,
            adjust=False
        )
        .mean()
        / atr_value.replace(
            0,
            np.nan
        )
    )

    dx = (
        100
        * (
            plus_di - minus_di
        ).abs()
        /
        (
            plus_di + minus_di
        ).replace(
            0,
            np.nan
        )
    )

    return (
        dx
        .ewm(
            alpha=1 / n,
            adjust=False
        )
        .mean()
        .fillna(20)
    )


# =========================================================
# ATR - WILDER
# =========================================================

def atr_wilder(
    high,
    low,
    close,
    n=14
):

    tr1 = high - low

    tr2 = (
        high - close.shift()
    ).abs()

    tr3 = (
        low - close.shift()
    ).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / n,
        adjust=False
    ).mean()


# =========================================================
# MaT-R
#
# Pine kodundaki:
#
# Kısa periyot = 3
# Uzun periyot = 5
# Sinyal = 2
# Trend = EMA34 > SMA34
# ATR = 17
# Çarpan = 2.2
# =========================================================

def matr_engine(
    close,
    high,
    low
):

    # -----------------------------------------------------
    # EMA 34
    # -----------------------------------------------------

    ema34 = close.ewm(
        span=34,
        adjust=False
    ).mean()

    # -----------------------------------------------------
    # SMA 34
    # -----------------------------------------------------

    sma34 = close.rolling(
        34
    ).mean()

    # -----------------------------------------------------
    # MaT-R MACD
    # Kısa = 3
    # Uzun = 5
    # Sinyal = 2
    # -----------------------------------------------------

    fast_ma = close.ewm(
        span=3,
        adjust=False
    ).mean()

    slow_ma = close.ewm(
        span=5,
        adjust=False
    ).mean()

    macd = fast_ma - slow_ma

    signal = macd.ewm(
        span=2,
        adjust=False
    ).mean()

    hist = macd - signal

    # -----------------------------------------------------
    # ATR 17
    # -----------------------------------------------------

    atr17 = atr_wilder(
        high,
        low,
        close,
        17
    )

    # -----------------------------------------------------
    # Son değerler
    # -----------------------------------------------------

    price = safe_float(
        close.iloc[-1]
    )

    macd_now = safe_float(
        macd.iloc[-1]
    )

    signal_now = safe_float(
        signal.iloc[-1]
    )

    hist_now = safe_float(
        hist.iloc[-1]
    )

    macd_prev = safe_float(
        macd.iloc[-2]
    )

    signal_prev = safe_float(
        signal.iloc[-2]
    )

    ema34_now = safe_float(
        ema34.iloc[-1]
    )

    sma34_now = safe_float(
        sma34.iloc[-1]
    )

    atr_now = safe_float(
        atr17.iloc[-1]
    )

    # -----------------------------------------------------
    # Pine:
    #
    # ta.crossover(macd, signal)
    #
    # -----------------------------------------------------

    crossover = (
        macd_now > signal_now
        and
        macd_prev <= signal_prev
    )

    # -----------------------------------------------------
    # Pine:
    #
    # oncu2 < oncu1
    #
    # SMA34 < EMA34
    # -----------------------------------------------------

    trend_ok = (
        sma34_now < ema34_now
    )

    # -----------------------------------------------------
    # AL SİNYALİ
    # -----------------------------------------------------

    buy_signal = (
        crossover
        and trend_ok
    )

    # -----------------------------------------------------
    # Mevcut pozitif durum
    # -----------------------------------------------------

    bullish = (
        macd_now > signal_now
        and trend_ok
    )

    # -----------------------------------------------------
    # Sinyal durumu
    # -----------------------------------------------------

    if buy_signal:
        matr_signal = "AL"
        matr_score = 100

    elif bullish:
        matr_signal = "POZİTİF"
        matr_score = 75

    elif macd_now > signal_now:
        matr_signal = "NÖTR"
        matr_score = 55

    else:
        matr_signal = "ZAYIF"
        matr_score = 25

    # -----------------------------------------------------
    # Giriş fiyatı
    #
    # Son gerçek MaT-R AL sinyalini bul
    # -----------------------------------------------------

    entry_price = None

    buy_indices = []

    for i in range(
        1,
        len(close)
    ):

        macd_i = safe_float(
            macd.iloc[i]
        )

        signal_i = safe_float(
            signal.iloc[i]
        )

        macd_prev_i = safe_float(
            macd.iloc[i - 1]
        )

        signal_prev_i = safe_float(
            signal.iloc[i - 1]
        )

        ema_i = safe_float(
            ema34.iloc[i]
        )

        sma_i = safe_float(
            sma34.iloc[i]
        )

        cross_i = (
            macd_i > signal_i
            and
            macd_prev_i <= signal_prev_i
        )

        trend_i = (
            sma_i < ema_i
        )

        if cross_i and trend_i:
            buy_indices.append(i)

    if buy_indices:

        last_buy_index = buy_indices[-1]

        entry_price = safe_float(
            close.iloc[last_buy_index]
        )

    # Eğer son sinyal çok eskiyse mevcut fiyatı
    # risk hesabında kullanmıyoruz.
    if entry_price is not None:

        days_since_signal = (
            len(close) - 1
            - buy_indices[-1]
        )

        if days_since_signal > 60:
            entry_price = None
            days_since_signal = None

    else:
        days_since_signal = None

    # -----------------------------------------------------
    # KAR AL / ZARAR KES
    # -----------------------------------------------------

    if entry_price is not None:

        stop_loss = (
            entry_price
            - 2.2 * atr_now
        )

        take_profit_1 = (
            entry_price * 1.12
        )

        take_profit_2 = (
            entry_price * 1.20
        )

    else:

        stop_loss = None
        take_profit_1 = None
        take_profit_2 = None

    # -----------------------------------------------------
    # Mevcut fiyata göre ATR zarar kes
    # -----------------------------------------------------

    current_atr_stop = (
        price - 2.2 * atr_now
    )

    # -----------------------------------------------------
    # EMA LİSTESİ
    # -----------------------------------------------------

    ema_periods = [
        8,
        21,
        34,
        55,
        89,
        144,
        233,
        377
    ]

    ema_values = {}

    for period in ema_periods:

        ema_values[
            f"ema{period}"
        ] = round(
            safe_float(
                close.ewm(
                    span=period,
                    adjust=False
                ).mean().iloc[-1]
            ),
            2
        )

    # -----------------------------------------------------
    # MA TREND PUANI
    # -----------------------------------------------------

    if price > ema34_now:
        trend_score = 100
    elif price > safe_float(
        close.ewm(
            span=21,
            adjust=False
        ).mean().iloc[-1]
    ):
        trend_score = 70
    else:
        trend_score = 30

    # -----------------------------------------------------
    # MA-R SONUCU
    # -----------------------------------------------------

    return {
        "matrSignal": matr_signal,
        "matrScore": int(matr_score),

        "matrBuySignal": bool(buy_signal),
        "matrBullish": bool(bullish),

        "matrMacd": round(
            macd_now,
            4
        ),

        "matrSignalLine": round(
            signal_now,
            4
        ),

        "matrHistogram": round(
            hist_now,
            4
        ),

        "matrTrend": (
            "POZİTİF"
            if trend_ok
            else "NEGATİF"
        ),

        "matrTrendScore": int(
            trend_score
        ),

        "matrEma34": round(
            ema34_now,
            2
        ),

        "matrSma34": round(
            sma34_now,
            2
        ),

        "matrAtr17": round(
            atr_now,
            2
        ),

        "matrStopLoss": (
            round(stop_loss, 2)
            if stop_loss is not None
            else None
        ),

        "matrTakeProfit1": (
            round(take_profit_1, 2)
            if take_profit_1 is not None
            else None
        ),

        "matrTakeProfit2": (
            round(take_profit_2, 2)
            if take_profit_2 is not None
            else None
        ),

        "matrCurrentAtrStop": round(
            current_atr_stop,
            2
        ),

        "matrEntryPrice": (
            round(entry_price, 2)
            if entry_price is not None
            else None
        ),

        "matrDaysSinceSignal": (
            int(days_since_signal)
            if days_since_signal is not None
            else None
        ),

        "matrCrossover": bool(
            crossover
        ),

        "matrEma": ema_values
    }


# =========================================================
# TEKNİK SKOR
# =========================================================

def technical_score(
    price,
    ma20,
    ma50,
    ma100,
    ma200,
    rsi_value,
    macd,
    macd_signal,
    adx_value
):

    score = 0

    if price > ma20:
        score += 15

    if price > ma50:
        score += 15

    if price > ma200:
        score += 15

    if ma20 > ma50:
        score += 10

    if ma50 > ma100:
        score += 10

    if ma100 > ma200:
        score += 10

    if 50 <= rsi_value <= 68:
        score += 10

    elif 45 <= rsi_value < 50:
        score += 6

    elif 68 < rsi_value <= 75:
        score += 7

    elif rsi_value > 75:
        score += 3

    if macd > macd_signal:
        score += 10

    if adx_value >= 30:
        score += 5

    elif adx_value >= 20:
        score += 3

    return clamp(score)


# =========================================================
# MOMENTUM
# =========================================================

def momentum_score(
    ret21,
    ret63,
    ret126
):

    score = 50

    if ret21 > 10:
        score += 15
    elif ret21 > 5:
        score += 10
    elif ret21 > 0:
        score += 5
    elif ret21 < -10:
        score -= 15
    elif ret21 < -5:
        score -= 10
    elif ret21 < 0:
        score -= 5

    if ret63 > 15:
        score += 15
    elif ret63 > 5:
        score += 10
    elif ret63 > 0:
        score += 5
    elif ret63 < -15:
        score -= 15
    elif ret63 < -5:
        score -= 10

    if ret126 > 25:
        score += 20
    elif ret126 > 10:
        score += 12
    elif ret126 > 0:
        score += 5
    elif ret126 < -20:
        score -= 20
    elif ret126 < -10:
        score -= 12

    return clamp(score)


# =========================================================
# PARA AKIŞI / HACİM
# =========================================================

def flow_score(
    close,
    volume
):

    volume = pd.to_numeric(
        volume,
        errors="coerce"
    ).fillna(0)

    avg20 = volume.rolling(
        20
    ).mean()

    last_avg = safe_float(
        avg20.iloc[-1],
        1
    )

    if last_avg <= 0:
        volume_ratio = 1
    else:
        volume_ratio = (
            safe_float(
                volume.iloc[-1]
            )
            / last_avg
        )

    ret21 = pct_change(
        close,
        21
    )

    score = 50

    if volume_ratio >= 2:
        score += 30

    elif volume_ratio >= 1.5:
        score += 20

    elif volume_ratio >= 1.2:
        score += 10

    elif volume_ratio < 0.7:
        score -= 10

    if (
        ret21 > 0
        and volume_ratio > 1
    ):
        score += 15

    if (
        ret21 < 0
        and volume_ratio > 1.5
    ):
        score -= 15

    return (
        clamp(score),
        volume_ratio
    )


# =========================================================
# RİSK
# =========================================================

def risk_score(close):

    returns = (
        close
        .pct_change()
        .dropna()
    )

    if len(returns) < 30:
        return 50, 0

    volatility = (
        returns
        .rolling(20)
        .std()
        .iloc[-1]
        * np.sqrt(252)
        * 100
    )

    volatility = safe_float(
        volatility
    )

    recent = close.tail(
        126
    )

    rolling_max = (
        recent.cummax()
    )

    drawdown = (
        recent / rolling_max - 1
    )

    max_drawdown = abs(
        safe_float(
            drawdown.min()
        ) * 100
    )

    score = 100

    if volatility > 70:
        score -= 45
    elif volatility > 50:
        score -= 30
    elif volatility > 35:
        score -= 20
    elif volatility > 25:
        score -= 10

    if max_drawdown > 40:
        score -= 30
    elif max_drawdown > 30:
        score -= 20
    elif max_drawdown > 20:
        score -= 10

    return (
        clamp(
            score,
            20,
            100
        ),
        volatility
    )


# =========================================================
# RELATİF GÜÇ
# =========================================================

def relative_strength(
    stock,
    benchmark
):

    if (
        benchmark is None
        or benchmark.empty
    ):
        return 50, 0

    stock21 = pct_change(
        stock,
        21
    )

    bench21 = pct_change(
        benchmark,
        21
    )

    stock63 = pct_change(
        stock,
        63
    )

    bench63 = pct_change(
        benchmark,
        63
    )

    diff21 = stock21 - bench21
    diff63 = stock63 - bench63

    score = 50

    if diff21 > 10:
        score += 20
    elif diff21 > 5:
        score += 12
    elif diff21 > 0:
        score += 5
    elif diff21 < -10:
        score -= 20
    elif diff21 < -5:
        score -= 12
    elif diff21 < 0:
        score -= 5

    if diff63 > 15:
        score += 20
    elif diff63 > 5:
        score += 10
    elif diff63 < -15:
        score -= 20
    elif diff63 < -5:
        score -= 10

    return (
        clamp(score),
        diff21
    )


# =========================================================
# ANA SKOR
# =========================================================

def score(
    sym,
    name,
    d,
    benchmark
):

    if d is None or d.empty:
        return None

    required = {
        "Close",
        "High",
        "Low",
        "Volume"
    }

    if not required.issubset(
        d.columns
    ):
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

    frame = pd.concat(
        [
            close.rename("Close"),
            high.rename("High"),
            low.rename("Low"),
            volume.rename("Volume")
        ],
        axis=1
    ).dropna(
        subset=["Close"]
    )

    if len(frame) < 220:
        return None

    close = frame["Close"]
    high = frame["High"]
    low = frame["Low"]
    volume = frame["Volume"]

    # -----------------------------------------------------
    # ORTALAMALAR
    # -----------------------------------------------------

    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma100 = close.rolling(100).mean()
    ma200 = close.rolling(200).mean()

    price = safe_float(
        close.iloc[-1]
    )

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    rsi_series = rsi(
        close
    )

    rsi_value = safe_float(
        rsi_series.iloc[-1]
    )

    # -----------------------------------------------------
    # NORMAL MACD
    # -----------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    macd_series = (
        ema12 - ema26
    )

    macd_signal_series = (
        macd_series
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    macd_value = safe_float(
        macd_series.iloc[-1]
    )

    macd_signal = safe_float(
        macd_signal_series.iloc[-1]
    )

    # -----------------------------------------------------
    # ADX
    # -----------------------------------------------------

    adx_series = adx(
        high,
        low,
        close
    )

    adx_value = safe_float(
        adx_series.iloc[-1]
    )

    # -----------------------------------------------------
    # GETİRİLER
    # -----------------------------------------------------

    ret21 = pct_change(
        close,
        21
    )

    ret63 = pct_change(
        close,
        63
    )

    ret126 = pct_change(
        close,
        126
    )

    # -----------------------------------------------------
    # HACİM
    # -----------------------------------------------------

    flow, volume_ratio = flow_score(
        close,
        volume
    )

    # -----------------------------------------------------
    # RİSK
    # -----------------------------------------------------

    risk, volatility = risk_score(
        close
    )

    # -----------------------------------------------------
    # RELATİF
    # -----------------------------------------------------

    relative, relative_diff = (
        relative_strength(
            close,
            benchmark
        )
    )

    # -----------------------------------------------------
    # TEKNİK
    # -----------------------------------------------------

    technical = technical_score(
        price,
        safe_float(
            ma20.iloc[-1]
        ),
        safe_float(
            ma50.iloc[-1]
        ),
        safe_float(
            ma100.iloc[-1]
        ),
        safe_float(
            ma200.iloc[-1]
        ),
        rsi_value,
        macd_value,
        macd_signal,
        adx_value
    )

    # -----------------------------------------------------
    # MOMENTUM
    # -----------------------------------------------------

    momentum = momentum_score(
        ret21,
        ret63,
        ret126
    )

    # -----------------------------------------------------
    # MaT-R
    # -----------------------------------------------------

    matr = matr_engine(
        close,
        high,
        low
    )

    matr_score = matr[
        "matrScore"
    ]

    # -----------------------------------------------------
    # PİYASA KALİTESİ
    # -----------------------------------------------------

    trend_quality = (
        technical * 0.40
        + momentum * 0.25
        + relative * 0.20
        + matr_score * 0.15
    )

    market_quality = clamp(
        trend_quality
    )

    # Şimdilik gerçek bilanço/KAP verisi
    # kullanılmadığı için sahte puan üretmiyoruz.
    fundamental = 50
    valuation = 50
    kap = 50

    # -----------------------------------------------------
    # ANA SKOR
    #
    # Teknik       %22
    # Momentum     %18
    # Para akışı   %14
    # Relatif güç  %13
    # Risk         %10
    # Piyasa       %13
    # MaT-R        %10
    # -----------------------------------------------------

    total = (
        technical * 0.22
        + momentum * 0.18
        + flow * 0.14
        + relative * 0.13
        + risk * 0.10
        + market_quality * 0.13
        + matr_score * 0.10
    )

    total = clamp(
        round(total)
    )

    # -----------------------------------------------------
    # GENEL SİNYAL
    # -----------------------------------------------------

    if total >= 75:
        signal = "GÜÇLÜ"

    elif total >= 65:
        signal = "POZİTİF"

    elif total >= 55:
        signal = "NÖTR"

    elif total >= 45:
        signal = "ZAYIF"

    else:
        signal = "NEGATİF"

    # -----------------------------------------------------
    # EK SİNYALLER
    # -----------------------------------------------------

    signals = []

    if price > safe_float(
        ma20.iloc[-1]
    ):
        signals.append("TREND")

    if macd_value > macd_signal:
        signals.append("MACD")

    if adx_value >= 25:
        signals.append("ADX")

    if volume_ratio >= 1.5:
        signals.append("HACİM")

    if relative_diff > 5:
        signals.append("RELATİF")

    if ret21 > 5:
        signals.append("MOMENTUM")

    if matr["matrBuySignal"]:
        signals.append("MaT-R AL")

    elif matr["matrBullish"]:
        signals.append("MaT-R POZİTİF")

    # -----------------------------------------------------
    # SONUÇ
    # -----------------------------------------------------

    result = {
        "code": sym,
        "name": name,

        "price": round(
            price,
            2
        ),

        "score": int(total),
        "signal": signal,

        "technical": int(
            technical
        ),

        "momentum": int(
            momentum
        ),

        "flow": int(
            flow
        ),

        "relativeStrength": int(
            relative
        ),

        "riskScore": int(
            risk
        ),

        "fundamental": int(
            fundamental
        ),

        "valuation": int(
            valuation
        ),

        "kap": int(
            kap
        ),

        "rsi": round(
            rsi_value,
            2
        ),

        "adx": round(
            adx_value,
            2
        ),

        "volumeRatio": round(
            volume_ratio,
            2
        ),

        "ret21": round(
            ret21,
            2
        ),

        "ret63": round(
            ret63,
            2
        ),

        "ret126": round(
            ret126,
            2
        ),

        "volatility": round(
            volatility,
            2
        ),

        "distance52High": round(
            (
                price
                /
                safe_float(
                    close.tail(252).max(),
                    price
                )
                - 1
            ) * 100,
            2
        ),

        "signals": signals
    }

    # -----------------------------------------------------
    # MaT-R VERİLERİNİ EKLE
    # -----------------------------------------------------

    result.update(
        matr
    )

    return result


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    names = get_symbols()

    syms = list(
        names
    )

    print(
        "BIST sembol sayısı:",
        len(syms)
    )

    # -----------------------------------------------------
    # BIST XU100 BENCHMARK
    # -----------------------------------------------------

    print(
        "BIST benchmark indiriliyor..."
    )

    try:

        benchmark_raw = yf.download(
            "^XU100",
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=30
        )

        if isinstance(
            benchmark_raw.columns,
            pd.MultiIndex
        ):

            benchmark = (
                benchmark_raw[
                    "Close"
                ].iloc[:, 0]
            )

        else:

            benchmark = (
                benchmark_raw[
                    "Close"
                ]
            )

        benchmark = pd.to_numeric(
            benchmark,
            errors="coerce"
        ).dropna()

    except Exception as e:

        print(
            "Benchmark alınamadı:",
            e
        )

        benchmark = pd.Series(
            dtype=float
        )

    # -----------------------------------------------------
    # HİSSELERİ TARA
    # -----------------------------------------------------

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
            f"[{i + 1}-"
            f"{i + len(batch)} / "
            f"{len(syms)}]"
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
                    and not raw.empty
                ):

                    if isinstance(
                        raw.columns,
                        pd.MultiIndex
                    ):

                        ticker = (
                            s + ".IS"
                        )

                        if (
                            ticker
                            in raw.columns
                            .get_level_values(0)
                        ):

                            d = raw[
                                ticker
                            ].copy()

                        elif (
                            ticker
                            in raw.columns
                            .get_level_values(1)
                        ):

                            d = raw.xs(
                                ticker,
                                axis=1,
                                level=1
                            ).copy()

                    else:

                        d = raw.copy()

                result = score(
                    s,
                    names[s],
                    d,
                    benchmark
                )

                if result is not None:

                    out.append(
                        result
                    )

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
    # MaT-R AL SAYISI
    # -----------------------------------------------------

    matr_buy_count = sum(
        1
        for x in out
        if x.get(
            "matrBuySignal",
            False
        )
    )

    matr_positive_count = sum(
        1
        for x in out
        if x.get(
            "matrBullish",
            False
        )
    )

    strong_count = sum(
        1
        for x in out
        if x["score"] >= 75
    )

    positive_count = sum(
        1
        for x in out
        if 65 <= x["score"] < 75
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
            separators=(
                ",",
                ":"
            )
        )

    # -----------------------------------------------------
    # RAPOR
    # -----------------------------------------------------

    print()
    print(
        "======================================"
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
        "GENEL GÜÇLÜ:",
        strong_count
    )

    print(
        "GENEL POZİTİF:",
        positive_count
    )

    print(
        "MaT-R AL:",
        matr_buy_count
    )

    print(
        "MaT-R POZİTİF:",
        matr_positive_count
    )

    print(
        "======================================"
    )

    print(
        "İLK 20:"
    )

    for i, x in enumerate(
        out[:20],
        1
    ):

        print(
            i,
            x["code"],
            "SKOR:",
            x["score"],
            x["signal"],
            "| MaT-R:",
            x["matrSignal"]
        )

    # -----------------------------------------------------
    # KONTROL
    # -----------------------------------------------------

    if len(out) < 400:

        raise RuntimeError(
            f"Çok az hisse döndü: "
            f"{len(out)}"
        )


if __name__ == "__main__":
    main()

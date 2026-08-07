#!/usr/bin/env python3
# BIST Radar - data.json düzeltici
#
# Amaç:
# update_data.py tarafından üretilen data.json içindeki
# NaN / Infinity / -Infinity değerlerini JSON standardına uygun
# null değerlerine çevirir.
#
# Kullanım:
#   python fix_data.py
#
# GitHub Actions'ta update_data.py'den SONRA çalıştırılmalıdır.

import json
import math
from pathlib import Path

DATA_FILE = Path("data.json")


def clean_json_values(value):
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    if isinstance(value, list):
        return [clean_json_values(v) for v in value]

    if isinstance(value, dict):
        return {k: clean_json_values(v) for k, v in value.items()}

    return value


def main():
    if not DATA_FILE.exists():
        raise SystemExit("HATA: data.json bulunamadı.")

    # Önce normal JSON olarak okumayı dene.
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Python json modülü NaN/Infinity'yi okuyabilir; bu nedenle
        # parse tekrar deneniyor ve sonrasında standart JSON yazılıyor.
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f, parse_constant=lambda x: None)

    data = clean_json_values(data)

    # allow_nan=False: Bundan sonra geçersiz NaN/Infinity yazılmasını engeller.
    tmp = DATA_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )
        f.write("\n")

    tmp.replace(DATA_FILE)

    if isinstance(data, list):
        print(f"OK: data.json düzeltildi. Hisse sayısı: {len(data)}")
    elif isinstance(data, dict):
        print("OK: data.json düzeltildi. Kök veri bir JSON nesnesi.")
    else:
        print("OK: data.json düzeltildi.")


if __name__ == "__main__":
    main()

# BIST Radar — Tüm BIST
Bu sürüm tüm BIST evrenini otomatik keşfedip günlük teknik tarama yapacak şekilde hazırlanmıştır.

## GitHub kurulumu
1. Tüm dosyaları `bist-radar` deposunun köküne yükle.
2. Settings > Pages > Deploy from a branch > `main` > `/ (root)` seç.
3. Actions sekmesinden `BIST Radar Günlük Güncelle` iş akışını bir kez manuel çalıştır.
4. İşlem bitince `data.json` oluşur ve site otomatik kullanır.

## Önemli
Bu paket ücretsiz yfinance günlük verisi kullanır. Gerçek zamanlı BIST verisi değildir. Veri sağlayıcıda bulunmayan semboller atlanabilir.
Temel analiz ve KAP puanı için gerçek, izinli bir veri kaynağı ayrıca bağlanmalıdır; bu sürümde bu iki alan nötr 50 ile başlar.
Yatırım tavsiyesi değildir.

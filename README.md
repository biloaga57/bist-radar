# BIST Radar — ücretsiz web sitesi başlangıç sürümü

Bu klasör statik bir web sitesidir. `index.html` dosyasını tarayıcıda açarak çalıştırabilirsiniz.

## İçerik
- Günlük tarama tablosu
- Arama ve sinyal filtresi
- Skor sıralaması
- RSI, 21 günlük momentum, hacim oranı
- Mobil uyumlu tasarım

## Gerçek veriye bağlama
Bu sürümdeki DATA dizisi demo veridir. Gerçek BIST verisi için `app.js` içindeki DATA yapısı bir API'den gelen JSON ile değiştirilmelidir.

Önerilen mimari:
Frontend (bu site) -> ücretsiz/izinli veri API'si -> günlük cron/job -> JSON/SQLite -> site.

Gerçek zamanlı BIST verisi için veri lisansı ve sağlayıcının kullanım koşulları kontrol edilmelidir.

## Ücretsiz yayınlama
Statik sürüm GitHub Pages, Cloudflare Pages veya Netlify gibi ücretsiz statik hosting servislerine yüklenebilir. Otomatik veri toplama için ayrıca GitHub Actions gibi zamanlanmış bir görev kullanılabilir; API kullanım koşullarına uyulmalıdır.

## Uyarı
Site yatırım tavsiyesi değildir. Skorlar sadece tarama amacıyla kullanılmalıdır.

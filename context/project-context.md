# ENS001 Gemi Rotalama Optimizasyonu - Proje Bağlamı

## 1. Projenin Amacı ve Durumu
Endüstri Mühendisliği takımı tarafından tasarlanan bir denizcilik/lojistik rotalama probleminin yazılım implementasyonunu yapıyoruz. Şu an **9. Hafta (Coding - Phase I)** aşamasındayız. Temel sınıf (class) yapılarını, kısıt (constraint) kontrollerini ve amaç fonksiyonunu (fitness/cost function) kodlamamız gerekiyor. Çözüm algoritması olarak **Genetik Algoritma (GA)** ve iyileştirici olarak **Değişken Komşuluk Araması (VNS)** kullanılacaktır. Geliştirme dili Python'dur.

## 2. Optimizasyon Problemi Detayları
* **Filo:** 10 gemi (7 şirket, 3 kiralık).
* **Rotalar:** Toplam 120 potansiyel rota kombinasyonu (Kuzey veya Güney yönlü, 2 kalkış limanı, 14 teslimat noktası). 
* **Zaman Periyodu:** 35 günlük operasyon döngüsü.

## 3. Matematiksel Model ve Kısıtlar (Constraints)
* **Zaman:** Toplam operasyon süresi 33 ile 37 gün arasında olmalıdır. Alt seferlerin (limanlar arası) hiçbiri 7 günü geçemez.
* **Bölge:** Bir rota ya sadece Kuzey ya da sadece Güney lokasyonlarına gidebilir (aynı anda ikisi birden olamaz).
* **Durak:** Bir gemi bir rota boyunca en fazla 2 farklı teslimat noktasına uğrayabilir. Döngü (cycle) oluşturulamaz.
* **Teslimat Zamanı:** İstenen tarihten (Due Date) en fazla 2 gün önce veya 2 gün sonra teslimat yapılmalıdır.
* **Kapasite ve Talep:** Taşınan yük gemi kapasitesini aşamaz. Müşteri talepleri bölünemez (tek seferde, tek gemiyle tam olarak karşılanmalı).
* **Atıl Süre (Idle Time):** Gemi 5 günden fazla boşta kalırsa dışarı kiralanır (gelir elde edilir). 5 günden az boşta kalırsa ceza maliyeti yazar.
* **Envanter:** 3 adet depodaki stoklar limitler dahilinde tutulmalı, negatife düşmemelidir.

## 4. Amaç Fonksiyonu (Minimize Z)
* Toplam Maliyet = (Rota Maliyeti) + (Gemi İşletme Gideri) + (Ceza Maliyeti) - (Kiralama Geliri)

## 5. Görevimiz (Phase I)
Lütfen bu bilgiler ışığında nesne yönelimli (OOP) bir yaklaşım kullanarak `Ship`, `Route`, `Location` sınıflarını ve yukarıdaki kısıtları kontrol eden doğrulama (validation) fonksiyonlarının temel iskeletini oluşturarak kodlamaya başla.
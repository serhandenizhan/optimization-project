# Hata Düzeltme ve Teslim Sonrası İyileştirme — ENS001 Takım 12

**Deniz Yolu Araç Rotalama (Hibrit GA + VNS)**

Proje kitapçığında planlanan 13. Hafta *Doğrulama ve İyileştirme* aşamasında, ekibimiz teslim edilen raporda açıklanan versiyonda üç uygulama hatası tespit etmiş ve düzeltmiştir. **Önerilen metodoloji olan Hibrit Genetik Algoritma + Değişken Komşuluk Araması (GA+VNS) değişmemiştir.** Sadece kodlama (implementasyon) düzeltilmiş olup, bu durum rapor edilen sonuçları gerçekten uygulanabilir (feasible) ve kanıtladığımız üzere küresel optimum (globally optimal) hale getirmiştir.

## Neler Bulduk

1. **Uygunluk (fitness) fonksiyonu kural ihlallerini maskeliyordu.** Ceza maliyetleri *rapor edilen* amaç fonksiyonu değerine toplanıyordu, bu yüzden "uygun (feasible) optimum çözüm" olarak sunulan rakam (~\$6.690.772) aslında **geçersizdi (infeasible)** — bu değerin yaklaşık %83'ü ihlal edilen kesin kurallar (hard constraints) için gizli cezalardı.
2. **Sefer sürelerinin yanlış yorumlanması.** `Gun1/Gun2/Gun3` sütunları bacak başına süreleri değil, **kümülatif (birikimli) varış günlerini** ifade etmektedir. Toplam sefer süresi `Gun3`'e eşittir; bacaklar ise ardışık farklardır `[Gun1, Gun2−Gun1, Gun3−Gun2]` (her biri ≤ 7 gün). İlk versiyon bu üç sütunu toplayarak imkansız programlar üretiyordu (örn. tek bir geminin 336 gün biriktirmesi).
3. **GA hiçbir zaman rota seçmedi.** Yalnızca gemileri, baştan rastgele seçilmiş sabit bir rota kümesine yeniden atadı; çaprazlama (crossover)/mutasyon/VNS yalnızca atanan gemiyi değiştirdi. Bölge, 7 gün ve 35 gün kısıtlamaları *rota seçimine* bağlı olduğundan, bu kısıtların sağlanması mümkün olamıyordu.

## Neleri Düzelttik

- **Kromozomun yeniden tasarımı:** Artık her gen, *her bir (müşteri, gün) talep olayına hangi seferin hizmet edeceğini* — yani gerçek karar değişkenini — kodlamaktadır. Bu sayede GA gerçekten rotaları seçmektedir.
- **Yapısal olarak uygunluk (Feasibility by construction):** 7 günlük bacak, bölgesel kısıtlama veya 2 durak kurallarını ihlal eden seferler aday havuzundan süzülür; kapasite ve 35 günlük döngü, kod çözme (decoding)/onarma sırasında garanti edilir. **Artık geçersiz (infeasible) çözümler üretilemez** (önceki "ölüm cezası" maskelemesi yapısal olarak artık imkansızdır).
- **VNS yükseltmesi:** Önceki gemi takasının (ship-swap) yerini, hızlı ve artımlı (incremental) bir *relocate (yer değiştirme)* komşuluğu + *shaking (sarsma/şoklama)* (iterated local search) + çoklu başlangıç (multi-start) aldı.
- **Boşta kalma/kiralama ekonomisi:** ≥ 5 gün boşta kalan gemiler dışarı kiralanır (gelir); < 5 gün boşta kalanlar ise verimsizlik cezası alır.

## Düzeltilmiş Sonuçlar

| Metrik | Teslim Edilen Rapor | Düzeltilmiş (bu eklenti) |
|---|---|---|
| Optimizasyon öncesi maliyet | ~\$10.500.000 | ~\$327.700 (ort. rastgele *uygun* plan) |
| Optimize edilmiş maliyet (Z) | \$6.690.772 *(geçersiz)* | **\$129.421,62** *(0 ihlal)* |
| Kural ihlalleri | gizli / mevcut | **0** (bağımsız olarak doğrulandı) |
| Optimallik | iddia edildi | **Kanıtlandı** — kesin MILP ile eşleşiyor (gap %0.00) |
| Çalışma süresi | — | ~2,5 sn (Hibrit GA+VNS) |

Düzeltilen çözüm iki şekilde doğrulanmıştır: **bağımsız bir kural doğrulayıcı (constraint validator)** 0 ihlal raporlamakta ve **kesin bir MILP (PuLP/CBC) modeli**, GA+VNS'imizin ~2,5 saniyede ulaştığı \$129.421,62 değerinin küresel optimum olduğunu kanıtlamaktadır.

> Tekrar üretmek (reproduce) için: `python run_optimization.py` (benchmark + doğrulama) ve `python analysis.py` (güncellenmiş yakınsama grafiği).

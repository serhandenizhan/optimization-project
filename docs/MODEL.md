# Model, Düzeltmeler ve Savunma Notları (ENS001 — Gemi Rotalama)

Bu belge, `vrp/` paketindeki **kısıt-sağlayan** çözümün matematiksel modelini,
eski (bozuk) implementasyona göre yapılan kritik düzeltmeleri ve sunumda
savunulabilecek varsayımları açıklar.

---

## 1. Eski implementasyon neden YANLIŞTI?

Eski `optimizer.py` + `main.py` "çözüyor" görünüyordu ama ürettiği "optimum"
çözümün maliyetinin **~%83'ü saf kısıt-ihlali cezasıydı** (yani çözüm
geçersizdi/infeasible). Kök nedenler:

1. **GA rota SEÇMİYORDU, sadece gemi atıyordu.** Çözümdeki 40 rota en başta
   `random.sample` ile rastgele seçilip sabitleniyordu; crossover/mutation/VNS
   yalnızca `assigned_ship` alanını değiştiriyordu. Bölge, 7-gün, 35-gün gibi
   kısıtlar rota kombinasyonuna bağlı olduğundan **hiçbir zaman düzeltilemiyordu.**
2. **Süre/bacak yanlış hesaplanıyordu.** `Gun1, Gun2, Gun3` sütunları
   **kümülatif varış günleridir** (Gun1≤Gun2≤Gun3, veride %100). Eski kod bunları
   `Gun1+Gun2+Gun3` diye TOPLUYORDU → tek gemiye 336 gün gibi saçma süreler çıkıyordu.
   - Doğrusu: **toplam sefer süresi = Gun3**; bacaklar = `[Gun1, Gun2-Gun1, Gun3-Gun2]`,
     her biri ≤ 7 gün.
3. **Veri sentetikti.** Eski `data_parser` talebi 0 olan müşterilere rastgele
   talep atıyor, bölgeyi/teslim tarihini elle uyduruyordu → benchmark anlamsızdı.

---

## 2. Doğru veri yorumu (`vrp/data.py`)

| Kaynak | Anlamı |
|---|---|
| `Kapasite` | 11 gemi: kapasite + ana liman. İlk 8 şirket, son 3 (G9-G11) kiralık. |
| `Gun_Maliyet` | Gemiye-özgü aday sefer havuzu: `g` gemisi, `i`→`j`(→`k`)→`o`, süre=Gun3, maliyet. |
| `Musteri_Talepleri` | Müşteri×gün bazında **bölünemez** talep olayları (25 adet). |
| `Kira6/8/10` | Gemiyi dışarı kiralama (negatif maliyet = gelir). |

İnşa-gereği (havuza alınırken) süzülen kısıtlar: **7-gün bacak**, **bölge saflığı**,
**max 2 durak**. Böylece çözücüye yalnızca feasible seferler girer (623 sefer).

---

## 3. Matematiksel model (`vrp/milp.py`)

**Karar:** `y[e,r] ∈ {0,1}` — `e` talep olayı, `r` seferiyle karşılanır.

**Amaç:** `min Z = Σ sefer maliyeti + Σ işletme gideri + Σ boşta ceza − Σ kira geliri`

**Kısıtlar (hepsi SERT — ceza terimi yok):**
1. **Kapsama (bölünemez talep):** her talep olayı tam bir sefere atanır: `Σ_r y[e,r] = 1`.
2. **Sefer-başına tekil olay:** bir sefer en fazla bir talep günü taşır (gerçekçi;
   teslimat-zamanı tutarlılığını korur).
3. **Kapasite:** `e`, ancak kapasitesi yeten geminin seferine atanabilir (havuz filtresi).
4. **35-gün döngüsü:** her geminin toplam sefer süresi ≤ 35 gün.
5. **Boşta/Kira ekonomisi:** `idle = 35 − süre`; `idle ≥ 5` → boş günler kiraya
   verilir (gelir), `0 < idle < 5` → verimsizlik cezası, `idle = 0` → tam kullanım.
   (Linearizasyon: `rent` ikili değişkeni + `w = rent·idle` yardımcı değişkeni.)

CBC küresel optimumu **~2.5 sn**'de bulur; `vrp/validator.py` bağımsız olarak
**0 ihlal** doğrular.

### 3b. Önerilen yöntem — Geliştirilmiş GA + VNS (`vrp/ga.py`)

Projenin asıl önerdiği (makaleyle uyumlu) metasezgisel yöntem budur. MILP ise
yalnızca **doğrulama/benchmark referansı** olarak kullanılır.

- **Kromozom:** her talep olayının hangi seferle karşılanacağı (gerçek karar).
- **GA operatörleri:** elitizm, üniform çaprazlama, mutasyon.
- **Memetik + VNS:** her bireye **artımlı (incremental) maliyetli** relocate yerel
  araması; ardından *shaking + yerel arama* (iterated local search) ile yerel
  optimumlardan kaçış.
- **Multi-start:** birkaç tohumla çalışır, en iyiyi tutar.

Sonuç: GA, **kanıtlı küresel optimumu (Z = 129.421,62 $) ~2,5 sn'de yakalar**
(gap %0.0). Yani önerilen metasezgisel, kesin yöntemle aynı kaliteyi metasezgisel
hızda verir. (`python run_optimization.py` çıktısı bunu gösterir.)

---

## 4. Önemli bulgu — veri/model gerginliği (savunmada vurgula)

- **M11**'in 4 talebi (33.000 ve 3×42.500 TEU) yalnızca **G4** (kapasite 42.500)
  ile karşılanabilir. Ama G4'ün havuzda yalnızca 4 feasible rotası var ve toplam
  süresi 26 gün → **katı 33-37 gün penceresi problemi INFEASIBLE yapar.**
- Çözüm: booklet'in **35-gün kuralı ile boşta/kira kuralını birleştirmek.** Gemi ya
  ~35 günlük programa taahhüt eder ya da boş günleri kiraya verilir. Bu, kuralların
  birleşik ve tutarlı okumasıdır ve G4 gibi "spot" gemileri doğru modeller.

---

## 5. Varsayımlar (raporda belgele)

- **Bölge (Kuzey/Güney):** Excel'de bölge sütunu yoktur. Takımın önceki kararıyla
  tutarlı açık varsayım: `KUZEY = {M2,M4,M7,M10,M11,M13}` (bkz. `vrp/data.py`).
- **Liman kısıtı uygulanmadı:** veride seferler geminin ana limanından kalkmıyor
  (572/1196 satır farklı) — `i` limanı serbest bırakıldı.
- **Parametreler:** işletme gideri 2.000 $/gün, kira geliri 396 $/gün (Kira10'dan:
  3960/10), verimsizlik cezası 2.000 $/gün.
- **Kapsam dışı (gelecek iş):** teslimat tarihi ±2 gün **takvim** kısıtı ve
  rafineri envanter dengesi, mevcut rota-havuzu soyutlamasında (ve referans
  modelin `X_{v,r}` yapısında) takvim boyutu olmadığından modellenmedi.

---

## 6. Çalıştırma

```bash
pip install -r requirements.txt
python run_optimization.py     # MILP + GA benchmark + doğrulama raporu
python analysis.py             # convergence_graph.png üretir
uvicorn api:app --reload       # canlı demo API'si (frontend bununla konuşur)
```

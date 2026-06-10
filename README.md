# 🚢 Global Maritime Route Optimization System

![Status](https://img.shields.io/badge/Status-Active-success)
![Istinye University](https://img.shields.io/badge/Istinye_University-ENS001-blue)
![React](https://img.shields.io/badge/Frontend-React_Vite-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_Python-009688?logo=fastapi)

[**🚀 CANLI DEMO İÇİN TIKLAYIN (Live Simulation)**](https://ship-routing-optimization.netlify.app/)

## 📌 Proje Hakkında
Bu proje, deniz taşımacılığı yapan küresel lojistik firmaları için geliştirilmiş bir **Karar Destek ve Simülasyon Sistemidir**. Araç Rotalama Problemi (VRP) temel alınarak, müşteri talepleri (TEU) ve gemi kapasiteleri arasındaki en optimum eşleşmeyi sağlayan özel bir **Genetik Algoritma** motoru ile tasarlanmıştır.

Amaç; kıtalararası rotalarda boş kapasiteyi (atıl kalma durumunu) minimuma indirmek, aşırı yüklemeden kaçınmak ve operasyonel sefer maliyetlerini genetik evrim simülasyonu ile asimptotik olarak en aza indirgemektir.

## ✨ Öne Çıkan Özellikler
- **Genetik Algoritma Motoru:** Elitizm, çaprazlama ve mutasyon operatörleriyle milisaniyeler içinde binlerce rotayı evrimleştirerek optimum Z (maliyet) değerini bulur.
- **Gerçekçi Okyanus Rotaları:** Gemiler harita üzerinde doğrusal (kuş uçuşu) değil, `searoute-js` algoritması ile dünyanın gerçek denizcilik kanalları ve boğazları üzerinden hareket eder.
- **Dinamik Kapasite Validasyonu:** Simülasyon esnasında gemilerin doluluk oranları (TEU) anlık hesaplanır. Kapasite sınırlarına göre UI renk değiştirir (Güvenli, Uyarı, Kritik).
- **Finansal Teşvik Sistemi:** Kârlı (negatif maliyetli) rotalar sistemde bir bug oluşturmak yerine "Teşvik (Incentive)" olarak finansal rapora yansıtılır.
- **Akıcı 60FPS Animasyon:** Donanım hızlandırmalı CSS ve React state optimizasyonu ile tarayıcıyı yormayan pürüzsüz gemi simülasyonları.

## 🛠 Teknoloji Yığını (Tech Stack)
* **Frontend:** React.js, Vite, React-Leaflet, Recharts, Searoute-js
* **Backend:** Python 3, FastAPI, Pandas
* **Deployment:** Netlify (Frontend), Render (Backend API)

---

## 💻 Geliştiriciler İçin Kurulum (Local Setup)

Proje canlı olarak [Netlify](https://ship-routing-optimization.netlify.app/) üzerinde barındırılmaktadır. Ancak sistemi kendi lokal bilgisayarınızda (localhost) çalıştırmak ve kaynak kodları test etmek isterseniz aşağıdaki adımları izleyebilirsiniz.

### 1. Backend (Python/FastAPI) Kurulumu
Genetik algoritma motorunu ve API'yi ayağa kaldırmak için:

```bash
# Proje dizinine gidin
cd optimization-project

# Sanal ortam oluşturun ve aktif edin (Opsiyonel ama önerilir)
python -m venv .venv
source .venv/bin/activate  # Mac/Linux için
# .venv\Scripts\activate   # Windows için

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# API sunucusunu başlatın
uvicorn backend.api:app --reload
```

### 2. Frontend (React/Vite) Kurulumu
Görsel simülasyon arayüzünü çalıştırmak için (Yeni bir terminal penceresinde):

```bash
# Frontend klasörüne gidin
cd frontend

# Bağımlılıkları yükleyin
npm install

# Geliştirici sunucusunu başlatın
npm run dev
```

### 3. Optimizasyon Testi, Analiz ve Sunum Slaytları
Projenin temel motorunu test etmek, MILP doğrulaması yapmak ve analiz materyallerini üretmek için:

```bash
# Geliştirilmiş GA ve MILP kesin çözümünü karşılaştırmalı çalıştırmak (0 ihlal kanıtı):
python scripts/run_optimization.py

# Genetik algoritmanın yakınsama grafiğini (convergence_graph.png) üretmek için:
python scripts/analysis.py

# Sunum slaytını (ENS001_Team12_Sunum.pptx) otomatik oluşturmak için:
python scripts/create_pptx.py
```
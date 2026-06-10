import { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, Tooltip, ZoomControl } from 'react-leaflet';
import searoute from 'searoute-js';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './App.css';

// Çeviri Sözlüğü
const t = {
  tr: {
    settings: "Ayarlar", mapTheme: "Harita Teması", switchToLight: "☀️ Aydınlık Moda Geç", switchToDark: "🌙 Karanlık Moda Geç",
    routeLines: "Rota Çizgileri", hide: "Gizle 🙈", show: "Göster 👁️", title: "Lojistik Simülasyonu", calculating: "Hesaplanıyor...",
    startSim: "🚀 Simülasyonu Başlat", cost: "Maliyet", savings: "Tasarruf", routeDetails: "Sefer Detayları", distance: "Sefer Mesafesi:",
    eta: "Tahmini Süre (ETA):", fillRate: "Doluluk", opCost: "Operasyon Maliyeti:", revenue: "Hizmet Bedeli (Gelir):", profit: "Net Kâr:",
    incentive: "(Teşvik)", day: "Gün", hour: "Saat", startPoint: "🟢 Başlangıç Noktası", endPoint: "🔴 Varış Noktası", interPoint: "🟡 Ara Durak",
    port: "Liman", ship: "Gemi", route: "Rota", optProcess: "Optimizasyon Süreci (Genetik Algoritma)", langSelect: "Dil / Language",
    portNames: {}
  },
  en: {
    settings: "Settings", mapTheme: "Map Theme", switchToLight: "☀️ Switch to Light", switchToDark: "🌙 Switch to Dark",
    routeLines: "Route Lines", hide: "Hide 🙈", show: "Show 👁️", title: "Logistics Simulation", calculating: "Calculating...",
    startSim: "🚀 Start Simulation", cost: "Cost", savings: "Savings", routeDetails: "Route Details", distance: "Distance:",
    eta: "Estimated Time (ETA):", fillRate: "Load", opCost: "Operation Cost:", revenue: "Revenue:", profit: "Net Profit:",
    incentive: "(Incentive)", day: "Days", hour: "Hours", startPoint: "🟢 Start Point", endPoint: "🔴 End Point", interPoint: "🟡 Intermediate Stop",
    port: "Port", ship: "Ship", route: "Route", optProcess: "Optimization Process (Genetic Algorithm)", langSelect: "Dil / Language",
    portNames: {}
  }
};

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Dinamik Gemi İkonu Üretici
const createShipIcon = (color, index = 0) => {
  const shipEmojis = ["🚢", "🛳️", "⛴️", "🛥️", "🚤"];
  const emoji = shipEmojis[index % shipEmojis.length];
  return new L.DivIcon({
    className: 'gliding-ship-marker',
    html: `<div class="neon-ship-icon" style="text-shadow: 0 0 10px ${color}, 0 0 20px ${color}; color: ${color};">${emoji}</div>`,
    iconSize: [35, 35],
    iconAnchor: [17, 17]
  });
};

// Türkiye Limanları ve Rastgele Koordinat Üretici
const getCoordinateAndName = (locId) => {
  const predefined = {
    "L1": { name: "L1", coords: [40.965, 28.684] },
    "L2": { name: "L2", coords: [38.438, 27.151] },
    "M0": { name: "M0", coords: [1.264, 103.840] },
    "M1": { name: "M1", coords: [31.200, 29.918] },
    "M2": { name: "M2", coords: [41.385, 2.173] },
    "M3": { name: "M3", coords: [21.485, 39.192] },
    "M4": { name: "M4", coords: [43.296, 5.369] },
    "M5": { name: "M5", coords: [33.605, -7.632] },
    "M6": { name: "M6", coords: [18.943, 72.836] },
    "M7": { name: "M7", coords: [37.945, 23.636] },
    "M8": { name: "M8", coords: [25.011, 55.055] },
    "M9": { name: "M9", coords: [-33.918, 18.423] },
    "M10": { name: "M10", coords: [51.949, 4.148] },
    "M11": { name: "M11", coords: [40.838, 14.269] },
    "M12": { name: "M12", coords: [31.222, 121.458] },
    "M13": { name: "M13", coords: [35.618, 139.771] },
    "M14": { name: "M14", coords: [14.675, -17.433] },
  };

  if (predefined[locId]) return predefined[locId];
  if (locId === "Liman") return predefined["L2"]; // Legacy fallback

  // Diğer ID'ler için Türkiye etrafında sahte koordinatlar üretelim
  const idNum = parseInt(locId.replace(/\D/g, '') || 0);

  const lat = 36.5 + ((idNum * 13) % 55) / 10.0;
  const lng = 26.5 + ((idNum * 17) % 150) / 10.0;
  const name = locId;

  return { name, coords: [lat, lng], originalName: name };
};

// --- KESİNTİSİZ HAREKET EDEN GEMİ BİLEŞENİ (React DOM Bypass - 60FPS) ---
const AnimatedShip = ({ route, pathPositions, color, index, lang }) => {
  const markerRef = useRef(null);

  useEffect(() => {
    if (!pathPositions || pathPositions.length < 2) return;

    let progress = 0;
    let animationFrameId;

    // Tüm rotanın fiziksel (geometrik) uzunluğunu hesaplıyoruz
    let totalDist = 0;
    for (let i = 0; i < pathPositions.length - 1; i++) {
      const dx = pathPositions[i + 1][0] - pathPositions[i][0];
      const dy = pathPositions[i + 1][1] - pathPositions[i][1];
      totalDist += Math.sqrt(dx * dx + dy * dy);
    }

    // İstenilen sabit hız (Tüm gemiler için aynı olacak)
    const constantSpeed = 0.0234; // %50 daha hızlandırıldı
    // Uzun rotada 'progress' yavaş artmalı, kısa rotada hızlı artmalı ki hızlar EŞİT olsun.
    const progressIncrement = totalDist > 0 ? (constantSpeed / totalDist) : 0.01;

    const animate = () => {
      progress += progressIncrement; // Artık her gemi aynı fiziksel hıza sahip!

      if (progress >= 1) {
        progress = 1; // Varış noktasına ulaştıysa dur
      }

      const totalSegments = pathPositions.length - 1;
      const exactIndex = progress * totalSegments;
      const lowerIndex = Math.floor(exactIndex);
      const upperIndex = Math.min(lowerIndex + 1, totalSegments);

      const segmentProgress = exactIndex - lowerIndex;

      const start = pathPositions[lowerIndex];
      const end = pathPositions[upperIndex];

      const lat = start[0] + (end[0] - start[0]) * segmentProgress;
      const lng = start[1] + (end[1] - start[1]) * segmentProgress;

      // React state kullanmadan doğrudan Leaflet objesini güncelliyoruz.
      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lng]);
      }

      // Döngüye girmemesi için hedefe ulaştıysa (progress === 1) requestAnimationFrame çağırma
      if (progress < 1) {
        animationFrameId = requestAnimationFrame(animate);
      }
    };

    // Animasyonu başlat
    animationFrameId = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(animationFrameId);
  }, [pathPositions]);

  return (
    <Marker ref={markerRef} position={pathPositions[0]} icon={createShipIcon(color, index)}>
      <Popup>
        <strong>{t[lang].ship}: {route.ship_id}</strong><br />
        {t[lang].route}: {route.route_id}
      </Popup>
    </Marker>
  );
};

function App() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [simKey, setSimKey] = useState(0);

  // UI States
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showRoutes, setShowRoutes] = useState(true);
  const [lang, setLang] = useState("en"); // Varsayılan ingilizce istendiği için
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);

  // Grafik verisi
  const chartData = metrics?.history ? metrics.history.map((cost, idx) => ({
    generation: idx,
    maliyet: Math.abs(cost)
  })) : [];

  const startSimulation = async () => {
    setLoading(true);
    setRoutes([]);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/optimize';
      const response = await axios.get(apiUrl);
      if (response.data.status === "success") {
        setRoutes(response.data.routes);
        setMetrics({
          finalCost: response.data.final_cost,
          saved: response.data.history[0] - response.data.final_cost,
          history: response.data.history
        });
        setSimKey(prev => prev + 1);
      }
    } catch (error) {
      console.error("API Hatası", error);
    }
    setLoading(false);
  };

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', backgroundColor: isDarkMode ? '#0f1115' : '#f3f4f6', overflow: 'hidden' }}>

      {/* Sağ Üst Seçenekler Butonu */}
      <button className="settings-btn" onClick={() => setIsSidebarOpen(true)}>⚙️</button>

      {/* Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : ''} ${!isDarkMode ? 'light' : ''}`}>
        <button className="close-btn" onClick={() => setIsSidebarOpen(false)}>✖</button>
        <h2>{t[lang].settings}</h2>
        <div className="setting-item">
          <span>{t[lang].langSelect}</span>
          <button className="toggle-btn" onClick={() => setLang(lang === "tr" ? "en" : "tr")}>
            {lang === "tr" ? '🇺🇸 English' : '🇹🇷 Türkçe'}
          </button>
        </div>
        <div className="setting-item">
          <span>{t[lang].mapTheme}</span>
          <button className="toggle-btn" onClick={() => setIsDarkMode(!isDarkMode)}>
            {isDarkMode ? t[lang].switchToLight : t[lang].switchToDark}
          </button>
        </div>
        <div className="setting-item">
          <span>{t[lang].routeLines}</span>
          <button className="toggle-btn" onClick={() => setShowRoutes(!showRoutes)}>
            {showRoutes ? t[lang].hide : t[lang].show}
          </button>
        </div>
      </div>

      {/* Orta Alt Panel */}
      <div className={`glass-panel ${!isDarkMode ? 'light' : ''}`}>
        <div>
          <h1 className="title">{t[lang].title}</h1>
        </div>
        
        <button className="start-btn" onClick={startSimulation} disabled={loading}>
          {loading ? t[lang].calculating : t[lang].startSim}
        </button>
      </div>

      {/* Sağ Alt Analiz Paneli */}
      {metrics && !loading && (
        <div className={`glass-panel right-panel ${!isDarkMode ? 'light' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: rightPanelOpen ? '15px' : '0' }}>
            <h3 style={{ margin: 0, fontSize: '16px', color: isDarkMode ? '#e5e7eb' : '#1f2937' }}>
              {lang === "tr" ? "Genel İstatistikler" : "Overall Statistics"}
            </h3>
            <button onClick={() => setRightPanelOpen(!rightPanelOpen)} style={{ background: 'none', border: 'none', color: isDarkMode ? '#e5e7eb' : '#1f2937', cursor: 'pointer', fontSize: '16px' }}>
              {rightPanelOpen ? '▼' : '▲'}
            </button>
          </div>
          
          {rightPanelOpen && (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', width: '100%', marginBottom: '20px' }}>
                <div className="metric">
                  <span className="label">{t[lang].cost}</span>
                  <span className="cost-val" style={{ fontSize: '24px' }}>${metrics.finalCost.toLocaleString()}</span>
                </div>
                <div className="metric">
                  <span className="label">{t[lang].savings}</span>
                  <span className="savings-val" style={{ fontSize: '24px' }}>${metrics.saved.toLocaleString()}</span>
                </div>
              </div>

              {chartData.length > 0 && (
                <div className="chart-container" style={{ height: '240px', width: '100%', paddingBottom: '30px' }}>
                  <h4 style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '10px', textAlign: 'center' }}>{t[lang].optProcess}</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 40 }}>
                      <XAxis 
                        dataKey="generation" 
                        stroke="#6b7280" 
                        fontSize={10} 
                        tick={{ fill: '#9ca3af' }}
                        label={{ value: lang === 'tr' ? 'Nesil (Gen)' : 'Generation', position: 'bottom', fill: '#9ca3af', fontSize: 11 }} 
                      />
                      <YAxis 
                        domain={['auto', 'auto']} 
                        stroke="#6b7280" 
                        fontSize={10} 
                        tick={{ fill: '#9ca3af' }}
                        tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
                        label={{ value: lang === 'tr' ? 'Maliyet (Cost)' : 'Cost', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 11, offset: -5 }} 
                      />
                      <RechartsTooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '5px', fontSize: '12px', color: '#fff' }} itemStyle={{ color: '#00f3ff' }} />
                      <Line type="monotone" dataKey="maliyet" stroke="#00f3ff" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Sol Alt Rota Detayları Tablosu */}
      {metrics && !loading && routes.length > 0 && (
        <div className={`glass-panel details-panel ${!isDarkMode ? 'light' : ''}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: leftPanelOpen ? '15px' : '0' }}>
            <h3 style={{ margin: 0 }}>{t[lang].routeDetails}</h3>
            <button onClick={() => setLeftPanelOpen(!leftPanelOpen)} style={{ background: 'none', border: 'none', color: isDarkMode ? '#e5e7eb' : '#1f2937', cursor: 'pointer', fontSize: '16px' }}>
              {leftPanelOpen ? '▼' : '▲'}
            </button>
          </div>
          
          {leftPanelOpen && (
            <div className="routes-scroll">
            {routes.map((r, i) => {
              const rStops = r.stops || [];
              if (rStops.length < 2) return null;

              // Rota ismini tüm durakları içerecek şekilde oluştur
              const fullRoutePath = rStops.map(stop => {
                const locData = getCoordinateAndName(stop);
                return t[lang].portNames[locData.name] || locData.name;
              }).join(" ➔ ");

              // Gelir ve kâr hesaplaması
              const cost = r.cost;
              const revenue = Math.abs(cost) * 1.35;
              const profit = revenue - cost;

              // Para formatlayıcı yardımcı fonksiyon
              const formatMoney = (amount, isCost = false) => {
                const absAmount = Math.abs(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                if (isCost) {
                  return amount >= 0 ? `-$${absAmount}` : `+$${absAmount} ${t[lang].incentive}`;
                }
                return amount >= 0 ? `+$${absAmount}` : `-$${absAmount}`;
              };

              // Mesafeyi hesapla
              let distanceKm = 0;
              let durationHours = 0;
              for (let k = 0; k < rStops.length - 1; k++) {
                const originCoord = getCoordinateAndName(rStops[k]).coords;
                const destCoord = getCoordinateAndName(rStops[k + 1]).coords;
                try {
                  // searoute expects [lng, lat]
                  const path = searoute([originCoord[1], originCoord[0]], [destCoord[1], destCoord[0]]);
                  distanceKm += (path.properties.length * 1.852); // Convert nautical miles to km
                  durationHours += path.properties.duration_hours || (distanceKm / 40.0);
                } catch (e) {
                  // Fallback to straight line geographic distance approximation
                  const dx = destCoord[0] - originCoord[0];
                  const dy = destCoord[1] - originCoord[1];
                  const distFallback = Math.sqrt(dx * dx + dy * dy) * 111.0;
                  distanceKm += distFallback;
                  durationHours += (distFallback / 40.0);
                }
              }

              const etaDays = Math.floor(durationHours / 24);
              const etaHours = Math.round(durationHours % 24);
              const etaString = etaDays > 0 ? `${etaDays} ${t[lang].day} ${etaHours} ${t[lang].hour}` : `${etaHours} ${t[lang].hour}`;

              const capacity = r.capacity || 10000;
              const load = r.total_load || 0;
              const fillPercentage = Math.min(100, Math.max(0, (load / capacity) * 100)).toFixed(1);

              return (
                <div key={i} className="route-detail-item">
                  <div className="rd-header">
                    <span className="rd-ship">{r.ship_id}</span>
                    <span className="rd-route-name" style={{ lineHeight: '1.6' }}>{fullRoutePath}</span>
                  </div>

                  <div className="rd-stats">
                    <div className="rd-stat-row">
                      <span className="rd-label">{t[lang].distance}</span>
                      <span className="rd-val distance">{distanceKm.toFixed(0)} km</span>
                    </div>
                    <div className="rd-stat-row">
                      <span className="rd-label">{t[lang].eta}</span>
                      <span className="rd-val distance">{etaString}</span>
                    </div>
                    <div className="rd-stat-row capacity-row" style={{ marginTop: '5px' }}>
                      <span className="rd-label">{t[lang].fillRate} ({load} / {capacity} TEU):</span>
                      <span className="rd-val">%{fillPercentage}</span>
                    </div>
                    <div className="capacity-bar-bg">
                      <div className="capacity-bar-fill" style={{ width: `${fillPercentage}%`, backgroundColor: fillPercentage > 90 ? '#ef4444' : fillPercentage > 75 ? '#f59e0b' : '#10b981' }}></div>
                    </div>
                    <div className="rd-stat-row" style={{ marginTop: '5px' }}>
                      <span className="rd-label">{t[lang].opCost}</span>
                      <span className="rd-val cost">{formatMoney(cost, true)}</span>
                    </div>
                    <div className="rd-stat-row">
                      <span className="rd-label">{t[lang].revenue}</span>
                      <span className="rd-val revenue">{formatMoney(revenue)}</span>
                    </div>
                    <div className="rd-stat-row profit-row">
                      <span className="rd-label">{t[lang].profit}</span>
                      <span className="rd-val profit">{formatMoney(profit)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
            </div>
          )}
        </div>
      )}

      <MapContainer center={[30, 30]} zoom={3} style={{ height: '100%', width: '100%', zIndex: 1 }} zoomControl={false}>
        <ZoomControl position="topright" />
        <TileLayer
          url={isDarkMode ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"}
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        {routes.map((route, index) => {
          let rawStops = route.stops || [];

          // HATA DÜZELTME: Eğer backend sadece 1 varış noktası döndürdüyse (örn: ["M1"])
          // Rota oluşturamayız. Bu yüzden gemi ID'sine göre mantıklı bir başlangıç limanı ekliyoruz!
          if (rawStops.length === 1) {
            const shipIndex = parseInt(route.ship_id.replace(/\D/g, '') || 1);
            const startLocId = `M${shipIndex % 10}`;
            const finalStartId = startLocId === rawStops[0] ? `M${(shipIndex + 1) % 10}` : startLocId;
            rawStops = [finalStartId, ...rawStops];
            route.stops = rawStops; // Detay panelinde de görünmesi için güncelliyoruz
          }

          // Rota oluşturabilmek için en az 2 lokasyon olmalı
          if (rawStops.length < 2) return null;

          const routeData = rawStops.map(stop => getCoordinateAndName(stop));
          const stopCoords = routeData.map(d => d.coords);
          const stopNames = routeData.map(d => t[lang].portNames[d.name] || d.name);

          // Deniz Yolu Koordinatlarını Hesapla (searoute)
          let seaPathPositions = [];
          for (let k = 0; k < stopCoords.length - 1; k++) {
            const origin = [stopCoords[k][1], stopCoords[k][0]]; // searoute expects [lng, lat]
            const dest = [stopCoords[k + 1][1], stopCoords[k + 1][0]];

            try {
              const seaPath = searoute(origin, dest);
              const leafletCoords = seaPath.geometry.coordinates.map(coord => [coord[1], coord[0]]);

              if (k > 0) {
                leafletCoords.shift(); // Tekrarlayan noktayı kaldır
              }
              seaPathPositions = [...seaPathPositions, ...leafletCoords];
            } catch (err) {
              console.warn("Searoute hatası, düz çizgiye dönülüyor", err);
              if (k === 0) seaPathPositions.push(stopCoords[k]);
              seaPathPositions.push(stopCoords[k + 1]);
            }
          }

          const routeColor = index % 2 === 0 ? "#00f3ff" : "#ff00e4";

          return (
            <div key={`${simKey}-${route.route_id}-${index}`}>
              {showRoutes && (
                <Polyline positions={seaPathPositions} color={routeColor} weight={4} dashArray="10, 15" opacity={0.6} />
              )}

              {stopCoords.map((pos, i) => (
                <Marker key={`stop-${i}`} position={pos}>
                  <Tooltip permanent direction="bottom" offset={[0, 10]} opacity={0.85}>
                    <span style={{ fontSize: '11px', fontWeight: '600' }}>{stopNames[i]}</span>
                  </Tooltip>
                  <Popup>
                    <strong>
                      {i === 0 ? t[lang].startPoint : i === stopCoords.length - 1 ? t[lang].endPoint : t[lang].interPoint}
                    </strong><br />
                    {t[lang].port}: {stopNames[i]}
                  </Popup>
                </Marker>
              ))}

              <AnimatedShip route={route} pathPositions={seaPathPositions} color={routeColor} index={index} lang={lang} />
            </div>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default App;
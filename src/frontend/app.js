/* ==========================================================================
   AquaSentinel AI — Interactive Dashboard Application Logic
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // Data Containers
    let rawData = [];
    let processedData = {
        dates: [],
        chl: [],
        sst: [],
        quality: [],
        mapData: {} // Cache for regional multiplier offsets
    };

    let predictionsDb = null;

    // State Variables
    let currentDateIndex = 0;
    let isPlaying = false;
    let playInterval = null;
    let selectedRegion = 'all'; // 'all', 'izmit', 'gemlik', 'adalar', 'bandirma', 'tekirdag'
    let activeLayer = 'chl'; // 'chl', 'sst', 'risk'
    let trendChart = null;

    // Region Coefficients (To simulate spatial variation when clicking map regions)
    const regionCoefficients = {
        all: { chl: 1.0, sst: 1.0, label: 'Tüm Marmara Denizi' },
        izmit: { chl: 1.45, sst: 1.05, label: 'İzmit Körfezi' },
        gemlik: { chl: 1.30, sst: 1.02, label: 'Gemlik Körfezi' },
        adalar: { chl: 1.10, sst: 0.98, label: 'Adalar Bölgesi' },
        bandirma: { chl: 1.25, sst: 1.01, label: 'Bandırma & Erdek' },
        tekirdag: { chl: 0.85, sst: 0.95, label: 'Tekirdağ Açıkları' }
    };

    // DOM Elements
    const activeDateText = document.getElementById('active-date-text');
    const riskGaugeFill = document.getElementById('risk-gauge-fill');
    const riskValueText = document.getElementById('risk-value-text');
    const riskStatusText = document.getElementById('risk-status-text');
    const chlValueText = document.getElementById('chl-value-text');
    const chlStatusDesc = document.getElementById('chl-status-desc');
    const chlIndicatorDot = document.getElementById('chl-indicator-dot');
    const sstValueText = document.getElementById('sst-value-text');
    const sstStatusDesc = document.getElementById('sst-status-desc');
    const sstIndicatorDot = document.getElementById('sst-indicator-dot');
    const qualityValueText = document.getElementById('quality-value-text');
    const selectedRegionText = document.getElementById('selected-region-text');
    const btnResetRegion = document.getElementById('btn-reset-region');

    // Playback & Controls
    const btnPlay = document.getElementById('btn-play');
    const playIcon = document.getElementById('play-icon');
    const timelineSlider = document.getElementById('timeline-slider');
    const sliderStartDate = document.getElementById('slider-start-date');
    const sliderCurrentDate = document.getElementById('slider-current-date');
    const sliderEndDate = document.getElementById('slider-end-date');

    // UI Modules & Feeds
    const aiThoughtContent = document.getElementById('ai-thought-content');
    const alarmFeedContent = document.getElementById('alarm-feed-content');
    const activeAlarmCount = document.getElementById('active-alarm-count');

    // Modals & Buttons
    const btnQuickReport = document.getElementById('btn-quick-report');
    const reportModal = document.getElementById('report-modal');
    const modalReportBody = document.getElementById('modal-report-body');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnCloseModalFooter = document.getElementById('btn-close-modal-footer');
    const btnPrintReport = document.getElementById('btn-print-report');

    // Layer buttons
    const layerChl = document.getElementById('layer-chl');
    const layerSst = document.getElementById('layer-sst');
    const layerRisk = document.getElementById('layer-risk');

    // Map Leaflet Variables
    let map = null;
    const regionCircles = {};
    const regionCoords = {
        izmit: { lat: 40.76, lng: 29.65, label: 'İzmit Körfezi' },
        gemlik: { lat: 40.43, lng: 29.05, label: 'Gemlik Körfezi' },
        adalar: { lat: 40.85, lng: 29.05, label: 'Adalar Bölgesi' },
        bandirma: { lat: 40.42, lng: 27.80, label: 'Bandırma & Erdek' },
        tekirdag: { lat: 40.80, lng: 27.45, label: 'Tekirdağ Açıkları' }
    };

    // API Key & Live LLM Elements
    const apiKeyInput = document.getElementById('api-key-input');
    const btnSaveApiKey = document.getElementById('btn-save-api-key');
    const btnClearApiKey = document.getElementById('btn-clear-api-key');
    const btnToggleKeyVisibility = document.getElementById('btn-toggle-key-visibility');
    const apiStatusBadge = document.getElementById('api-status-badge');
    let userApiKey = localStorage.getItem('gemini_api_key') || '';

    // Test buttons
    const btnGenMock = document.getElementById('btn-gen-mock');
    const btnClearCache = document.getElementById('btn-clear-cache');

    // Step 1: Fetch and Parse CSV Data
    async function loadData() {
        showAILog("Sistem başlatılıyor...");
        showAILog("Zaman serisi CSV verileri okunuyor...");

        // Try to load predictions database from machine learning model
        try {
            const predResponse = await fetch('predictions.json');
            if (predResponse.ok) {
                predictionsDb = await predResponse.json();
                showAILog("[ML MODEL] Eğitilmiş Random Forest model tahminleri başarıyla yüklendi!");
            } else {
                showAILog("[ML MODEL] Tahmin veritabanı bulunamadı. Formül bazlı hesaplama kullanılacak.");
            }
        } catch (e) {
            showAILog("[ML MODEL] Tahmin veritabanı yüklenemedi. Formül bazlı hesaplama kullanılacak.");
        }

        try {
            // Vercel statik sunumu için öncelikle yerel CSV'yi dene, ardından üst dizine bak
            let response = await fetch('marmara_time_series.csv');
            if (!response.ok) {
                response = await fetch('../../data/processed/marmara_time_series.csv');
            }
            if (!response.ok) {
                throw new Error("CSV dosyası sunucudan okunamadı.");
            }
            const csvText = await response.text();
            parseAndProcessData(csvText);
        } catch (error) {
            showAILog(`[BİLGİ] Veri okuma: ${error.message}`);
            showAILog("Arayüz için varsayılan zaman serisi yükleniyor...");
            loadFallbackMockData();
        }
    }

    // Parse standard YZTA format: date,parameter_type,mean_value,std_value...
    function parseAndProcessData(csvText) {
        const lines = csvText.trim().split('\n');
        if (lines.length < 2) {
            showAILog("[HATA] Boş veri seti algılandı.", "alert-msg");
            loadFallbackMockData();
            return;
        }

        const headers = lines[0].split(',');
        const data = [];

        for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            const currentLine = lines[i].split(',');
            const row = {};
            headers.forEach((header, index) => {
                row[header.trim()] = currentLine[index] ? currentLine[index].trim() : '';
            });
            data.push(row);
        }

        rawData = data;
        processTimeSeries(data);
    }

    // Process parsed data to build time-series arrays
    function processTimeSeries(data) {
        // Group by Date
        const grouped = {};
        data.forEach(item => {
            const date = item.date;
            if (!grouped[date]) {
                grouped[date] = { date, chlorophyll_a: null, sst: null, quality_ratio: 0.85 };
            }
            if (item.parameter_type === 'chlorophyll_a') {
                grouped[date].chlorophyll_a = parseFloat(item.mean_value);
                grouped[date].quality_ratio = parseFloat(item.quality_ratio);
            } else if (item.parameter_type === 'sst') {
                grouped[date].sst = parseFloat(item.mean_value);
            }
        });

        // Convert to sorted arrays
        const sortedDates = Object.keys(grouped).sort();
        processedData.dates = sortedDates;
        processedData.chl = sortedDates.map(d => grouped[d].chlorophyll_a || 1.5);
        processedData.sst = sortedDates.map(d => grouped[d].sst || 15.0);
        processedData.quality = sortedDates.map(d => grouped[d].quality_ratio || 0.85);

        if (processedData.dates.length === 0) {
            loadFallbackMockData();
            return;
        }

        showAILog(`Zaman serisi başarıyla işlendi. Toplam ${processedData.dates.length} tarih noktası yüklendi.`);
        initDashboard();
    }

    // Fallback Mock generator in case the CSV doesn't exist yet
    function loadFallbackMockData() {
        showAILog("İstemci tarafında test veri seti üretiliyor...");
        const dates = [];
        const chl = [];
        const sst = [];
        const quality = [];

        // Generate 60 days of mock data for 2024
        const startDate = new Date('2024-05-01');
        for (let i = 0; i < 60; i++) {
            const currentDate = new Date(startDate);
            currentDate.setDate(startDate.getDate() + i * 3);
            const dateStr = currentDate.toISOString().split('T')[0];

            // Simulating spring-summer trends
            const dayOfSimulation = i / 60;
            const seasonalTemp = 14 + 12 * Math.sin(dayOfSimulation * Math.PI / 2);
            const baseChl = 1.2 + 5.0 * Math.sin(dayOfSimulation * Math.PI);
            const noiseChl = (Math.random() - 0.5) * 0.8;
            const noiseTemp = (Math.random() - 0.5) * 0.6;

            // Add a spike during June (mid simulation)
            let chlSpike = 0;
            if (i > 25 && i < 40) {
                chlSpike = 6.5 + (Math.random() * 4.0);
            }

            dates.push(dateStr);
            chl.push(Math.max(0.2, parseFloat((baseChl + noiseChl + chlSpike).toFixed(2))));
            sst.push(parseFloat((seasonalTemp + noiseTemp).toFixed(1)));
            quality.push(parseFloat((0.75 + Math.random() * 0.2).toFixed(2)));
        }

        processedData.dates = dates;
        processedData.chl = chl;
        processedData.sst = sst;
        processedData.quality = quality;

        initDashboard();
    }

    function getLayerColor() {
        if (activeLayer === 'chl') return '#06b6d4'; // Teal
        if (activeLayer === 'sst') return '#f97316'; // Orange
        return '#ef4444'; // Red for Risk
    }

    async function ensureLeafletLoaded() {
        if (window.L) return true;

        return new Promise((resolve) => {
            showAILog("[SİSTEM] Leaflet kütüphanesi yükleniyor...");

            // Add CSS
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
            document.head.appendChild(link);

            // Add JS
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
            script.onload = () => {
                showAILog("[SİSTEM] Leaflet kütüphanesi başarıyla yüklendi.");
                resolve(true);
            };
            script.onerror = () => {
                showAILog("[HATA] Leaflet CDN yüklenemedi. İnternet bağlantısını kontrol edin.", "alert-msg");
                resolve(false);
            };
            document.head.appendChild(script);
        });
    }

    function initMap() {
        if (map) return; // Prevent double init

        // Center map to Marmara Sea
        map = L.map('marmara-map', {
            zoomControl: false,
            minZoom: 7,
            maxZoom: 10,
            attributionControl: false
        }).setView([40.72, 28.45], 8);

        // Add Dark Matter Tile Layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);

        L.control.zoom({ position: 'topright' }).addTo(map);

        // Create interactive circles for each region
        Object.keys(regionCoords).forEach(key => {
            const coord = regionCoords[key];
            const circle = L.circle([coord.lat, coord.lng], {
                radius: 10000, // 10km
                fillColor: '#06b6d4',
                fillOpacity: 0.5,
                color: '#06b6d4',
                weight: 1.5
            }).addTo(map);

            circle.on('click', () => {
                selectRegion(key);
            });

            // Custom tooltip
            circle.bindTooltip(`<strong>${coord.label}</strong><br><span style="font-size:10px;">Gözlemlemek için tıklayın</span>`, {
                direction: 'top',
                className: 'custom-map-tooltip'
            });

            regionCircles[key] = circle;
        });

        // Add map click background to reset region
        map.on('click', (e) => {
            if (e.originalEvent && (e.originalEvent.target.id === 'marmara-map' || e.originalEvent.target.classList.contains('leaflet-container'))) {
                selectRegion('all');
            }
        });
    }

    // Step 2: Initialize UI, Slider, Maps and Charts
    async function initDashboard() {
        // Init Slider Limits
        if (timelineSlider && processedData.dates.length > 0) {
            timelineSlider.min = 0;
            timelineSlider.max = processedData.dates.length - 1;
            timelineSlider.value = 0;
            currentDateIndex = 0;
        }

        if (sliderStartDate && processedData.dates.length > 0) {
            sliderStartDate.textContent = formatDate(processedData.dates[0]);
        }
        if (sliderEndDate && processedData.dates.length > 0) {
            sliderEndDate.textContent = formatDate(processedData.dates[processedData.dates.length - 1]);
        }

        // 1. UPDATE METRIC CARDS & DATA VIEW IMMEDIATELY
        updateDateView();

        // 2. Ensure Leaflet is loaded and init Map
        try {
            const leafletReady = await ensureLeafletLoaded();
            if (leafletReady) {
                initMap();
            } else {
                showAILog("[HATA] Harita yüklenemedi (Leaflet kütüphanesi eksik).", "alert-msg");
            }
        } catch (e) {
            console.warn("Map init issue:", e);
        }

        // 3. Init Chart
        try {
            buildChart();
        } catch (e) {
            console.warn("Chart init issue:", e);
        }

        // 4. Bind interactive events
        setupEvents();
    }

    // Setup interactive event listeners
    function setupEvents() {
        // Slider Change
        timelineSlider?.addEventListener('input', (e) => {
            currentDateIndex = parseInt(e.target.value);
            updateDateView();
        });

        // Play/Pause Playback
        btnPlay?.addEventListener('click', () => {
            if (isPlaying) {
                pausePlayback();
            } else {
                startPlayback();
            }
        });

        // Layer Toggles
        layerChl?.addEventListener('click', () => setLayer('chl'));
        layerSst?.addEventListener('click', () => setLayer('sst'));
        layerRisk?.addEventListener('click', () => setLayer('risk'));

        // Reset region filter
        btnResetRegion?.addEventListener('click', () => {
            selectRegion('all');
        });

        // Modals
        btnQuickReport?.addEventListener('click', openReportModal);
        btnCloseModal?.addEventListener('click', closeReportModal);
        btnCloseModalFooter?.addEventListener('click', closeReportModal);
        btnPrintReport?.addEventListener('click', () => window.print());

        // API Key Management Handlers
        if (userApiKey && apiKeyInput) {
            apiKeyInput.value = userApiKey;
            updateApiStatusBadge(true);
        }

        btnSaveApiKey?.addEventListener('click', () => {
            const val = apiKeyInput ? apiKeyInput.value.trim() : '';
            if (val) {
                userApiKey = val;
                localStorage.setItem('gemini_api_key', val);
                updateApiStatusBadge(true);
                showAILog("Google Gemini API anahtarı kaydedildi. Canlı AI yorumlama aktif!");
                updateDateView();
            } else {
                showAILog("[UYARI] Geçerli bir API anahtarı giriniz.", "alert-msg");
            }
        });

        btnClearApiKey?.addEventListener('click', () => {
            userApiKey = '';
            if (apiKeyInput) apiKeyInput.value = '';
            localStorage.removeItem('gemini_api_key');
            updateApiStatusBadge(false);
            showAILog("API anahtarı temizlendi. Varsayılan hazır ajan metinlerine dönüldü.");
            updateDateView();
        });

        btnToggleKeyVisibility?.addEventListener('click', () => {
            if (apiKeyInput && apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
            } else if (apiKeyInput) {
                apiKeyInput.type = 'password';
            }
        });

        // Simulation Triggers (Simulate client-side process)
        btnGenMock?.addEventListener('click', () => {
            showAILog("[UYARI] Yeniden sahte veri üretme tetiklendi...", "alert-msg");
            loadFallbackMockData();
            showAILog("Sahte veri seti yenilendi ve yüklendi.");
        });

        btnClearCache?.addEventListener('click', () => {
            showAILog("Zaman serisi sıfırlandı.");
            processedData = { dates: [], chl: [], sst: [], quality: [] };
            loadFallbackMockData();
        });
    }

    // Step 3: Playback Logic
    function startPlayback() {
        isPlaying = true;
        btnPlay.classList.add('btn-secondary');
        btnPlay.classList.remove('btn-primary');
        playIcon.setAttribute('data-lucide', 'pause');
        lucide.createIcons();

        playInterval = setInterval(() => {
            currentDateIndex++;
            if (currentDateIndex >= processedData.dates.length) {
                currentDateIndex = 0; // Loop back
            }
            timelineSlider.value = currentDateIndex;
            updateDateView();
        }, 1500); // 1.5s per date frame
    }

    function pausePlayback() {
        isPlaying = false;
        btnPlay.classList.add('btn-primary');
        btnPlay.classList.remove('btn-secondary');
        playIcon.setAttribute('data-lucide', 'play');
        lucide.createIcons();
        clearInterval(playInterval);
    }

    // Step 4: Update Dashboard View based on selected index
    function updateDateView() {
        if (!processedData.dates || processedData.dates.length === 0) return;

        const date = processedData.dates[currentDateIndex];
        const baseChl = processedData.chl[currentDateIndex];
        const baseSst = processedData.sst[currentDateIndex];
        const qRatio = processedData.quality[currentDateIndex];

        // Apply regional modifiers (fallback values)
        const coeff = regionCoefficients[selectedRegion] || regionCoefficients['all'];
        let finalChl = parseFloat((baseChl * coeff.chl).toFixed(2));
        let finalSst = parseFloat((baseSst * coeff.sst).toFixed(1));
        let riskScore = calculateRiskIndex(finalChl, finalSst);

        // Check if we have scikit-learn model predictions for this date and region
        let isRealPrediction = false;
        if (predictionsDb && predictionsDb[date] && predictionsDb[date][selectedRegion]) {
            const pred = predictionsDb[date][selectedRegion];
            riskScore = Math.round(pred.risk_percentage);
            finalChl = pred.chlorophyll_a;
            finalSst = pred.sst;
            isRealPrediction = true;
        }

        // 1. Text & Metric Displays (Wrapped safely)
        if (activeDateText) activeDateText.textContent = formatDate(date);
        if (sliderCurrentDate) sliderCurrentDate.textContent = formatDate(date);
        if (chlValueText) chlValueText.textContent = finalChl;
        if (sstValueText) sstValueText.textContent = finalSst;
        if (qualityValueText) qualityValueText.textContent = `${Math.round(qRatio * 100)}%`;

        // 2. Risk Gauge & Indicators
        try { updateRiskGauge(riskScore); } catch (e) {}
        try { updateChlIndicator(finalChl); } catch (e) {}
        try { updateSstIndicator(finalSst); } catch (e) {}

        // 3. Update Map overlays dynamically
        try { updateMapOverlay(baseChl, baseSst); } catch (e) {}

        // 4. Update Alarm Lists and AI thoughts
        try { updateAlarmsAndThoughts(date, finalChl, finalSst, riskScore, isRealPrediction); } catch (e) {}

        // 5. Update Chart Highlight
        try { updateChartHighlight(); } catch (e) {}
    }

    // Calculate dynamic risk index (Chl weight 60%, SST weight 40%)
    function calculateRiskIndex(chl, sst) {
        // Chl normal range 0.5-3. Risk points linear 0 to 1 between 3 and 10
        let chlPoints = 0;
        if (chl > 3.0) {
            chlPoints = Math.min(1.0, (chl - 3.0) / 7.0);
        }

        // SST threshold 22. Risk points linear 0 to 1 between 18 and 26
        let sstPoints = 0;
        if (sst > 18.0) {
            sstPoints = Math.min(1.0, (sst - 18.0) / 8.0);
        }

        const riskVal = (chlPoints * 0.6 + sstPoints * 0.4) * 100;
        return Math.round(riskVal);
    }

    // Update risk gauge SVG
    function updateRiskGauge(riskScore) {
        riskValueText.textContent = `${riskScore}%`;

        // SVG dashoffset calculation (arc length = 125.6)
        const offset = 125.6 * (1 - riskScore / 100);
        riskGaugeFill.style.strokeDashoffset = offset;

        // Visual Colors based on Risk level
        let status = 'DÜŞÜK RİSK';
        let color = '#22c55e'; // Safe Green

        if (riskScore > 65) {
            status = 'CRITICAL ALARM';
            color = '#ef4444'; // Red
        } else if (riskScore > 30) {
            status = 'ORTA SEVİYE RİSK';
            color = '#eab308'; // Yellow
        }

        riskGaugeFill.style.stroke = color;
        riskStatusText.textContent = status;
        riskStatusText.style.color = color;
    }

    // Update Chlorophyll limits warning
    function updateChlIndicator(chl) {
        if (chl > 5.0) {
            chlIndicatorDot.className = 'trend-indicator danger';
            chlStatusDesc.textContent = 'Müsilaj Risk Sınırı Aşıldı';
        } else if (chl > 3.0) {
            chlIndicatorDot.className = 'trend-indicator warning';
            chlStatusDesc.textContent = 'Normal Üstü Yoğunluk';
        } else {
            chlIndicatorDot.className = 'trend-indicator normal';
            chlStatusDesc.textContent = 'Ekolojik Değer Normal';
        }
    }

    // Update SST warning
    function updateSstIndicator(sst) {
        if (sst > 22.0) {
            sstIndicatorDot.className = 'trend-indicator danger';
            sstStatusDesc.textContent = 'Tetikleme Eşiği Aşıldı';
        } else if (sst > 18.0) {
            sstIndicatorDot.className = 'trend-indicator warning';
            sstStatusDesc.textContent = 'Yüksek Sıcaklık';
        } else {
            sstIndicatorDot.className = 'trend-indicator normal';
            sstStatusDesc.textContent = 'Mevsim Normalleri';
        }
    }

    // Set Map Layer mode
    function setLayer(layerName) {
        activeLayer = layerName;
        [layerChl, layerSst, layerRisk].forEach(btn => btn.classList.remove('active'));

        if (layerName === 'chl') layerChl.classList.add('active');
        if (layerName === 'sst') layerSst.classList.add('active');
        if (layerName === 'risk') layerRisk.classList.add('active');

        updateDateView();
    }

    // Update map overlay glows based on parameters
    function updateMapOverlay(baseChl, baseSst) {
        const heatmapGroup = document.getElementById('heatmap-overlay-group');

        // Colors for each layer
        let defaultColor = '#06b6d4'; // Teal for Chlorophyll
        if (activeLayer === 'sst') defaultColor = '#f97316'; // Orange for SST
        if (activeLayer === 'risk') defaultColor = '#ef4444'; // Red for Risk

        // Update each Leaflet circle overlay
        Object.keys(regionCircles).forEach(point => {
            const circle = regionCircles[point];
            const regionCo = regionCoefficients[point];
            const localChl = baseChl * regionCo.chl;
            const localSst = baseSst * regionCo.sst;
            const localRisk = calculateRiskIndex(localChl, localSst);

            // Radius in meters based on intensity
            let intensity = 1.0;
            if (activeLayer === 'chl') {
                intensity = Math.min(2.5, localChl / 2.5);
            } else if (activeLayer === 'sst') {
                intensity = Math.min(2.0, (localSst - 10) / 10);
            } else {
                intensity = localRisk / 50;
            }

            const baseRadius = 8000; // 8km base
            const finalRadius = Math.max(4000, baseRadius * intensity);
            circle.setRadius(finalRadius);

            // Style options based on selection
            let strokeColor = defaultColor;
            let weight = 1.5;
            let fillOpacity = 0.5;

            if (selectedRegion === point) {
                strokeColor = '#ffffff';
                weight = 3.0;
                fillOpacity = 0.75;
            } else if (selectedRegion !== 'all') {
                fillOpacity = 0.15;
            }

            circle.setStyle({
                fillColor: defaultColor,
                color: strokeColor,
                weight: weight,
                fillOpacity: fillOpacity
            });
        });
    }

    // Region Selection Trigger
    function selectRegion(regionId) {
        selectedRegion = regionId;

        // Update Leaflet circle highlights
        const defaultColor = getLayerColor();
        Object.keys(regionCircles).forEach(key => {
            const circle = regionCircles[key];
            if (key === regionId) {
                circle.setStyle({
                    weight: 3.5,
                    color: '#ffffff',
                    fillOpacity: 0.75
                });
            } else {
                circle.setStyle({
                    weight: 1.5,
                    color: defaultColor,
                    fillOpacity: selectedRegion === 'all' ? 0.5 : 0.15
                });
            }
        });

        // Label update
        const label = regionCoefficients[regionId].label;
        selectedRegionText.textContent = label;

        if (regionId === 'all') {
            btnResetRegion.style.display = 'none';
        } else {
            btnResetRegion.style.display = 'inline-block';
        }

        showAILog(`[REGION] Analiz bölgesi değiştirildi: ${label}`);

        // Rebuild charts based on new region scaling coefficients
        buildChart();
        updateDateView();
    }

    // Dynamic Alarms Feed and AI Thought process Simulation
    function updateAlarmsAndThoughts(date, chl, sst, riskScore, isRealPrediction = false) {
        // Alarms Builder
        const alarms = [];
        if (chl > 5.0) {
            alarms.push({
                type: 'danger',
                msg: `KRİTİK: ${regionCoefficients[selectedRegion].label} bölgesinde Klorofil-a limit değeri aşıldı (${chl} mg/m³).`
            });
        } else if (chl > 3.0) {
            alarms.push({
                type: 'warning',
                msg: `UYARI: Klorofil-a seviyesi normalin üstünde seyrediyor (${chl} mg/m³).`
            });
        }

        if (sst > 22.0) {
            alarms.push({
                type: 'danger',
                msg: `KRİTİK: Deniz suyu sıcaklığı müsilaj tetikleme eşiğini aştı (${sst}°C).`
            });
        }

        if (riskScore > 65) {
            alarms.push({
                type: 'danger',
                msg: `ACİL DURUM: Yüksek risk indeks oranı (%${riskScore}). Deniz tabanında müsilaj birikimi riski tespit edildi.`
            });
        }

        // Render alarms
        alarmFeedContent.innerHTML = '';
        if (alarms.length === 0) {
            alarmFeedContent.innerHTML = '<div class="no-alarm-msg">Güvenli: Risk eşiğini aşan parametre bulunamadı.</div>';
            activeAlarmCount.textContent = '0 Aktif';
            activeAlarmCount.className = 'badge alarm-count safe';
        } else {
            alarms.forEach(al => {
                const div = document.createElement('div');
                div.className = `alarm-item ${al.type}`;
                div.innerHTML = `<i data-lucide="info"></i> <span>${al.msg}</span>`;
                alarmFeedContent.appendChild(div);
            });
            activeAlarmCount.textContent = `${alarms.length} Aktif`;
            activeAlarmCount.className = 'badge alarm-count';
            lucide.createIcons();
        }

        // AI Agent thoughts simulator
        aiThoughtContent.innerHTML = '';
        addThoughtLine(`[SYSTEM] Analiz zaman dilimi: ${date}`);
        addThoughtLine(`[ReportingAgent] Coğrafi alan: ${regionCoefficients[selectedRegion].label}`);
        addThoughtLine(`[ReportingAgent] Giriş verileri işleniyor... (Chl: ${chl} mg/m³, Sıcaklık: ${sst}°C)`);

        if (isRealPrediction) {
            addThoughtLine(`[RiskAgent] scikit-learn Random Forest model tahmini başarıyla sorgulandı.`);
        } else {
            addThoughtLine(`[RiskAgent] Bilimsel kural eşleşmesi (Heuristic) formülü çalıştırıldı.`);
        }

        // If User API Key exists, trigger Live Gemini LLM Analysis; otherwise fallback to templates
        if (userApiKey) {
            fetchLiveGeminiInsight(date, regionCoefficients[selectedRegion].label, chl, sst, riskScore);
        } else {
            renderTemplateThoughts(riskScore);
        }
    }

    function renderTemplateThoughts(riskScore) {
        if (riskScore > 65) {
            addThoughtLine(`[RiskAgent] UYARI: Klorofil ve SST girdileri korelasyon limitlerini aşıyor.`, "alert-msg");
            addThoughtLine(`[RiskAgent] Risk skoru hesaplandı: %${riskScore}. Durum: Kritik.`);
            addThoughtLine(`[ReportingAgent] UYARI: Müsilaj salgısı erken uyarı mesajı aktif hale getirildi! Yetkili çevre birimlerine bildiri gönderiliyor.`, "alert-msg");
        } else if (riskScore > 30) {
            addThoughtLine(`[RiskAgent] Risk skoru hesaplandı: %${riskScore}. Durum: Kontrollü İzleme.`);
            addThoughtLine(`[ReportingAgent] Zaman serisi eğrisinde artış eğilimi gözleniyor. Sonraki veriler takip edilecek.`);
        } else {
            addThoughtLine(`[RiskAgent] Tüm girdiler ekolojik güvenlik bantları dahilinde.`);
            addThoughtLine(`[ReportingAgent] Müsilaj riski düşük. Rutin gözleme devam ediliyor.`);
        }
    }

    async function fetchLiveGeminiInsight(date, regionLabel, chl, sst, riskScore) {
        addThoughtLine(`[Gemini AI Live] Canlı LLM ekolojik analizi üretiliyor...`);

        try {
            const prompt = `Sen bir deniz biyoloğu ve çevre uzmanı AI ajanısın (ReportingAgent). Marmara Denizi'nin ${regionLabel} bölgesinde ${date} tarihinde ölçülen Klorofil-a: ${chl} mg/m³, Deniz Yüzeyi Sıcaklığı: ${sst}°C ve Yapay Zeka Müsilaj Risk Skoru: %${riskScore} olarak tespit edilmiştir. Bu verilere dayanarak deniz ekosistemi üzerindeki etkiyi ve alınması gereken önlemi 2 kısa cümlede canlı olarak Türkçe değerlendir.`;

            const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${userApiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{ parts: [{ text: prompt }] }]
                })
            });

            if (!response.ok) {
                throw new Error(`API Hatası (${response.status})`);
            }

            const data = await response.json();
            const text = data.candidates?.[0]?.content?.parts?.[0]?.text;

            if (text) {
                addThoughtLine(`[Gemini AI Live] "${text.trim()}"`, "gemini-live");
            } else {
                throw new Error("Boş API yanıtı");
            }
        } catch (error) {
            addThoughtLine(`[Gemini AI Live - HATA] ${error.message}. Varsayılan şablona geçildi.`, "alert-msg");
            renderTemplateThoughts(riskScore);
        }
    }

    function updateApiStatusBadge(isActive) {
        if (!apiStatusBadge) return;
        if (isActive) {
            apiStatusBadge.className = 'api-status-dot active';
            apiStatusBadge.title = 'Canlı Gemini AI Analizi Aktif';
        } else {
            apiStatusBadge.className = 'api-status-dot';
            apiStatusBadge.title = 'Hazır Metin Modu (Pasif)';
        }
    }

    function addThoughtLine(msg, className = '') {
        const div = document.createElement('div');
        div.className = `log-entry ${className}`;
        div.textContent = msg;
        aiThoughtContent.appendChild(div);
        // Scroll to bottom
        aiThoughtContent.scrollTop = aiThoughtContent.scrollHeight;
    }

    function showAILog(msg, className = '') {
        const div = document.createElement('div');
        div.className = `log-entry system-msg ${className}`;
        div.textContent = `[SİSTEM LOGU] ${msg}`;
        aiThoughtContent.appendChild(div);
    }

    // Step 5: Chart.js visualization
    function buildChart() {
        const canvas = document.getElementById('trendChart');
        if (!canvas || typeof Chart === 'undefined') return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Destory previous chart if any
        if (trendChart) {
            trendChart.destroy();
        }

        const coeff = regionCoefficients[selectedRegion];
        const scaledChl = processedData.chl.map(v => parseFloat((v * coeff.chl).toFixed(2)));
        const scaledSst = processedData.sst.map(v => parseFloat((v * coeff.sst).toFixed(1)));

        // Multi-line chart (Left y-axis Chlorophyll, Right y-axis SST)
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: processedData.dates.map(d => formatDate(d)),
                datasets: [
                    {
                        label: 'Klorofil-a (mg/m³)',
                        data: scaledChl,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.05)',
                        borderWidth: 2,
                        pointRadius: 2,
                        pointHoverRadius: 6,
                        yAxisID: 'yChl',
                        tension: 0.3
                    },
                    {
                        label: 'Deniz Yüzeyi Sıcaklığı (SST) (°C)',
                        data: scaledSst,
                        borderColor: '#f97316',
                        backgroundColor: 'rgba(249, 115, 22, 0.05)',
                        borderWidth: 2,
                        pointRadius: 2,
                        pointHoverRadius: 6,
                        yAxisID: 'ySst',
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false } // Custom legend is in HTML
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.02)' },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    yChl: {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'Klorofil-a (mg/m³)', color: '#06b6d4' },
                        grid: { color: 'rgba(255,255,255,0.03)' },
                        ticks: { color: '#94a3b8' }
                    },
                    ySst: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: 'Sıcaklık (°C)', color: '#f97316' },
                        grid: { drawOnChartArea: false }, // Only keep left axis grids
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    }

    function updateChartHighlight() {
        if (!trendChart) return;

        // Add vertical line highlight on the current index using Chart.js custom plugin or simple updates
        // To keep it simple and high-performance, we can change the radius of the active point
        const datasets = trendChart.data.datasets;
        datasets.forEach(dataset => {
            const radii = new Array(processedData.dates.length).fill(2);
            radii[currentDateIndex] = 8; // Highlight current
            dataset.pointRadius = radii;
        });
        trendChart.update('none'); // Update without animation for speed
    }

    // Step 6: Modals & Report Generation
    function openReportModal() {
        const date = processedData.dates[currentDateIndex];
        const coeff = regionCoefficients[selectedRegion];
        const chl = parseFloat((processedData.chl[currentDateIndex] * coeff.chl).toFixed(2));
        const sst = parseFloat((processedData.sst[currentDateIndex] * coeff.sst).toFixed(1));
        const risk = calculateRiskIndex(chl, sst);
        const qRatio = Math.round(processedData.quality[currentDateIndex] * 100);

        let riskText = 'DÜŞÜK RİSK';
        let riskDesc = 'Ekolojik durum kararlı. Müsilaj risk uyarısı verilmemiştir.';
        if (risk > 65) {
            riskText = 'KRİTİK ALARM';
            riskDesc = 'Müsilaj oluşumu için yüksek olasılık. Klorofil yoğunluğu ve deniz suyu sıcaklığı eşik değerlerin çok üzerindedir. Acil önlem tavsiye edilir.';
        } else if (risk > 30) {
            riskText = 'ORTA SEVİYE UYARI';
            riskDesc = 'Su kolonunda klorofil artışı tespit edilmiştir. Sıcaklık artışıyla birlikte müsilaj oluşumu tetiklenebilir. Yakın takip gereklidir.';
        }

        modalReportBody.innerHTML = `
            <div class="report-section">
                <h3>Genel Rapor Detayları</h3>
                <div class="report-grid">
                    <div class="report-item"><span>Rapor Tarihi:</span> <strong>${formatDate(date)}</strong></div>
                    <div class="report-item"><span>Gözlem Bölgesi:</span> <strong>${regionCoefficients[selectedRegion].label}</strong></div>
                    <div class="report-item"><span>Uydular:</span> <strong>Sentinel-3 OLCI & SLSTR</strong></div>
                    <div class="report-item"><span>Veri Durumu:</span> <strong>Kalite Kontrolü Yapıldı</strong></div>
                </div>
            </div>
            <div class="report-section">
                <h3>Parametre Analiz Sonuçları</h3>
                <div class="report-grid">
                    <div class="report-item"><span>Klorofil-a:</span> <strong>${chl} mg/m³</strong></div>
                    <div class="report-item"><span>Deniz Sıcaklığı (SST):</span> <strong>${sst} °C</strong></div>
                    <div class="report-item"><span>Risk İndeksi:</span> <strong style="color: ${risk > 65 ? '#ef4444' : risk > 30 ? '#eab308' : '#22c55e'}">${riskText} (%${risk})</strong></div>
                    <div class="report-item"><span>Veri Temizlik Oranı:</span> <strong>%${qRatio}</strong></div>
                </div>
            </div>
            <div class="report-section">
                <h3>Yapay Zeka Risk Değerlendirmesi</h3>
                <p class="report-desc">${riskDesc}</p>
            </div>
            <div class="report-section">
                <h3>Sistem Notu</h3>
                <p class="report-desc" style="font-size: 11px; color: #94a3b8;">
                    Bu rapor AquaSentinel AI - ReportingAgent tarafından otomatik olarak üretilmiştir. Sentinel-3 Level-2 veri standartlarına uygundur.
                </p>
            </div>
        `;

        reportModal.classList.add('open');
    }

    function closeReportModal() {
        reportModal.classList.remove('open');
    }

    // Helpers
    function formatDate(dateStr) {
        if (!dateStr) return '';
        const parts = dateStr.split('-');
        if (parts.length !== 3) return dateStr;
        return `${parts[2]}/${parts[1]}/${parts[0]}`; // DD/MM/YYYY
    }

    // Launch!
    loadData();
});

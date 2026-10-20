(function () {
    'use strict';

    const POLL_INTERVAL_MS = 1000;
    const MAX_HISTORY_POINTS = 60;

    const hrHistory = [];
    const spo2History = [];

    let lastKnownBeatTimestamp = null;
    let pollTimer = null;

    const el = {
        systemClock: document.getElementById('system-clock'),
        connectionPill: document.getElementById('connection-pill'),
        connectionStatusText: document.getElementById('connection-status-text'),
        systemBanner: document.getElementById('system-banner'),
        bannerMessage: document.getElementById('banner-message'),

        hrIconWrap: document.getElementById('hr-icon-wrap'),
        hrStatusBadge: document.getElementById('hr-status-badge'),
        hrValue: document.getElementById('hr-value'),
        hrSubtext: document.getElementById('hr-subtext'),

        spo2StatusBadge: document.getElementById('spo2-status-badge'),
        spo2Value: document.getElementById('spo2-value'),
        spo2Fill: document.getElementById('spo2-progress-fill'),

        tempValue: document.getElementById('temp-value'),
        tempStatusBadge: document.getElementById('temp-status-badge'),
        tempSubtext: document.getElementById('temp-subtext'),
        humValue: document.getElementById('hum-value'),
        humStatusBadge: document.getElementById('hum-status-badge'),
        humSubtext: document.getElementById('hum-subtext'),

        chartHrCurr: document.getElementById('chart-hr-curr'),
        chartSpo2Curr: document.getElementById('chart-spo2-curr'),

        hrCanvas: document.getElementById('heartRateChart'),
        spo2Canvas: document.getElementById('spo2Chart'),
    };

    function updateClock() {
        if (!el.systemClock) return;
        el.systemClock.textContent = new Date().toLocaleTimeString();
    }
    setInterval(updateClock, 1000);
    updateClock();

    class SensorCanvasChart {
        constructor(canvas, options) {
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');
            this.options = Object.assign(
                {
                    lineColor: '#06b6d4',
                    glowColor: 'rgba(6, 182, 212, 0.25)',
                    fillGradientStart: 'rgba(6, 182, 212, 0.2)',
                    fillGradientEnd: 'rgba(6, 182, 212, 0.0)',
                    yMin: 0,
                    yMax: 100,
                    yGridSteps: 4,
                    unit: '',
                    decimals: 0,
                },
                options
            );

            this.resize();
            window.addEventListener('resize', () => this.resize());
        }

        resize() {
            if (!this.canvas) return;
            const rect = this.canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            this.canvas.width = rect.width * dpr;
            this.canvas.height = rect.height * dpr;
            this.ctx.scale(dpr, dpr);
            this.width = rect.width;
            this.height = rect.height;
        }

        render(dataPoints) {
            if (!this.ctx || !this.width || !this.height) return;

            const ctx = this.ctx;
            const w = this.width;
            const h = this.height;

            ctx.clearRect(0, 0, w, h);

            const padLeft = 40;
            const padRight = 12;
            const padTop = 14;
            const padBottom = 22;
            const plotW = w - padLeft - padRight;
            const plotH = h - padTop - padBottom;

            const yMin = this.options.yMin;
            const yMax = this.options.yMax;
            const steps = this.options.yGridSteps;

            ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            ctx.fillStyle = '#64748b';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.lineWidth = 1;

            for (let i = 0; i <= steps; i++) {
                const fraction = i / steps;
                const yVal = yMin + fraction * (yMax - yMin);
                const py = padTop + plotH - fraction * plotH;

                ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
                ctx.beginPath();
                ctx.moveTo(padLeft, py);
                ctx.lineTo(padLeft + plotW, py);
                ctx.stroke();

                ctx.fillText(yVal.toFixed(this.options.decimals) + this.options.unit, padLeft - 6, py);
            }

            ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
            ctx.beginPath();
            ctx.moveTo(padLeft, padTop + plotH);
            ctx.lineTo(padLeft + plotW, padTop + plotH);
            ctx.stroke();

            if (!dataPoints || dataPoints.length === 0) {
                ctx.textAlign = 'center';
                ctx.fillStyle = '#475569';
                ctx.fillText('Awaiting sensor stream...', padLeft + plotW / 2, padTop + plotH / 2);
                return;
            }

            const getX = (index) => padLeft + (index / (MAX_HISTORY_POINTS - 1)) * plotW;
            const getY = (val) => {
                const clamped = Math.max(yMin, Math.min(yMax, val));
                const ratio = (clamped - yMin) / (yMax - yMin);
                return padTop + plotH - ratio * plotH;
            };

            const segments = [];
            let currentSegment = [];

            for (let i = 0; i < dataPoints.length; i++) {
                const pt = dataPoints[i];
                if (pt.val !== null && pt.val !== undefined && pt.val > 0) {
                    currentSegment.push({ x: getX(i), y: getY(pt.val), val: pt.val });
                } else {
                    if (currentSegment.length > 0) {
                        segments.push(currentSegment);
                        currentSegment = [];
                    }
                }
            }
            if (currentSegment.length > 0) {
                segments.push(currentSegment);
            }

            for (const seg of segments) {
                if (seg.length === 0) continue;

                const grad = ctx.createLinearGradient(0, padTop, 0, padTop + plotH);
                grad.addColorStop(0, this.options.fillGradientStart);
                grad.addColorStop(1, this.options.fillGradientEnd);

                ctx.beginPath();
                ctx.moveTo(seg[0].x, padTop + plotH);
                ctx.lineTo(seg[0].x, seg[0].y);
                for (let i = 1; i < seg.length; i++) {
                    ctx.lineTo(seg[i].x, seg[i].y);
                }
                ctx.lineTo(seg[seg.length - 1].x, padTop + plotH);
                ctx.closePath();
                ctx.fillStyle = grad;
                ctx.fill();

                ctx.save();
                ctx.shadowColor = this.options.glowColor;
                ctx.shadowBlur = 6;
                ctx.strokeStyle = this.options.lineColor;
                ctx.lineWidth = 2.0;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';

                ctx.beginPath();
                ctx.moveTo(seg[0].x, seg[0].y);
                for (let i = 1; i < seg.length; i++) {
                    ctx.lineTo(seg[i].x, seg[i].y);
                }
                ctx.stroke();
                ctx.restore();

                const lastPt = seg[seg.length - 1];
                ctx.beginPath();
                ctx.arc(lastPt.x, lastPt.y, 3.5, 0, Math.PI * 2);
                ctx.fillStyle = '#ffffff';
                ctx.fill();
                ctx.strokeStyle = this.options.lineColor;
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        }
    }

    const hrChart = new SensorCanvasChart(el.hrCanvas, {
        lineColor: '#f43f5e',
        glowColor: 'rgba(244, 63, 94, 0.4)',
        fillGradientStart: 'rgba(244, 63, 94, 0.22)',
        fillGradientEnd: 'rgba(244, 63, 94, 0.0)',
        yMin: 40,
        yMax: 160,
        yGridSteps: 4,
        unit: '',
        decimals: 0,
    });

    const spo2Chart = new SensorCanvasChart(el.spo2Canvas, {
        lineColor: '#06b6d4',
        glowColor: 'rgba(6, 182, 212, 0.4)',
        fillGradientStart: 'rgba(6, 182, 212, 0.22)',
        fillGradientEnd: 'rgba(6, 182, 212, 0.0)',
        yMin: 80,
        yMax: 100,
        yGridSteps: 4,
        unit: '%',
        decimals: 0,
    });

    function triggerBeatAnimation() {
        if (!el.hrIconWrap) return;
        el.hrIconWrap.classList.add('beat-pulse');
        setTimeout(() => {
            el.hrIconWrap.classList.remove('beat-pulse');
        }, 250);
    }

    async function fetchReadings() {
        try {
            const res = await fetch('/api/readings', {
                method: 'GET',
                headers: { 'Accept': 'application/json' },
                cache: 'no-store',
            });

            if (!res.ok) throw new Error(`HTTP error ${res.status}`);

            const data = await res.json();
            updateDashboard(data);
        } catch (err) {
            handleNetworkError(err);
        }
    }

    function updateDashboard(data) {
        const {
            heart_rate,
            spo2,
            temperature,
            humidity,
            connected,
            finger_detected,
            stale,
            last_beat,
            message,
        } = data;

        if (!connected) {
            setConnectionState('disconnected', 'Disconnected');
            setBanner('error', message || 'Serial disconnected. Reconnecting...');
        } else if (stale) {
            setConnectionState('stale', 'Signal Stale');
            setBanner('warning', message || 'Sensor data stale. Place finger on sensor.');
        } else {
            setConnectionState('connected', 'Live Stream');
            setBanner('success', message || 'Receiving live health & environmental stream.');
        }

        if (last_beat && last_beat !== lastKnownBeatTimestamp) {
            lastKnownBeatTimestamp = last_beat;
            triggerBeatAnimation();
        }

        const isHrValid = connected && !stale && finger_detected && heart_rate !== null && heart_rate > 0;
        if (isHrValid) {
            el.hrValue.textContent = heart_rate.toFixed(1);
            if (heart_rate < 60) {
                setBadge(el.hrStatusBadge, 'Bradycardia', 'badge-warning');
                el.hrSubtext.textContent = 'Low resting pulse';
            } else if (heart_rate > 100) {
                setBadge(el.hrStatusBadge, 'Elevated', 'badge-warning');
                el.hrSubtext.textContent = 'High pulse detected';
            } else {
                setBadge(el.hrStatusBadge, 'Normal', 'badge-optimal');
                el.hrSubtext.textContent = 'Optimal resting pulse';
            }
            if (el.chartHrCurr) el.chartHrCurr.textContent = `${heart_rate.toFixed(1)} BPM`;
        } else {
            el.hrValue.textContent = '--.-';
            if (!connected) {
                setBadge(el.hrStatusBadge, 'Offline', 'badge-danger');
                el.hrSubtext.textContent = 'Serial link offline';
            } else {
                setBadge(el.hrStatusBadge, 'Waiting', 'badge-neutral');
                el.hrSubtext.textContent = 'Place finger gently on sensor';
            }
            if (el.chartHrCurr) el.chartHrCurr.textContent = '-- BPM';
        }

        const isSpo2Valid = connected && !stale && finger_detected && spo2 !== null && spo2 > 0;
        if (isSpo2Valid) {
            const spo2Int = Math.round(spo2);
            el.spo2Value.textContent = spo2Int;
            el.spo2Fill.style.width = `${Math.min(100, Math.max(0, spo2Int))}%`;

            if (spo2Int >= 95) {
                setBadge(el.spo2StatusBadge, 'Optimal', 'badge-optimal');
            } else if (spo2Int >= 90) {
                setBadge(el.spo2StatusBadge, 'Borderline', 'badge-warning');
            } else {
                setBadge(el.spo2StatusBadge, 'Low SpO2', 'badge-danger');
            }
            if (el.chartSpo2Curr) el.chartSpo2Curr.textContent = `${spo2Int}%`;
        } else {
            el.spo2Value.textContent = '--';
            el.spo2Fill.style.width = '0%';
            setBadge(el.spo2StatusBadge, 'Standby', 'badge-neutral');
            if (el.chartSpo2Curr) el.chartSpo2Curr.textContent = '-- %';
        }

        if (temperature !== null && temperature !== undefined) {
            el.tempValue.textContent = Number(temperature).toFixed(1);
            if (temperature >= 22.0 && temperature <= 28.0) {
                setBadge(el.tempStatusBadge, 'Comfortable', 'badge-optimal');
                el.tempSubtext.textContent = 'Normal ambient room temperature';
            } else if (temperature > 28.0) {
                setBadge(el.tempStatusBadge, 'Warm', 'badge-warning');
                el.tempSubtext.textContent = 'Elevated ambient temperature';
            } else {
                setBadge(el.tempStatusBadge, 'Cool', 'badge-warning');
                el.tempSubtext.textContent = 'Cool ambient temperature';
            }
        }

        if (humidity !== null && humidity !== undefined) {
            el.humValue.textContent = Number(humidity).toFixed(1);
            if (humidity >= 40 && humidity <= 65) {
                setBadge(el.humStatusBadge, 'Optimal', 'badge-optimal');
                el.humSubtext.textContent = 'Comfortable moisture level';
            } else if (humidity > 65) {
                setBadge(el.humStatusBadge, 'High', 'badge-warning');
                el.humSubtext.textContent = 'Humid environment';
            } else {
                setBadge(el.humStatusBadge, 'Dry', 'badge-warning');
                el.humSubtext.textContent = 'Dry air detected';
            }
        }

        const now = new Date();
        hrHistory.push({ time: now, val: isHrValid ? heart_rate : null });
        spo2History.push({ time: now, val: isSpo2Valid ? Math.round(spo2) : null });

        if (hrHistory.length > MAX_HISTORY_POINTS) hrHistory.shift();
        if (spo2History.length > MAX_HISTORY_POINTS) spo2History.shift();

        hrChart.render(hrHistory);
        spo2Chart.render(spo2History);
    }

    function handleNetworkError(err) {
        setConnectionState('disconnected', 'Server Offline');
        setBanner('error', `Cannot reach server: ${err.message || err}`);
        el.hrValue.textContent = '--.-';
        el.spo2Value.textContent = '--';
        el.spo2Fill.style.width = '0%';
    }

    function setConnectionState(stateClass, label) {
        if (!el.connectionPill || !el.connectionStatusText) return;
        el.connectionPill.className = `status-pill status-${stateClass}`;
        el.connectionStatusText.textContent = label;
    }

    function setBanner(type, message) {
        if (!el.systemBanner || !el.bannerMessage) return;
        el.systemBanner.className = `system-banner banner-${type}`;
        el.bannerMessage.textContent = message;
    }

    function setBadge(badgeEl, text, badgeClass) {
        if (!badgeEl) return;
        badgeEl.className = `badge ${badgeClass}`;
        badgeEl.textContent = text;
    }

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        fetchReadings();
        pollTimer = setInterval(fetchReadings, POLL_INTERVAL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startPolling);
    } else {
        startPolling();
    }
})();

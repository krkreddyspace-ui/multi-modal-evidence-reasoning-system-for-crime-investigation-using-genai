// ============================================================
//  FORENSIC ANALYTICS — Chart Renderer
//  Reads analytics data from localStorage and renders all charts
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

    // Read analytics from localStorage
    const raw = localStorage.getItem('forensic_analytics');
    if (!raw) {
        document.getElementById('empty-state').style.display = 'flex';
        document.getElementById('analytics-content').style.display = 'none';
        return;
    }

    let analytics;
    try {
        analytics = JSON.parse(raw);
    } catch (e) {
        document.getElementById('empty-state').style.display = 'flex';
        document.getElementById('analytics-content').style.display = 'none';
        return;
    }

    // Show the analytics content
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('analytics-content').style.display = 'block';

    // Timestamp
    const ts = localStorage.getItem('forensic_analytics_ts');
    if (ts) {
        document.getElementById('header-timestamp').textContent = new Date(parseInt(ts)).toLocaleString();
    }

    // -------------------------------------------------------
    // Populate KPI Stat Cards
    // -------------------------------------------------------
    const timing = analytics.timing || {};
    document.getElementById('stat-total-time').textContent = (timing.total_pipeline_sec || 0).toFixed(1) + 's';
    document.getElementById('stat-extraction-time').textContent = 'EXT: ' + (timing.extraction_sec || 0).toFixed(1) + 's';
    document.getElementById('stat-reasoning-time').textContent = 'AI: ' + (timing.reasoning_sec || 0).toFixed(1) + 's';
    document.getElementById('stat-total-files').textContent = analytics.total_files || 0;
    document.getElementById('stat-total-chars').textContent = (analytics.total_chars_extracted || 0).toLocaleString();

    const confValue = analytics.confidence_value || 0;
    const confEl = document.getElementById('stat-confidence');
    confEl.textContent = confValue + '%';
    if (confValue > 70) { confEl.classList.remove('text-red-400'); confEl.classList.add('text-green-400'); }
    else if (confValue > 40) { confEl.classList.remove('text-red-400'); confEl.classList.add('text-yellow-400'); }

    const modDist = analytics.modality_distribution || {};
    const modSummary = Object.entries(modDist).map(([k, v]) => `${k}: ${v}`).join(' · ');
    document.getElementById('stat-modalities').textContent = modSummary || '—';

    // -------------------------------------------------------
    // Chart Theme Colors
    // -------------------------------------------------------
    const fontColor = 'rgba(255,255,255,0.7)';
    const gridColor = 'rgba(255,255,255,0.06)';
    const neonCyan = '#00f3ff';
    const neonViolet = '#bc13fe';
    const neonRed = '#ff003c';
    const neonGreen = '#39ff14';
    const neonYellow = '#ffd700';
    const neonOrange = '#ff6a00';

    Chart.defaults.color = fontColor;
    Chart.defaults.font.family = "'JetBrains Mono', 'Space Grotesk', monospace";
    Chart.defaults.font.size = 11;

    // -------------------------------------------------------
    // 1. PIPELINE EFFICIENCY (Bar: per-file timing + file size)
    // -------------------------------------------------------
    const perFile = timing.per_file || [];
    const pipelineCtx = document.getElementById('chart-pipeline');
    if (pipelineCtx && perFile.length > 0) {
        const fileLabels = perFile.map(f => f.file_name.length > 15 ? f.file_name.substring(0, 15) + '…' : f.file_name);
        const fileTimes = perFile.map(f => f.processing_time_sec);
        const fileSizes = perFile.map(f => f.file_size_kb);

        const barColors = perFile.map((_, i) => {
            const palette = [neonCyan, neonViolet, neonRed, neonGreen, neonYellow, neonOrange];
            return palette[i % palette.length];
        });

        new Chart(pipelineCtx, {
            type: 'bar',
            data: {
                labels: fileLabels,
                datasets: [
                    {
                        label: 'Processing Time (s)',
                        data: fileTimes,
                        backgroundColor: barColors.map(c => c + '33'),
                        borderColor: barColors,
                        borderWidth: 2,
                        borderRadius: 8,
                        yAxisID: 'y'
                    },
                    {
                        label: 'File Size (KB)',
                        data: fileSizes,
                        backgroundColor: 'rgba(255,255,255,0.05)',
                        borderColor: 'rgba(255,255,255,0.2)',
                        borderWidth: 1,
                        borderRadius: 8,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { padding: 16, usePointStyle: true, pointStyle: 'rectRounded' } }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { maxRotation: 45 } },
                    y: { position: 'left', grid: { color: gridColor }, title: { display: true, text: 'Time (s)', color: neonCyan } },
                    y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Size (KB)', color: 'rgba(255,255,255,0.4)' } }
                }
            }
        });
    }

    // -------------------------------------------------------
    // 2. MODALITY DISTRIBUTION (Doughnut)
    // -------------------------------------------------------
    const modalityCtx = document.getElementById('chart-modality');
    const modLabels = Object.keys(modDist);
    const modValues = Object.values(modDist);
    if (modalityCtx && modLabels.length > 0) {
        const modColors = [neonCyan, neonViolet, neonRed, neonGreen, neonYellow, neonOrange];
        new Chart(modalityCtx, {
            type: 'doughnut',
            data: {
                labels: modLabels,
                datasets: [{
                    data: modValues,
                    backgroundColor: modLabels.map((_, i) => modColors[i % modColors.length] + '55'),
                    borderColor: modLabels.map((_, i) => modColors[i % modColors.length]),
                    borderWidth: 2,
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '55%',
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } } }
                }
            }
        });
    }

    // -------------------------------------------------------
    // 3. RISK FACTOR ANALYSIS (Radar)
    // -------------------------------------------------------
    const riskCtx = document.getElementById('chart-risk');
    const riskCats = analytics.risk_categories || {};
    const riskLabels = Object.keys(riskCats);
    const riskValues = Object.values(riskCats);
    if (riskCtx && riskLabels.length > 0) {
        new Chart(riskCtx, {
            type: 'radar',
            data: {
                labels: riskLabels,
                datasets: [{
                    label: 'Risk Intensity',
                    data: riskValues,
                    backgroundColor: neonRed + '22',
                    borderColor: neonRed,
                    borderWidth: 2,
                    pointBackgroundColor: neonRed,
                    pointBorderColor: '#fff',
                    pointRadius: 5,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255,255,255,0.08)' },
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        pointLabels: { color: fontColor, font: { size: 12, weight: 'bold' } },
                        ticks: { display: false },
                        suggestedMin: 0
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // -------------------------------------------------------
    // 4. CONFIDENCE GAUGE (Doughnut - Semi-circle)
    // -------------------------------------------------------
    const confCtx = document.getElementById('chart-confidence');
    if (confCtx) {
        const gaugeColor = confValue > 70 ? neonGreen : confValue > 40 ? neonYellow : neonRed;
        new Chart(confCtx, {
            type: 'doughnut',
            data: {
                labels: ['Confidence', 'Remaining'],
                datasets: [{
                    data: [confValue, 100 - confValue],
                    backgroundColor: [gaugeColor + '88', 'rgba(255,255,255,0.04)'],
                    borderColor: [gaugeColor, 'rgba(255,255,255,0.08)'],
                    borderWidth: 2,
                    circumference: 270,
                    rotation: 225
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            },
            plugins: [{
                id: 'gaugeText',
                afterDraw(chart) {
                    const { ctx, chartArea } = chart;
                    const centerX = (chartArea.left + chartArea.right) / 2;
                    const centerY = (chartArea.top + chartArea.bottom) / 2 + 10;
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = 'bold 48px JetBrains Mono, monospace';
                    ctx.fillStyle = gaugeColor;
                    ctx.shadowColor = gaugeColor;
                    ctx.shadowBlur = 25;
                    ctx.fillText(confValue + '%', centerX, centerY);
                    ctx.restore();
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.font = '11px Space Grotesk, sans-serif';
                    ctx.fillStyle = 'rgba(255,255,255,0.4)';
                    ctx.fillText('AI CONFIDENCE INDEX', centerX, centerY + 35);
                    ctx.restore();
                }
            }]
        });
    }

    // -------------------------------------------------------
    // 5. KEYWORD HIT FREQUENCY (Horizontal Bar)
    // -------------------------------------------------------
    const kwCtx = document.getElementById('chart-keywords');
    const kwData = analytics.keyword_hits || {};
    const kwLabels = Object.keys(kwData);
    const kwValues = Object.values(kwData);
    if (kwCtx && kwLabels.length > 0) {
        const kwGradientColors = kwLabels.map((_, i) => {
            const hue = (i * 30 + 180) % 360;
            return `hsla(${hue}, 100%, 65%, 0.7)`;
        });
        const kwBorderColors = kwLabels.map((_, i) => {
            const hue = (i * 30 + 180) % 360;
            return `hsl(${hue}, 100%, 65%)`;
        });

        new Chart(kwCtx, {
            type: 'bar',
            data: {
                labels: kwLabels.map(k => k.toUpperCase()),
                datasets: [{
                    label: 'Occurrences',
                    data: kwValues,
                    backgroundColor: kwGradientColors,
                    borderColor: kwBorderColors,
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: gridColor }, title: { display: true, text: 'Hit Count', color: neonYellow } },
                    y: { grid: { display: false }, ticks: { font: { size: 11, weight: 'bold' } } }
                }
            }
        });
    }

    // -------------------------------------------------------
    // 6. CONTENT RICHNESS PER FILE (Bar)
    // -------------------------------------------------------
    const richCtx = document.getElementById('chart-richness');
    const richData = analytics.content_richness || [];
    if (richCtx && richData.length > 0) {
        const richLabels = richData.map(r => r.file_name.length > 16 ? r.file_name.substring(0, 16) + '…' : r.file_name);
        const richValues = richData.map(r => r.char_count);
        const richColors = richData.map(r => {
            switch (r.modality) {
                case 'IMAGE': return neonViolet;
                case 'AUDIO': return neonGreen;
                case 'TEXT': return neonCyan;
                case 'APPLICATION': return neonOrange;
                default: return neonYellow;
            }
        });

        new Chart(richCtx, {
            type: 'bar',
            data: {
                labels: richLabels,
                datasets: [{
                    label: 'Characters Extracted',
                    data: richValues,
                    backgroundColor: richColors.map(c => c + '44'),
                    borderColor: richColors,
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: gridColor }, ticks: { maxRotation: 45 } },
                    y: { grid: { color: gridColor }, title: { display: true, text: 'Chars Extracted', color: neonCyan } }
                }
            }
        });
    }

});

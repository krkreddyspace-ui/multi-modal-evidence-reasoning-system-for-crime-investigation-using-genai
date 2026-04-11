document.addEventListener('DOMContentLoaded', () => {
    
    // UI Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileListEl = document.getElementById('file-list');
    const analyzeBtn = document.getElementById('analyze-btn');

    const loadingState = document.getElementById('loading-state');
    const resultsDashboard = document.getElementById('results-dashboard');
    const evidenceContainer = document.getElementById('evidence-container');
    const resetBtn = document.getElementById('reset-dashboard-btn');

    // State
    let selectedFiles = [];

    // --- Restore cached dashboard on page load ---
    const cachedData = localStorage.getItem('forensic_dashboard_data');
    let hasRestoredFromCache = false;
    
    if (cachedData) {
        try {
            const data = JSON.parse(cachedData);
            populateDashboard(data);
            updateFlowchartState(3);
            hasRestoredFromCache = true;
            // Re-enable analytics nav button
            const navBtn = document.getElementById('analytics-nav-btn');
            if (navBtn) {
                navBtn.classList.remove('opacity-40', 'pointer-events-none');
                navBtn.classList.add('opacity-100', 'shadow-[0_0_15px_rgba(57,255,20,0.2)]');
                navBtn.title = 'View Forensic Analytics';
            }
            
            // Scroll to the main dashboard container automatically
            setTimeout(() => {
                document.getElementById('dashboard-content').scrollIntoView({ behavior: 'smooth' });
            }, 500); // slight delay to allow rendering
            
        } catch(e) {
            console.warn('Failed to restore cached dashboard:', e);
        }
    }

    // --- Process Flow Manager ---
    function updateFlowchartState(step) {
        // Step 0: Idle, 1: Intake (Files added), 2: Analyzing (API called), 3: Complete
        const setNodeActive = (num, isAnimating) => {
            const node = document.getElementById(`flow-node-${num}`);
            const icon = document.getElementById(`flow-icon-${num}`);
            const text = document.getElementById(`flow-text-${num}`);
            if (!node) return;
            node.classList.remove('opacity-50');
            node.classList.add('opacity-100');
            
            icon.classList.remove('border-white/20', 'bg-[#05050A]', 'text-white/50', 'border-violet-500', 'bg-violet-500/20', 'text-violet-400');
            icon.classList.add('border-cyan-400', 'bg-cyan-500/20', 'text-cyan-400', 'shadow-[0_0_15px_#00f3ff]');
            
            text.classList.remove('text-white/50', 'text-violet-400');
            text.classList.add('text-cyan-400', 'drop-shadow-md');
            
            if (isAnimating) icon.classList.add('animate-pulse');
            else icon.classList.remove('animate-pulse');
        };

        const setNodeComplete = (num) => {
            const node = document.getElementById(`flow-node-${num}`);
            const icon = document.getElementById(`flow-icon-${num}`);
            const text = document.getElementById(`flow-text-${num}`);
            const line = document.getElementById(`flow-line-${num}`);
            if (!node) return;
            
            node.classList.remove('opacity-50');
            node.classList.add('opacity-100');
            
            icon.classList.remove('border-white/20', 'bg-[#05050A]', 'text-white/50', 'border-cyan-400', 'bg-cyan-500/20', 'text-cyan-400', 'shadow-[0_0_15px_#00f3ff]');
            icon.classList.add('border-violet-500', 'bg-violet-500/20', 'text-violet-400');
            icon.classList.remove('animate-pulse');
            
            text.classList.remove('text-white/50', 'text-cyan-400', 'drop-shadow-md');
            text.classList.add('text-violet-400');
            
            if (line) {
                line.classList.remove('bg-white/20');
                line.classList.add('bg-violet-500', 'shadow-[0_0_8px_#bc13fe]');
            }
        };

        const setNodeIdle = (num) => {
            const node = document.getElementById(`flow-node-${num}`);
            const icon = document.getElementById(`flow-icon-${num}`);
            const text = document.getElementById(`flow-text-${num}`);
            const line = document.getElementById(`flow-line-${num}`);
            if (!node) return;
            
            node.classList.remove('opacity-100');
            node.classList.add('opacity-50');
            
            icon.classList.remove('border-cyan-400', 'bg-cyan-500/20', 'text-cyan-400', 'shadow-[0_0_15px_#00f3ff]', 'border-violet-500', 'bg-violet-500/20', 'text-violet-400');
            icon.classList.add('border-white/20', 'bg-[#05050A]', 'text-white/50');
            icon.classList.remove('animate-pulse');
            
            text.classList.remove('text-cyan-400', 'text-violet-400', 'drop-shadow-md');
            text.classList.add('text-white/50');
            
            if (line) {
                line.classList.remove('bg-violet-500', 'shadow-[0_0_8px_#bc13fe]');
                line.classList.add('bg-white/20');
            }
        };

        if (step === 0) {
            setNodeIdle(1); setNodeIdle(2); setNodeIdle(3); setNodeIdle(4);
        } else if (step === 1) {
            setNodeActive(1, true); setNodeIdle(2); setNodeIdle(3); setNodeIdle(4);
        } else if (step === 2) {
            setNodeComplete(1); setNodeActive(2, true); setNodeIdle(3); setNodeIdle(4);
            setTimeout(() => { setNodeComplete(2); setNodeActive(3, true); }, 2000);
        } else if (step === 3) {
            setNodeComplete(1); setNodeComplete(2); setNodeComplete(3); setNodeComplete(4);
        }
    }

    if (!hasRestoredFromCache) {
        updateFlowchartState(0);
    }

    // --- Drag & Drop Handlers ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add('bg-cyan-500/10', 'border-cyan-400'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove('bg-cyan-500/10', 'border-cyan-400'), false);
    });

    dropzone.addEventListener('drop', handleDrop, false);
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFilesSelect);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFilesSelect(e) {
        handleFiles(e.target.files);
    }

    function handleFiles(files) {
        if (!files.length) return;
        
        // Add to selected array (prevent perfect duplicates by name/size)
        let added = 0;
        Array.from(files).forEach(file => {
            const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
            if (!exists) {
                selectedFiles.push(file);
                added++;
            }
        });

        if (added > 0) {
            updateFlowchartState(1);
        }

        renderFileList();
    }

    function renderFileList() {
        fileListEl.innerHTML = '';
        
        if (selectedFiles.length > 0) {
            analyzeBtn.removeAttribute('disabled');
        } else {
            analyzeBtn.setAttribute('disabled', 'true');
        }

        selectedFiles.forEach((file, index) => {
            const ext = file.name.split('.').pop().toLowerCase();
            let iconClass = 'lucide:file-text'; // default
            
            if (['png','jpg','jpeg'].includes(ext)) iconClass = 'lucide:image';
            if (['wav','mp3'].includes(ext)) iconClass = 'lucide:file-audio';
            if (ext === 'pdf') iconClass = 'lucide:file-check-2';
            if (ext === 'csv') iconClass = 'lucide:file-spreadsheet';

            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-2 bg-black/40 border border-cyan-500/20 rounded shadow-md group hover:bg-white/5 transition-all';
            
            item.innerHTML = `
                <div class="flex items-center gap-3 overflow-hidden">
                    <iconify-icon icon="${iconClass}" class="text-xl text-cyan-400 shrink-0"></iconify-icon>
                    <span class="text-xs text-white font-bold tracking-widest uppercase truncate">${file.name}</span>
                </div>
                <iconify-icon icon="lucide:x-circle" class="text-red-500/50 hover:text-red-500 cursor-pointer shrink-0 remove-file transition-all" data-idx="${index}" title="Remove"></iconify-icon>
            `;
            
            fileListEl.appendChild(item);
        });

        // Attach remove limit events
        document.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(e.target.dataset.idx);
                selectedFiles.splice(idx, 1);
                if (selectedFiles.length === 0) updateFlowchartState(0);
                renderFileList();
            });
        });
    }

    // --- API Request & Dashboard Rendering ---
    analyzeBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;

        updateFlowchartState(2);

        // UI transitions
        loadingState.style.display = 'flex';
        analyzeBtn.setAttribute('disabled', 'true');
        
        // Scroll to top to focus on loading
        window.scrollTo(0,0);

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const data = await response.json();
            
            // Cache the full response for persistence across navigation
            localStorage.setItem('forensic_dashboard_data', JSON.stringify(data));
            
            updateFlowchartState(3);
            
            populateDashboard(data);
            
            // Switch view
            loadingState.style.display = 'none';

            // Scroll to the main dashboard container
            document.getElementById('dashboard-content').scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error(error);
            updateFlowchartState(0);
            alert("Error analyzing evidence: " + error.message);
            loadingState.style.display = 'none';
        } finally {
            analyzeBtn.removeAttribute('disabled');
        }
    });

    function populateDashboard(data) {
        const { summary, raw_evidence, analytics } = data;

        // Top KPIs
        const culpritText = summary.culprit || "Unknown";
        document.getElementById('res-culprit').textContent = culpritText;
        
        // Coloring the culprit card based on if it's found
        const cCard = document.getElementById('res-culprit');
        if (culpritText.toLowerCase().includes("not identified") || culpritText.toLowerCase() === "unknown") {
            cCard.classList.remove('text-white');
            cCard.classList.add('text-gray-500');
        } else {
            cCard.classList.add('text-white');
            cCard.classList.remove('text-gray-500');
        }

        const confString = (summary.confidence || "0").replace('%','');
        document.getElementById('res-confidence').textContent = confString + "%";
        
        let numericConf = parseFloat(confString);
        if (!isNaN(numericConf)) {
            document.getElementById('res-confidence-bar').style.width = numericConf + "%";
        }
        
        // Detail Panels
        // Convert markdown stars ** to strong formatting
        let rawReasoning = summary.reasoning || "No reasoning generated.";
        document.getElementById('res-reasoning').innerHTML = parseSimpleMarkdown(rawReasoning);
        
        let rawKeyEvidence = summary.evidence || "No evidence parameters generated.";
        document.getElementById('res-key-evidence').innerHTML = parseSimpleMarkdown(rawKeyEvidence);
        
        let rawEliminated = summary.eliminated || "None detected in analysis.";
        const eliminatedContainer = document.getElementById('res-eliminated');
        eliminatedContainer.innerHTML = '';
        
        if (rawEliminated.includes('None detected')) {
            eliminatedContainer.innerHTML = `<div class="p-4 bg-white/5 border border-white/10 rounded-xl text-gray-400 font-mono text-sm">${rawEliminated}</div>`;
        } else {
            const lines = rawEliminated.split('\n').filter(l => l.trim().length > 0);
            lines.forEach(line => {
                let text = line.replace(/^[\-\*]\s*/, '').trim();
                let name = "Unknown";
                let reason = text;
                
                const separatorIndex = text.search(/[→>:-]/);
                if (separatorIndex > 0 && separatorIndex < 40) { // arbitrary limit to avoid interpreting a mid-sentence dash as a separator
                    name = text.substring(0, separatorIndex).trim();
                    reason = text.substring(separatorIndex + 1).replace(/^[>:-]\s*/, '').trim();
                }
                
                const div = document.createElement('div');
                div.className = 'p-3 bg-gray-500/5 border border-gray-500/20 rounded-xl flex flex-col gap-1 shadow-sm hover:border-gray-500/40 transition-colors border-l-4 border-l-gray-500 relative overflow-hidden group';
                div.innerHTML = `
                    <div class="absolute inset-0 bg-gradient-to-r from-gray-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <div class="relative flex items-center gap-2">
                        <iconify-icon icon="lucide:user-x" class="text-gray-400 text-lg group-hover:text-white transition-colors"></iconify-icon>
                        <span class="text-sm font-bold text-gray-300 uppercase tracking-widest group-hover:text-white transition-colors">${parseSimpleMarkdown(name)}</span>
                    </div>
                    <p class="relative text-sm font-mono text-gray-400 leading-relaxed pl-7">${parseSimpleMarkdown(reason)}</p>
                `;
                eliminatedContainer.appendChild(div);
            });
        }

        // Smart Tags Generation
        const investigateText = (rawReasoning + " " + rawKeyEvidence).toLowerCase();
        let generatedTags = [];
        
        const tagsMapping = {
            'fraud': { label: 'FRAUD', color: 'bg-red-500/20 border-red-500/40 text-red-400' },
            'murder': { label: 'HOMICIDE', color: 'bg-red-500/20 border-red-500/40 text-red-400' },
            'kill': { label: 'HOMICIDE', color: 'bg-red-500/20 border-red-500/40 text-red-400' },
            'cyber': { label: 'CYBER-BREACH', color: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400' },
            'hack': { label: 'CYBER-BREACH', color: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400' },
            'bribe': { label: 'CORRUPTION', color: 'bg-violet-500/20 border-violet-500/40 text-violet-400' },
            'theft': { label: 'THEFT', color: 'bg-violet-500/20 border-violet-500/40 text-violet-400' },
            'stole': { label: 'THEFT', color: 'bg-violet-500/20 border-violet-500/40 text-violet-400' },
            'assault': { label: 'ASSAULT', color: 'bg-red-500/20 border-red-500/40 text-red-400' },
            'financial': { label: 'FINANCIAL', color: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400' }
        };

        Object.keys(tagsMapping).forEach(key => {
            if (investigateText.includes(key)) {
                if (!generatedTags.find(t => t.label === tagsMapping[key].label)) {
                    generatedTags.push(tagsMapping[key]);
                }
            }
        });

        // Always have at least one Critical tag
        if (generatedTags.length === 0) {
            generatedTags.push({ label: 'CRITICAL', color: 'bg-red-500/20 border-red-500/40 text-red-400' });
        }

        const tagsContainer = document.getElementById('res-tags');
        tagsContainer.innerHTML = '';
        generatedTags.forEach(tag => {
            tagsContainer.innerHTML += `<span class="text-xs px-2 py-0.5 rounded border font-bold uppercase ${tag.color}">${tag.label}</span>`;
        });

        // Raw Evidence Blocks - Using Cyber Card aesthetic
        evidenceContainer.innerHTML = '';
        raw_evidence.forEach((item, idx) => {
            const fileDesc = (item.file_name || 'unknown').split('.').pop().toUpperCase() + ' FILE';
            
            const mime = item.file_type || '';
            const rawPath = `/data/raw/${item.file_name}`;
            
            let htmlCard = document.createElement('div');
            // Cycle through neon colors for visual variance
            const colorThemes = [
                { border: 'neon-border-cyan', bg: 'bg-cyan-500/10', borderInner: 'border-cyan-500/20', text: 'text-cyan-400', shadow: 'shadow-[0_0_15px_rgba(0,243,255,0.3)]', badgeBg: 'bg-cyan-500/20', badgeBorder: 'border-cyan-500/30' },
                { border: 'neon-border-violet', bg: 'bg-violet-500/10', borderInner: 'border-violet-500/20', text: 'text-violet-400', shadow: 'shadow-[0_0_15px_rgba(188,19,254,0.3)]', badgeBg: 'bg-violet-500/20', badgeBorder: 'border-violet-500/30' },
                { border: 'neon-border-red', bg: 'bg-red-500/10', borderInner: 'border-red-500/20', text: 'text-red-400', shadow: 'shadow-[0_0_15px_rgba(255,0,60,0.3)]', badgeBg: 'bg-red-500/20', badgeBorder: 'border-red-500/30' }
            ];
            
            const theme = colorThemes[idx % colorThemes.length];
            htmlCard.className = `${theme.border} bg-black/40 rounded-xl p-4 group cursor-pointer hover:bg-black/80 transition-all border border-white/5`;

            let iconClass = 'lucide:file-text';
            if (mime.includes('image')) iconClass = 'lucide:image';
            if (mime.includes('audio')) iconClass = 'lucide:music';
            if (mime.includes('pdf')) iconClass = 'lucide:file-check-2';
            if (mime.includes('csv')) iconClass = 'lucide:database';

            const extractedText = (item.evidence && item.evidence.content) ? item.evidence.content.substring(0, 150) + "..." : "No reliable text extracted.";

            let innerHTML = `
                <div class="flex items-start gap-4">
                    <div class="w-14 h-14 rounded-lg flex items-center justify-center shrink-0 border transition-all ${theme.bg} ${theme.borderInner} ${theme.text} group-hover:${theme.shadow}">
                        <iconify-icon icon="${iconClass}" class="text-3xl"></iconify-icon>
                    </div>
                    <div class="flex-1 overflow-hidden">
                        <div class="flex justify-between items-center">
                            <h5 class="text-sm font-bold text-white truncate uppercase" title="${item.file_name}">${item.file_name}</h5>
                            <span class="text-xs font-bold px-2 py-0.5 rounded border ${theme.badgeBg} ${theme.badgeBorder} ${theme.text}">PROCESSED</span>
                        </div>
                        <p class="text-xs text-gray-500 mt-1 uppercase tracking-tighter">Status: EXTRACTED // Type: ${fileDesc}</p>
                        
                        <div class="mt-3 text-sm text-gray-400 font-mono leading-tight whitespace-pre-wrap">${extractedText}</div>
            `;

            // Append Media if applies
            if (mime.includes('image')) {
                innerHTML += `
                    <div class="mt-4 rounded border border-white/10 overflow-hidden opacity-90 group-hover:opacity-100 transition-opacity">
                        <img src="${rawPath}" class="w-full h-auto max-h-32 object-cover object-top" alt="Evidence Preview">
                    </div>
                `;
            } else if (mime.includes('audio')) {
                innerHTML += `
                    <div class="mt-4 p-2 bg-black/50 rounded border border-white/10 opacity-90 group-hover:opacity-100 transition-opacity align-middle">
                        <audio controls class="w-full h-8 outline-none">
                            <source src="${rawPath}" type="${mime}">
                        </audio>
                    </div>
                `;
            }

            innerHTML += `
                    </div>
                </div>
            `;
            htmlCard.innerHTML = innerHTML;
            evidenceContainer.appendChild(htmlCard);
        });
        // --- Save Analytics to localStorage & enable nav button ---
        if (analytics) {
            localStorage.setItem('forensic_analytics', JSON.stringify(analytics));
            localStorage.setItem('forensic_analytics_ts', Date.now().toString());
            
            // Enable the Analytics nav button
            const navBtn = document.getElementById('analytics-nav-btn');
            if (navBtn) {
                navBtn.classList.remove('opacity-40', 'pointer-events-none');
                navBtn.classList.add('opacity-100', 'shadow-[0_0_15px_rgba(57,255,20,0.2)]');
                navBtn.title = 'View Forensic Analytics';
            }
        }
    }

    // --- Reset / New Case Logic ---
    resetBtn.addEventListener('click', () => {
        if (confirm("Clear current investigation data and start a new case?")) {
            // Clear Storage
            localStorage.removeItem('forensic_dashboard_data');
            localStorage.removeItem('forensic_analytics');
            localStorage.removeItem('forensic_analytics_ts');

            // Reset State Variables
            selectedFiles = [];
            hasRestoredFromCache = false;

            // Reset UI components
            renderFileList();
            updateFlowchartState(0);
            
            // Re-disable analytics button
            const navBtn = document.getElementById('analytics-nav-btn');
            if (navBtn) {
                navBtn.classList.add('opacity-40', 'pointer-events-none');
                navBtn.classList.remove('opacity-100', 'shadow-[0_0_15px_rgba(57,255,20,0.2)]');
                navBtn.title = 'Run analysis first';
            }

            // Clear Dashboard Displays
            document.getElementById('res-culprit').textContent = "Awaiting ID";
            document.getElementById('res-culprit').classList.remove('text-gray-500');
            document.getElementById('res-culprit').classList.add('text-white');
            document.getElementById('res-confidence').textContent = "0%";
            document.getElementById('res-confidence-bar').style.width = "0%";
            document.getElementById('res-reasoning').innerHTML = "Awaiting data...";
            document.getElementById('res-key-evidence').innerHTML = "Awaiting parameters...";
            document.getElementById('res-eliminated').innerHTML = "Awaiting parameters...";
            document.getElementById('res-tags').innerHTML = '<span class="text-[8px] px-1 bg-red-500/20 border border-red-500/40 rounded text-red-400 font-bold uppercase">CRITICAL</span>';
            evidenceContainer.innerHTML = '';
            
            // Scroll back to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    // Small utility to parse bold asterisks correctly since server returns raw text
    function parseSimpleMarkdown(text) {
        return text.replace(/\*\*(.*?)\*\*/g, '<span class="text-white font-bold">$1</span>');
    }

});

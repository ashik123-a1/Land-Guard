/**
 * LandGuard Site-Wide Persistent Hands-Free Voice Assistant Controller ("Hello Daffodil")
 * 
 * Provides an authoritative, singleton, persistent hands-free voice control system
 * across all authenticated LandGuard pages (Citizen & Staff/Admin portals).
 * 
 * Preserves the opt-in hands-free session in sessionStorage across full-page navigation,
 * automatically reinitializes speech recognition upon destination page load,
 * supports consecutive voice commands without re-activation, executes real navigation,
 * and terminates exclusively upon explicit "Stop Daffodil" / "স্টপ ড্যাফোডিল" or stop controls.
 */

(function (window, document) {
    'use strict';

    // Prevent duplicate initializations
    if (window.LandGuardVoiceController) {
        return;
    }

    // Dedicated Voice Assistant HUD check:
    // If on /user/voice (where voice-hud-container or orbCanvas exists), voice.html runs its own
    // high-fidelity neural orb and spotter. We attach the sign-out listener and expose the facade
    // without starting a secondary recognition instance or overwriting voice.html's local handlers.
    if (document.getElementById('voice-hud-container') || document.getElementById('orbCanvas')) {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href*="/logout"]');
            if (link) {
                try { sessionStorage.removeItem('landguard_voice_hands_free'); } catch (err) {}
            }
        });
        window.LandGuardVoiceController = {
            isHandsFreeActive: () => (typeof window.isHandsFreeActive === 'function' ? window.isHandsFreeActive() : false),
            isSessionActive: () => (typeof window.isSessionActive === 'function' ? window.isSessionActive() : false),
            getCurrentState: () => (typeof window.getCurrentState === 'function' ? window.getCurrentState() : 'HANDS_FREE_OFF'),
            simulateSpeechInput: (t) => (typeof window.simulateSpeechInput === 'function' ? window.simulateSpeechInput(t) : null),
            toggleHandsFreeMode: () => (typeof window.toggleHandsFreeMode === 'function' ? window.toggleHandsFreeMode() : null),
            handleStopDaffodil: () => (typeof window.handleStopDaffodil === 'function' ? window.handleStopDaffodil() : null),
        };
        return;
    }

    /* =========================================================
       1. CONSTANTS & STATE DEFINITIONS
       ========================================================= */
    const STORAGE_KEY = 'landguard_voice_hands_free';

    const STATE = {
        HANDS_FREE_OFF: 'HANDS_FREE_OFF',
        WAKE_WORD_STANDBY: 'WAKE_WORD_STANDBY',
        COMMAND_LISTENING: 'COMMAND_LISTENING',
        PROCESSING: 'PROCESSING',
        SPEAKING: 'SPEAKING',
        RECOVERING: 'RECOVERING',
        ERROR: 'ERROR',
        // Compatibility Aliases for existing templates & test suites
        HANDS_FREE_DISABLED: 'HANDS_FREE_OFF',
        IDLE: 'HANDS_FREE_OFF',
        WAKE_WORD_DETECTED: 'COMMAND_LISTENING',
        LISTENING: 'COMMAND_LISTENING',
        LISTENING_COMMAND: 'COMMAND_LISTENING',
        ANALYZING: 'PROCESSING',
        PERMISSION_REQUIRED: 'ERROR'
    };

    const WAKE_WORD_REGEX = /(?:^|[^\p{L}\p{N}])(?:(?:hell?o+w?|hallo|hey|hi|hai|হ্যালো|হেলো|হাই|হে)[\s,.:;!?-]+)?(?:daff?od[ia]ll?|deff?od[ia]ll?|deafod[ia]ll?|defa[u]?lt?|ড্যাফোডিল|ডেফোডিল|ডাফোডিল|ডেফডিল|ড্যাফডিল|দেফোডিল|দ্যাফোডিল|ড্যাফোডেল|ডেফোডেল|ড্যাপোডিল|ডেপোডিল|ড্যাফুডিল|ডিফোডিল|ডিফডিল)(?:$|[^\p{L}\p{N}])/iu;
    const STOP_DAFFODIL_REGEX = /(?:^|[^\p{L}\p{N}])(?:(?:stop|shut\s+down|deactivate|exit|bye|goodbye|স্টপ|বন্ধ\s*করো?|থামো)[\s,.:;!?-]+(?:daff?od[ia]ll?|deff?od[ia]ll?|deafod[ia]ll?|defa[u]?lt?|ড্যাফোডিল|ডেফোডিল|ডাফোডিল|ডেফডিল|ড্যাফডিল|দেফোডিল|দ্যাফোডিল|ড্যাফোডেল|ডেফোডেল|ড্যাপোডিল|ডেপোডিল|ড্যাফুডিল|ডিফোডিল|ডিফডিল)|(?:daff?od[ia]ll?|deff?od[ia]ll?|deafod[ia]ll?|defa[u]?lt?|ড্যাফোডিল|ডেফোডিল|ডাফোডিল|ডেফডিল|ড্যাফডিল|দেফোডিল|দ্যাফোডিল|ড্যাফোডেল|ডেফোডেল|ড্যাপোডিল|ডেপোডিল|ড্যাফুডিল|ডিফোডিল|ডিফডিল)[\s,.:;!?-]+(?:stop|বন্ধ|থামো|বন্ধ\s*করো?)|turn\s+off\s+hands\s*free|disable\s+hands\s*free|হ্যান্ডস\s*ফ্রি\s*বন্ধ)(?:$|[^\p{L}\p{N}])/iu;

    /* =========================================================
       2. CONTROLLER SINGLETON STATE
       ========================================================= */
    function getSiteLanguage() {
        try {
            if (typeof document !== 'undefined' && document.documentElement) {
                const htmlLang = document.documentElement.lang;
                if (htmlLang === 'bn' || htmlLang === 'en') return htmlLang;
            }
            if (typeof document !== 'undefined' && document.cookie) {
                const match = document.cookie.match(/(?:^|;\s*)landguard_lang=(bn|en)(?:;|$)/);
                if (match && match[1]) return match[1];
            }
        } catch (e) {}
        return 'bn'; // Primary default is Bangla
    }

    let handsFreeActive = false;
    let isSessionActivated = false;
    let currentState = STATE.HANDS_FREE_OFF;
    let currentLanguage = 'auto'; // 'auto', 'en', 'bn'
    let autoSpeechLang = (getSiteLanguage() === 'en') ? 'en-US' : 'bn-BD';

    let wakeRecognition = null;
    let isStartingSpotter = false;
    let isSpotterPausedForTTS = false;
    let lastSpotterStartTime = 0;
    let consecutiveRestartCount = 0;
    let spotterRestartTimer = null;

    let currentAudio = null;
    let audioCtx = null;
    let lastSpokenText = '';
    let currentResponseData = null;
    const stateChangeListeners = [];

    /* =========================================================
       3. STORAGE PERSISTENCE HELPERS (sessionStorage)
       ========================================================= */
    function loadSession() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    }

    function saveSession(data) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch (e) {}
    }

    function clearSession() {
        try {
            sessionStorage.removeItem(STORAGE_KEY);
        } catch (e) {}
    }

    /* =========================================================
       4. WEB AUDIO FEEDBACK & CHIMES
       ========================================================= */
    function initAudioContext() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                audioCtx = new AudioContext();
            }
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume().catch(() => {});
        }
    }

    function playChime(type) {
        try {
            initAudioContext();
            if (!audioCtx) return;
            const now = audioCtx.currentTime;

            if (type === 'activate') {
                // High-tech ascending triple-tone
                const osc1 = audioCtx.createOscillator();
                const gain1 = audioCtx.createGain();
                osc1.type = 'sine';
                osc1.frequency.setValueAtTime(440, now);
                osc1.frequency.exponentialRampToValueAtTime(880, now + 0.12);
                gain1.gain.setValueAtTime(0.12, now);
                gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
                osc1.connect(gain1);
                gain1.connect(audioCtx.destination);
                osc1.start(now);
                osc1.stop(now + 0.25);

                const osc2 = audioCtx.createOscillator();
                const gain2 = audioCtx.createGain();
                osc2.type = 'sine';
                osc2.frequency.setValueAtTime(880, now + 0.1);
                osc2.frequency.exponentialRampToValueAtTime(1320, now + 0.26);
                gain2.gain.setValueAtTime(0.12, now + 0.1);
                gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.32);
                osc2.connect(gain2);
                gain2.connect(audioCtx.destination);
                osc2.start(now + 0.1);
                osc2.stop(now + 0.35);
            } else if (type === 'reply') {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(520, now);
                osc.frequency.exponentialRampToValueAtTime(660, now + 0.08);
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(now);
                osc.stop(now + 0.2);
            } else if (type === 'stop') {
                // Descending tone for deactivation
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(700, now);
                osc.frequency.exponentialRampToValueAtTime(200, now + 0.16);
                gain.gain.setValueAtTime(0.1, now);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.17);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(now);
                osc.stop(now + 0.18);
            }
        } catch (e) {}
    }

    /* =========================================================
       5. PHONETIC NORMALIZATION (Banglish / Romanized Bengali)
       ========================================================= */
    function normalizePhoneticInput(str) {
        if (!str) return str;
        let s = str.trim();
        s = s.replace(/\bdaag\b/gi, 'dag');
        s = s.replace(/\bkhatian\b/gi, 'khatian');
        s = s.replace(/\bporcha\b/gi, 'porcha');
        s = s.replace(/\bhellow\b/gi, 'hello');
        s = s.replace(/\b(?:deffodil|defodil|dafodil|deafodil|daffadil|daffodill)\b/gi, 'daffodil');
        s = s.replace(/\b(dak|dag)\s*(?:bam\s*bahut|bam|bahut|number|no\.?|#)?\s*(\d+)\b/gi, 'দাগ নম্বর $2');
        s = s.replace(/\b(\d+)\s*(?:er|te|e)\b/gi, '$1');
        return s;
    }

    function getActiveSpeechLang() {
        if (currentLanguage === 'bn') return 'bn-BD';
        if (currentLanguage === 'en') return 'en-US';
        const siteLang = getSiteLanguage();
        if (autoSpeechLang) return autoSpeechLang;
        return (siteLang === 'en') ? 'en-US' : 'bn-BD';
    }

    /* =========================================================
       6. STATE MANAGEMENT & VISUAL UI SYNCHRONIZATION
       ========================================================= */
    function setVisualState(newState) {
        currentState = newState;

        // Synchronize all UI elements that may exist on the page
        updateHandsFreeBtnUI();
        updateStatusLabelUI();

        // Notify subscribers (e.g., 3D orb canvas on voice.html)
        stateChangeListeners.forEach(fn => {
            try { fn(newState); } catch (e) {}
        });
    }

    function onVisualStateChange(fn) {
        if (typeof fn === 'function') {
            stateChangeListeners.push(fn);
        }
    }

    function updateHandsFreeBtnUI() {
        // Collect all toggle buttons and indicator elements
        const buttons = document.querySelectorAll('#handsFreeToggleBtn, .js-hands-free-toggle');
        const dots = document.querySelectorAll('#handsFreeDot, .js-hands-free-dot');
        const labels = document.querySelectorAll('#handsFreeLabel, .js-hands-free-label');

        if (handsFreeActive) {
            dots.forEach(dot => {
                if (currentState === STATE.COMMAND_LISTENING) {
                    dot.className = "w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse";
                } else if (currentState === STATE.PROCESSING) {
                    dot.className = "w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping";
                } else if (currentState === STATE.SPEAKING) {
                    dot.className = "w-2.5 h-2.5 rounded-full bg-fuchsia-400 animate-pulse";
                } else {
                    dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse";
                }
            });

            labels.forEach(label => {
                label.textContent = isSessionActivated ? 'Hands-Free: LISTENING' : 'Hands-Free: ON';
            });

            buttons.forEach(btn => {
                btn.classList.remove('bg-slate-900/90', 'border-slate-700', 'text-slate-300');
                btn.classList.add('bg-emerald-950/80', 'border-emerald-500/70', 'text-emerald-300');
            });
        } else {
            dots.forEach(dot => {
                dot.className = "w-2.5 h-2.5 rounded-full bg-slate-500";
            });

            labels.forEach(label => {
                label.textContent = 'Hands-Free: OFF';
            });

            buttons.forEach(btn => {
                btn.classList.remove('bg-emerald-950/80', 'border-emerald-500/70', 'text-emerald-300');
                btn.classList.add('bg-slate-900/90', 'border-slate-700', 'text-slate-300');
            });
        }
    }

    function updateStatusLabelUI() {
        const statusText = document.getElementById('statusText');
        if (!statusText) return;

        if (!handsFreeActive) {
            statusText.textContent = "HANDS-FREE OFF";
        } else if (currentState === STATE.COMMAND_LISTENING) {
            statusText.textContent = "LISTENING FOR COMMANDS...";
        } else if (currentState === STATE.PROCESSING) {
            statusText.textContent = "ANALYZING INTENT...";
        } else if (currentState === STATE.SPEAKING) {
            statusText.textContent = "SPEAKING...";
        } else if (currentState === STATE.WAKE_WORD_STANDBY) {
            statusText.textContent = 'STANDBY: SAY "HELLO DAFFODIL"';
        } else if (currentState === STATE.ERROR) {
            statusText.textContent = "MIC PERMISSION REQUIRED";
        } else {
            statusText.textContent = "STANDBY";
        }
    }

    /* =========================================================
       7. CONTINUOUS SPEECH RECOGNITION SPOTTER
       ========================================================= */
    function startHandsFreeSpotter() {
        if (!handsFreeActive) return;
        if (isSpotterPausedForTTS) return;
        if (isStartingSpotter) return;

        if (spotterRestartTimer) {
            clearTimeout(spotterRestartTimer);
            spotterRestartTimer = null;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setVisualState(STATE.ERROR);
            if (typeof window.showToast === 'function') {
                window.showToast("Web Speech API not supported in this browser for hands-free wake word.", "warning");
            }
            handsFreeActive = false;
            isSessionActivated = false;
            clearSession();
            updateHandsFreeBtnUI();
            return;
        }

        stopHandsFreeSpotter();

        const now = Date.now();
        if (now - lastSpotterStartTime < 500) {
            consecutiveRestartCount++;
            if (consecutiveRestartCount > 6) {
                spotterRestartTimer = setTimeout(() => {
                    consecutiveRestartCount = 0;
                    if (handsFreeActive && !wakeRecognition && !isSpotterPausedForTTS) {
                        startHandsFreeSpotter();
                    }
                }, 1200);
                return;
            }
        } else {
            consecutiveRestartCount = 0;
        }
        lastSpotterStartTime = now;
        isStartingSpotter = true;

        try {
            const rec = new SpeechRecognition();
            rec.continuous = true;
            rec.interimResults = false;
            rec.maxAlternatives = 3;
            rec.lang = getActiveSpeechLang();

            rec.onstart = () => {
                isStartingSpotter = false;
                if (handsFreeActive && currentState !== STATE.PROCESSING && currentState !== STATE.SPEAKING) {
                    setVisualState(isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY);
                }
            };

            rec.onresult = (e) => {
                if (!handsFreeActive) return;
                const lastIdx = e.results.length - 1;
                const res = e.results[lastIdx];
                if (!res || !res[0]) return;
                const rawTranscript = res[0].transcript;
                const altTranscripts = [];
                for (let i = 0; i < res.length; i++) {
                    if (res[i] && res[i].transcript) {
                        altTranscripts.push(res[i].transcript);
                    }
                }
                processSpotterTranscript(rawTranscript, altTranscripts);
            };

            rec.onerror = (e) => {
                isStartingSpotter = false;
                console.warn("[LandGuard Voice] Spotter error:", e.error);
                if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                    handsFreeActive = false;
                    isSessionActivated = false;
                    clearSession();
                    stopHandsFreeSpotter();
                    setVisualState(STATE.ERROR);
                    updateHandsFreeBtnUI();
                    if (typeof window.showToast === 'function') {
                        window.showToast("Microphone permission denied. Hands-Free mode disabled.", "error");
                    }
                    return;
                }
            };

            rec.onend = () => {
                wakeRecognition = null;
                isStartingSpotter = false;
                if (handsFreeActive && !document.hidden && !isSpotterPausedForTTS) {
                    const restartDelay = (consecutiveRestartCount > 2) ? 600 : 200;
                    spotterRestartTimer = setTimeout(() => {
                        if (handsFreeActive && !wakeRecognition && !isSpotterPausedForTTS) {
                            startHandsFreeSpotter();
                        }
                    }, restartDelay);
                }
            };

            rec.start();
            wakeRecognition = rec;
        } catch (err) {
            isStartingSpotter = false;
            console.error("[LandGuard Voice] Could not start hands-free recognition:", err);
        }
    }

    function stopHandsFreeSpotter() {
        if (spotterRestartTimer) {
            clearTimeout(spotterRestartTimer);
            spotterRestartTimer = null;
        }
        if (wakeRecognition) {
            try {
                wakeRecognition.onstart = null;
                wakeRecognition.onresult = null;
                wakeRecognition.onerror = null;
                wakeRecognition.onend = null;
                wakeRecognition.abort();
            } catch (e) {}
            wakeRecognition = null;
        }
        isStartingSpotter = false;
    }

    /* =========================================================
       8. TRANSCRIPT PROCESSING & EARLY STOP INTERCEPTION
       ========================================================= */
    function processSpotterTranscript(rawTranscript, altTranscripts = []) {
        if (!rawTranscript) return;
        let transcript = rawTranscript.trim();
        if (currentLanguage === 'auto') {
            transcript = normalizePhoneticInput(transcript);
        }

        const candidates = [transcript];
        if (Array.isArray(altTranscripts)) {
            altTranscripts.forEach(alt => {
                if (alt && typeof alt === 'string') {
                    let cleanedAlt = alt.trim();
                    if (currentLanguage === 'auto') cleanedAlt = normalizePhoneticInput(cleanedAlt);
                    if (!candidates.includes(cleanedAlt)) candidates.push(cleanedAlt);
                }
            });
        }

        // 1. Strict Stop Phrase Interception: Must be intercepted BEFORE ordinary intent dispatch!
        const stopCandidate = candidates.find(c => STOP_DAFFODIL_REGEX.test(c));
        if (stopCandidate) {
            console.log("[LandGuard Voice] Stop Daffodil phrase intercepted. Disabling hands-free.");
            handleStopDaffodil();
            return;
        }

        // 2. Check for Wake Word ("Hello Daffodil" or "হ্যালো ড্যাফোডিল")
        const wakeCandidate = candidates.find(c => WAKE_WORD_REGEX.test(c));
        if (wakeCandidate) {
            isSessionActivated = true;
            saveSession({
                enabled: true,
                mode: STATE.COMMAND_LISTENING,
                activated: true,
                language: currentLanguage
            });
            playChime('activate');
            setVisualState(STATE.COMMAND_LISTENING);

            let cleaned = wakeCandidate.replace(WAKE_WORD_REGEX, '').trim();
            cleaned = cleaned.replace(/^[,\s:;!?-]+|[,\s:;!?-]+$/g, '').trim();

            const inputElem = document.getElementById('voice-text-input');
            if (inputElem) inputElem.value = wakeCandidate;

            if (cleaned.length > 0) {
                // Compound command: "Hello Daffodil open verification history"
                setTimeout(() => {
                    submitQuery(wakeCandidate);
                }, 250);
            } else {
                // Standalone wake word: "Hello Daffodil"
                setTimeout(() => {
                    submitQuery(wakeCandidate);
                }, 200);
            }
            return;
        }

        // 3. Consecutive Commands: Once activated, accept subsequent commands seamlessly
        if (isSessionActivated || currentState === STATE.COMMAND_LISTENING) {
            const inputElem = document.getElementById('voice-text-input');
            if (inputElem) inputElem.value = transcript;
            submitQuery(transcript);
            return;
        }
    }

    /* =========================================================
       9. INTENT SUBMISSION & REAL CROSS-PAGE NAVIGATION
       ========================================================= */
    async function submitQuery(queryText) {
        if (!queryText || !queryText.trim()) return;

        let cleanQuery = queryText.trim();
        if (currentLanguage === 'auto') {
            cleanQuery = normalizePhoneticInput(cleanQuery);
        }
        const inputElem = document.getElementById('voice-text-input');
        if (inputElem) inputElem.value = cleanQuery;

        setVisualState(STATE.PROCESSING);
        const startTime = performance.now();

        try {
            const res = await fetch('/api/voice/parse-intent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: cleanQuery,
                    language: currentLanguage
                })
            });

            const elapsed = Math.round(performance.now() - startTime);
            const latencyEl = document.getElementById('telemetryLatency');
            if (latencyEl) latencyEl.innerText = `${elapsed}ms`;

            if (!res.ok) {
                setVisualState(handsFreeActive ? (isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY) : STATE.HANDS_FREE_OFF);
                if (typeof window.showToast === 'function') window.showToast("Voice parsing failed", "error");
                return;
            }

            const data = await res.json();
            currentResponseData = data;

            // In Auto mode: adapt subsequent speech recognition to detected language
            if (currentLanguage === 'auto' && data.language) {
                autoSpeechLang = (data.language === 'bn') ? 'bn-BD' : 'en-US';
                if (wakeRecognition) wakeRecognition.lang = autoSpeechLang;
            }

            handleIntentResponse(data);
        } catch (err) {
            setVisualState(handsFreeActive ? (isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY) : STATE.HANDS_FREE_OFF);
            if (typeof window.showToast === 'function') window.showToast("Error contacting voice server: " + err.message, "error");
        }
    }

    function handleIntentResponse(data) {
        // If Stop Daffodil was returned by server:
        if (data.intent === 'CONTROL_STOP_DAFFODIL' || (data.suggested_action && data.suggested_action.action === 'DEACTIVATE_HANDS_FREE')) {
            handleStopDaffodil();
            return;
        }

        // Render assistant response into HUD or compact toast
        renderAssistantResponse(data);

        // Check if suggested action is a navigation request
        if (data.suggested_action && data.suggested_action.action === 'NAVIGATE' && data.suggested_action.url) {
            const targetUrl = data.suggested_action.url;
            const currentPath = window.location.pathname;

            // If mutating action requiring confirmation, do not auto-navigate
            if (data.confirmation_required) {
                playSpokenAudio();
                return;
            }

            // Real Navigation: execute navigation ONLY if Hands-Free is active and target is different from current page
            if (handsFreeActive && targetUrl !== currentPath && targetUrl !== (currentPath + window.location.search)) {
                const respLang = (currentLanguage === 'auto') ? getSiteLanguage() : currentLanguage;
                const spokenMsg = (respLang === 'bn') ? data.spoken_response_bn : data.spoken_response_en;

                saveSession({
                    enabled: true,
                    mode: STATE.COMMAND_LISTENING,
                    activated: true,
                    language: currentLanguage,
                    speechToAnnounce: spokenMsg || '',
                    targetUrl: targetUrl
                });

                // Short delay to allow speech audio to initiate before navigation begins
                setTimeout(() => {
                    window.location.href = targetUrl;
                }, 350);
                return;
            } else {
                playSpokenAudio();
            }
        } else if (handsFreeActive && data.suggested_action && data.suggested_action.action === 'BACK') {
            saveSession({
                enabled: true,
                mode: STATE.COMMAND_LISTENING,
                activated: true,
                language: currentLanguage
            });
            setTimeout(() => {
                window.history.back();
            }, 350);
            return;
        } else {
            // General query response without navigation (e.g. plot data query, status check)
            playSpokenAudio();
        }
    }

    function renderAssistantResponse(data) {
        const respLang = (currentLanguage === 'auto') ? getSiteLanguage() : currentLanguage;
        lastSpokenText = (respLang === 'bn') ? data.spoken_response_bn : data.spoken_response_en;

        // Hidden hooks for accessibility and automated test inspection
        const hookBn = document.getElementById('spoken-bn');
        const hookEn = document.getElementById('spoken-en');
        if (hookBn) hookBn.innerText = data.spoken_response_bn || '';
        if (hookEn) hookEn.innerText = data.spoken_response_en || '';

        // If on full Voice HUD page, render full cards
        const fullCard = document.getElementById('response-card');
        if (fullCard) {
            fullCard.classList.remove('hidden');

            const intentBadge = document.getElementById('response-intent-badge');
            if (intentBadge) intentBadge.innerText = data.intent || 'UNKNOWN_INTENT';

            const confBadge = document.getElementById('response-confidence-badge');
            if (confBadge) confBadge.innerText = `CONFIDENCE: ${(data.confidence * 100).toFixed(0)}%`;

            const primaryLabel = document.getElementById('primary-lang-label');
            const primaryText = document.getElementById('primary-spoken-text');
            const secondaryLabel = document.getElementById('secondary-lang-label');
            const secondaryText = document.getElementById('secondary-spoken-text');

            if (respLang === 'en') {
                if (primaryLabel) primaryLabel.innerText = "RESPONSE (ENGLISH / ARIA):";
                if (primaryText) primaryText.innerText = data.spoken_response_en || '';
                if (secondaryLabel) secondaryLabel.innerText = "অনুবাদ (বাংলা / নবানিতা):";
                if (secondaryText) secondaryText.innerText = data.spoken_response_bn || '';
            } else {
                if (primaryLabel) primaryLabel.innerText = "উত্তর (বাংলা / নবানিতা):";
                if (primaryText) primaryText.innerText = data.spoken_response_bn || '';
                if (secondaryLabel) secondaryLabel.innerText = "TRANSLATION (ENGLISH / ARIA):";
                if (secondaryText) secondaryText.innerText = data.spoken_response_en || '';
            }

            // Extracted entities
            const entDiv = document.getElementById('entities-container');
            if (entDiv) {
                entDiv.innerHTML = '';
                if (data.entities && Object.keys(data.entities).length > 0) {
                    for (const [k, v] of Object.entries(data.entities)) {
                        const pill = document.createElement('span');
                        pill.className = "px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-cyan-300";
                        pill.innerText = `${k.toUpperCase()}: ${v}`;
                        entDiv.appendChild(pill);
                    }
                }
            }

            // Explicit confirmation prompt
            const confDiv = document.getElementById('confirmation-container');
            if (confDiv) {
                if (data.confirmation_required) {
                    confDiv.className = "p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-1.5 text-left";
                    confDiv.innerHTML = `
                        <div class="flex items-center gap-2 text-amber-400 font-bold text-xs font-mono">
                            <i data-lucide="shield-alert" class="w-4 h-4"></i>
                            <span>EXPLICIT CITIZEN CONFIRMATION REQUIRED / দাখিল নিশ্চিতকরণ আবশ্যক</span>
                        </div>
                        <p class="text-xs text-amber-200/90 leading-relaxed font-sans">
                            Please review the drafted grievance parameters above. This action will initiate an official investigation docket on the Cadastral Registry. Click the button below to confirm and review the formal submission form.
                        </p>
                    `;
                    confDiv.classList.remove('hidden');
                } else {
                    confDiv.classList.add('hidden');
                }
            }

            // Action deep link container
            const actDiv = document.getElementById('action-container');
            if (actDiv) {
                actDiv.innerHTML = '';
                if (data.suggested_action && (data.suggested_action.url || data.suggested_action.action === "BACK")) {
                    const isBack = data.suggested_action.action === "BACK";
                    const targetUrl = data.suggested_action.url;

                    const btn = document.createElement('a');
                    btn.href = targetUrl || "javascript:window.history.back()";
                    btn.className = "px-4 py-2 rounded-xl text-xs font-semibold text-navy-950 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 transition-all flex items-center gap-1.5 shadow-lg shadow-cyan-500/20";
                    btn.innerHTML = `<i data-lucide="${isBack ? 'arrow-left' : 'external-link'}" class="w-3.5 h-3.5"></i><span>${data.suggested_action.label || 'Proceed to Portal'}</span>`;
                    actDiv.appendChild(btn);

                    const navBadge = document.createElement('div');
                    navBadge.id = "auto-nav-countdown";
                    navBadge.className = "mr-auto px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-xs font-mono text-cyan-300 flex items-center gap-2";
                    navBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span><span>Target: <strong>${data.suggested_action.label || 'Portal Page'}</strong> (Hands-Free Active)</span>`;
                    actDiv.prepend(navBadge);
                }
            }
            if (window.lucide) window.lucide.createIcons();
        } else {
            // On other pages (non-voice HUD): show sleek toast
            if (typeof window.showToast === 'function') {
                const toastMsg = (respLang === 'bn') ? data.spoken_response_bn : data.spoken_response_en;
                if (toastMsg) {
                    window.showToast(`Assistant: ${toastMsg}`, 'info', 4000);
                }
            }
        }
    }

    /* =========================================================
       10. AUDIO PLAYBACK & SYNTHESIS
       ========================================================= */
    function stopAllAudio() {
        isSpotterPausedForTTS = false;
        if (currentAudio) {
            try {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {}
            currentAudio = null;
        }
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }
        setAudioIndicator(false);
        setVisualState(handsFreeActive ? (isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY) : STATE.HANDS_FREE_OFF);
        playChime('stop');
    }

    function onSpeechOutputEnded() {
        isSpotterPausedForTTS = false;
        setAudioIndicator(false);
        currentAudio = null;
        if (handsFreeActive) {
            setVisualState(isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY);
            setTimeout(() => {
                if (handsFreeActive && !wakeRecognition && !isSpotterPausedForTTS) {
                    startHandsFreeSpotter();
                }
            }, 180);
        } else {
            setVisualState(STATE.HANDS_FREE_OFF);
        }
    }

    function setAudioIndicator(isPlaying, label = "Speaking...") {
        const pill = document.getElementById('audio-status-pill');
        const textSpan = document.getElementById('audio-status-text');
        if (pill && textSpan) {
            if (isPlaying) {
                textSpan.innerText = label;
                pill.classList.remove('hidden');
            } else {
                pill.classList.add('hidden');
            }
        }
    }

    function playSpokenAudio(specificLang = null) {
        if (currentAudio) {
            try {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {}
            currentAudio = null;
        }

        isSpotterPausedForTTS = true;
        if (wakeRecognition) {
            try {
                wakeRecognition.onend = null;
                wakeRecognition.abort();
            } catch (e) {}
            wakeRecognition = null;
        }

        let lang = specificLang;
        if (!lang) {
            if (currentLanguage === 'bn') lang = 'bn';
            else if (currentLanguage === 'en') lang = 'en';
            else lang = getSiteLanguage();
        }

        let textToSpeak = '';
        if (lang === 'bn') {
            textToSpeak = currentResponseData ? currentResponseData.spoken_response_bn : lastSpokenText;
        } else {
            textToSpeak = currentResponseData ? currentResponseData.spoken_response_en : lastSpokenText;
        }

        if (!textToSpeak || !textToSpeak.trim()) {
            onSpeechOutputEnded();
            return;
        }

        // 1. High-fidelity Neural TTS via backend (/api/voice/tts)
        try {
            const ttsUrl = `/api/voice/tts?text=${encodeURIComponent(textToSpeak.trim())}&lang=${lang}`;
            const audio = new Audio(ttsUrl);
            currentAudio = audio;

            setAudioIndicator(true, lang === 'bn' ? "নবানিতা (বাংলা)..." : "Aria (English)...");
            setVisualState(STATE.SPEAKING);
            playChime('reply');

            audio.addEventListener('ended', onSpeechOutputEnded);
            audio.addEventListener('error', (err) => {
                console.warn("[LandGuard Voice] Backend neural TTS stream error, attempting Web Speech fallback:", err);
                fallbackBrowserSpeak(textToSpeak, lang);
            });

            audio.play().catch(playErr => {
                console.warn("[LandGuard Voice] Audio autoplay blocked, trying Web Speech fallback:", playErr);
                fallbackBrowserSpeak(textToSpeak, lang);
            });
        } catch (err) {
            console.warn("[LandGuard Voice] Exception during audio playback, using Web Speech fallback:", err);
            fallbackBrowserSpeak(textToSpeak, lang);
        }
    }

    function fallbackBrowserSpeak(text, lang) {
        setAudioIndicator(false);
        if (!('speechSynthesis' in window)) {
            onSpeechOutputEnded();
            return;
        }
        try {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = (lang === 'bn') ? 'bn-BD' : 'en-US';
            utterance.rate = 1.0;
            utterance.onstart = () => { setVisualState(STATE.SPEAKING); };
            utterance.onend = onSpeechOutputEnded;
            utterance.onerror = onSpeechOutputEnded;
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            onSpeechOutputEnded();
        }
    }

    /* =========================================================
       11. TOGGLE, STOP & RESTORATION LIFECYCLE
       ========================================================= */
    function toggleHandsFreeMode() {
        initAudioContext();
        handsFreeActive = !handsFreeActive;

        if (handsFreeActive) {
            isSessionActivated = false;
            saveSession({
                enabled: true,
                mode: STATE.WAKE_WORD_STANDBY,
                activated: false,
                language: currentLanguage
            });
            startHandsFreeSpotter();
            playChime('activate');
            updateHandsFreeBtnUI();
            setVisualState(STATE.WAKE_WORD_STANDBY);
            if (typeof window.showToast === 'function') {
                window.showToast("Hands-Free Mode Enabled. Say 'Hello Daffodil' to activate.", "success");
            }
        } else {
            handleStopDaffodil();
        }
    }

    function handleStopDaffodil() {
        if (currentAudio) {
            try {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {}
            currentAudio = null;
        }
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }
        setAudioIndicator(false);
        stopHandsFreeSpotter();

        handsFreeActive = false;
        isSessionActivated = false;
        isSpotterPausedForTTS = false;
        clearSession();

        updateHandsFreeBtnUI();
        setVisualState(STATE.HANDS_FREE_OFF);
        playChime('stop');

        if (typeof window.showToast === 'function') {
            window.showToast("Hands-Free Mode Deactivated ('Stop Daffodil' recognized).", "info");
        }

        const inputElem = document.getElementById('voice-text-input');
        if (inputElem) inputElem.value = "Stop Daffodil";
        const statusText = document.getElementById('statusText');
        if (statusText) statusText.textContent = "HANDS-FREE OFF";
    }

    function handleSignOut() {
        clearSession();
        stopHandsFreeSpotter();
        stopAllAudio();
        handsFreeActive = false;
        isSessionActivated = false;
    }

    function restoreHandsFreeSession() {
        const saved = loadSession();
        if (!saved || !saved.enabled) {
            handsFreeActive = false;
            isSessionActivated = false;
            setVisualState(STATE.HANDS_FREE_OFF);
            updateHandsFreeBtnUI();
            return;
        }

        // Restore active hands-free session across page load
        handsFreeActive = true;
        isSessionActivated = !!saved.activated;
        if (saved.language) currentLanguage = saved.language;

        setVisualState(isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY);
        updateHandsFreeBtnUI();

        // Check if there was an announcement to speak or toast upon arrival
        if (saved.speechToAnnounce) {
            const announcement = saved.speechToAnnounce;
            // Clear announcement so it does not repeat on page reload
            saveSession({
                enabled: true,
                mode: isSessionActivated ? STATE.COMMAND_LISTENING : STATE.WAKE_WORD_STANDBY,
                activated: isSessionActivated,
                language: currentLanguage,
                speechToAnnounce: ''
            });

            const hookEn = document.getElementById('spoken-en');
            if (hookEn) hookEn.innerText = announcement;
            const hookBn = document.getElementById('spoken-bn');
            if (hookBn) hookBn.innerText = announcement;

            if (typeof window.showToast === 'function') {
                window.showToast(`Assistant: ${announcement}`, 'info', 3500);
            }

            // Play announcement and then resume spotter
            lastSpokenText = announcement;
            playSpokenAudio(currentLanguage === 'auto' ? getSiteLanguage() : currentLanguage);
        } else {
            startHandsFreeSpotter();
        }
    }

    /* =========================================================
       12. COMPACT FLOATING WIDGET FOR NON-VOICE PAGES
       ========================================================= */
    function injectCompactFloatingHUDIfNeeded() {
        // Floating corner HUD disabled per user preference (topbar pill retains full functionality)
        const existing = document.getElementById('landguard-floating-voice-widget');
        if (existing) {
            existing.remove();
        }
        return;
    }

    /* =========================================================
       13. EVENT LISTENERS & BOOTSTRAP
       ========================================================= */
    // Global Sign-Out listener
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a[href*="/logout"]');
        if (link) {
            handleSignOut();
        }
    });

    // Privacy & Lifecycle Management: auto-pause on background tab
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            if (wakeRecognition) {
                try { wakeRecognition.abort(); } catch (e) {}
            }
            if (currentAudio) {
                try { currentAudio.pause(); } catch (e) {}
            }
        } else {
            if (handsFreeActive && !wakeRecognition && !isSpotterPausedForTTS) {
                startHandsFreeSpotter();
            }
        }
    });

    // Beforeunload: abort temporary audio streams without destroying saved sessionStorage
    window.addEventListener('beforeunload', () => {
        if (wakeRecognition) {
            try { wakeRecognition.abort(); } catch (e) {}
        }
        if (currentAudio) {
            try { currentAudio.pause(); } catch (e) {}
        }
    });

    function init() {
        injectCompactFloatingHUDIfNeeded();
        restoreHandsFreeSession();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    /* =========================================================
       14. GLOBAL EXPORTS
       ========================================================= */
    const controller = {
        STATE,
        toggleHandsFreeMode,
        handleStopDaffodil,
        handleSignOut,
        processSpotterTranscript,
        submitQuery,
        playSpokenAudio,
        stopAllAudio,
        onVisualStateChange,
        setVisualState,
        isHandsFreeActive: () => handsFreeActive,
        isSessionActive: () => isSessionActivated,
        getCurrentState: () => currentState
    };

    window.LandGuardVoiceController = controller;

    // Direct window-level helpers for backward compatibility and automated UI testing
    window.toggleHandsFreeMode = toggleHandsFreeMode;
    window.handleStopDaffodil = handleStopDaffodil;
    window.handleSignOut = handleSignOut;
    window.processSpotterTranscript = processSpotterTranscript;
    window.simulateSpeechInput = function (transcript) {
        processSpotterTranscript(transcript);
    };
    window.submitQuery = submitQuery;
    window.playSpokenAudio = playSpokenAudio;
    window.stopAllAudio = stopAllAudio;
    window.setVisualState = setVisualState;
    window.STATE = STATE;
    window.isHandsFreeActive = () => handsFreeActive;
    window.isSessionActive = () => isSessionActivated;
    window.getCurrentState = () => currentState;

})(window, document);

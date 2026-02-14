document.addEventListener("DOMContentLoaded", () => {

    // ----------------------
    // Configuration
    // ----------------------
    const MESSAGES_PER_BATCH = 20;

    // ----------------------
    // Elements
    // ----------------------
    const container = document.getElementById("chat");
    const searchInput = document.getElementById("searchBox");
    const toggleBtn = document.getElementById("toggleHeaderBtn");
    const headerContent = document.getElementById("headerContent");
    const exportAnnotationsBtn = document.getElementById("exportAnnotationsBtn");
    const importAnnotationsBtn = document.getElementById("importAnnotationsBtn");
    const importAnnotationsInput = document.getElementById("importAnnotationsInput");
    const annotationFeedback = document.getElementById("annotationFeedback");

    let filteredMessages = messages.slice(); // initially all messages
    let currentIndex = 0;

    // Toogle header visibility
    toggleBtn.addEventListener("click", () => {
        if (headerContent.style.display === "none") {
            headerContent.style.display = "block";
        } else {
            headerContent.style.display = "none";
        }
        resizeChatContainer(); // adjust chat height after toggle
    });

    // Function to resize chat container
    function resizeChatContainer() {
        const headerHeight = headerContent.offsetHeight || 0;
        const searchHeight = searchBox.offsetHeight || 0;
        const windowHeight = window.innerHeight;
        const padding = 220; // space from bottom

        const newHeight = windowHeight - headerHeight - searchHeight - padding;
        container.style.height = newHeight + "px";
    }

    // Initial resize
    resizeChatContainer();

    // Resize on window resize
    window.addEventListener("resize", resizeChatContainer);

    // Filtering stuff
    const chatFilter = document.getElementById("chatFilter");
    const senderFilter = document.getElementById("senderFilter");
    const mediaFilter = document.getElementById("mediaFilter");
    const tagFilter = document.getElementById("tagFilter");
    const timePreset = document.getElementById("timePreset");
    const timeRange = document.getElementById("timeRange");
    const timeFrom = document.getElementById("timeFrom");
    const timeTo = document.getElementById("timeTo");
    const messageCount = document.getElementById("messageCount");

    const DEFAULT_TAGS = ["Important", "Relevant", "Follow-up"];
    const TAG_COLOR_MAP = {
        "Important": "#dc2626",
        "Relevant": "#2563eb",
        "Follow-up": "#eab308"
    };
    const tagAssignments = new Map();

    const uniqueChats = [...new Set(messages.map(msg => msg.chat || "Chat"))]
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));

    function normalizeTagName(value) {
        return (value || "").trim().replace(/\s+/g, " ");
    }

    function getMessageKey(msg) {
        return [
            msg.chat || "",
            msg.timestamp || "",
            msg.sender || "",
            msg.content || "",
            msg.media || ""
        ].join("||");
    }

    function simpleHash(text) {
        let hash = 0;
        const value = String(text || "");
        for (let i = 0; i < value.length; i++) {
            hash = ((hash << 5) - hash) + value.charCodeAt(i);
            hash |= 0;
        }
        return Math.abs(hash).toString(16);
    }

    function buildReportId() {
        const count = messages.length;
        const first = messages[0] ? getMessageKey(messages[0]) : "";
        const last = messages[count - 1] ? getMessageKey(messages[count - 1]) : "";
        const chatSeed = [...new Set(messages.map(msg => msg.chat || "Chat"))].sort().join("|");
        return `report-${simpleHash(`${count}|${first}|${last}|${chatSeed}`)}`;
    }

    function showAnnotationFeedback(text) {
        if (!annotationFeedback) return;
        annotationFeedback.textContent = text;
        window.setTimeout(() => {
            if (annotationFeedback.textContent === text) {
                annotationFeedback.textContent = "";
            }
        }, 2200);
    }

    const REPORT_ID = buildReportId();
    const TAG_STORAGE_KEY = `bubbly_tags_v1:${REPORT_ID}`;

    function saveTagState() {
        const payload = {
            version: 1,
            report_id: REPORT_ID,
            updated_at: new Date().toISOString(),
            assignments: Object.fromEntries(tagAssignments)
        };
        try {
            localStorage.setItem(TAG_STORAGE_KEY, JSON.stringify(payload));
        } catch (_) {
            // Non-fatal if storage is unavailable.
        }
    }

    function loadTagState() {
        try {
            const raw = localStorage.getItem(TAG_STORAGE_KEY);
            if (!raw) return;
            const parsed = JSON.parse(raw);
            if (parsed.report_id && parsed.report_id !== REPORT_ID) {
                return;
            }
            if (parsed.assignments && typeof parsed.assignments === "object") {
                Object.entries(parsed.assignments).forEach(([key, tags]) => {
                    if (!Array.isArray(tags)) return;
                    const normalized = tags
                        .map(normalizeTagName)
                        .filter(tag => tag && DEFAULT_TAGS.includes(tag));
                    if (normalized.length > 0) {
                        tagAssignments.set(key, normalized);
                    }
                });
            }
        } catch (_) {
            // Ignore invalid storage content.
        }
    }

    function applyAnnotationPayload(parsed, allowMismatchedReport = false) {
        if (!parsed || typeof parsed !== "object") {
            throw new Error("Invalid annotation file format.");
        }
        if (!allowMismatchedReport && parsed.report_id && parsed.report_id !== REPORT_ID) {
            throw new Error("Annotation file belongs to another report.");
        }
        tagAssignments.clear();
        if (parsed.assignments && typeof parsed.assignments === "object") {
            Object.entries(parsed.assignments).forEach(([key, tags]) => {
                if (!Array.isArray(tags)) return;
                const normalized = tags
                    .map(normalizeTagName)
                    .filter(tag => tag && DEFAULT_TAGS.includes(tag));
                if (normalized.length > 0) {
                    tagAssignments.set(key, normalized);
                }
            });
        }
        saveTagState();
    }

    function getMessageTags(msg) {
        return tagAssignments.get(msg.__msgKey) || [];
    }

    function buildMultiSelect(container, options, placeholder, single = false, showBulk = false) {
        container.classList.add(single ? "single-select" : "multi-select");
        container.innerHTML = `
            <button type="button" class="multi-select__button">${placeholder}</button>
            <div class="multi-select__panel">
                <input type="text" class="multi-select__search" placeholder="Search...">
                ${showBulk ? '<div class="multi-select__bulk"><button type="button" class="multi-select__bulk-btn" data-action="select">Select all</button><button type="button" class="multi-select__bulk-btn" data-action="clear">Clear</button></div>' : ""}
                <div class="multi-select__list"></div>
            </div>
        `;
        const button = container.querySelector(".multi-select__button");
        const panel = container.querySelector(".multi-select__panel");
        const search = container.querySelector(".multi-select__search");
        const list = container.querySelector(".multi-select__list");
        const bulk = container.querySelector(".multi-select__bulk");
        let currentOptions = options.slice();
        const selected = new Set();

        function updateButtonLabel() {
            if (selected.size === 0) {
                button.textContent = placeholder;
                return;
            }
            const labels = currentOptions
                .filter(opt => selected.has(opt.value))
                .map(opt => opt.label);
            if (single) {
                button.textContent = labels[0] || placeholder;
                return;
            }
            if (labels.length <= 2) {
                button.textContent = labels.join(", ");
            } else {
                button.textContent = `${labels.length} selected`;
            }
        }

        function renderList(filterText) {
            list.innerHTML = "";
            const text = (filterText || "").toLowerCase();
            currentOptions
                .filter(opt => opt.label.toLowerCase().includes(text))
                .forEach(opt => {
                    const row = document.createElement("label");
                    row.className = "multi-select__option";
                    const checkbox = document.createElement("input");
                    checkbox.type = "checkbox";
                    checkbox.value = opt.value;
                    checkbox.checked = selected.has(opt.value);
                    checkbox.addEventListener("change", () => {
                        if (single) {
                            selected.clear();
                            if (checkbox.checked) {
                                selected.add(opt.value);
                            }
                            renderList(search.value);
                        } else {
                            if (checkbox.checked) {
                                selected.add(opt.value);
                            } else {
                                selected.delete(opt.value);
                            }
                        }
                        updateButtonLabel();
                        applyFilters();
                    });
                    row.appendChild(checkbox);
                    if (opt.color) {
                        const dot = document.createElement("span");
                        dot.className = "tag-color-dot";
                        dot.style.background = opt.color;
                        row.appendChild(dot);
                    }
                    const textNode = document.createElement("span");
                    textNode.textContent = opt.label;
                    row.appendChild(textNode);
                    list.appendChild(row);
                });
            updateButtonLabel();
        }

        button.addEventListener("click", () => {
            container.classList.toggle("open");
            if (container.classList.contains("open")) {
                search.focus();
            }
        });

        search.addEventListener("input", () => renderList(search.value));
        if (bulk) {
            bulk.addEventListener("click", (event) => {
                const action = event.target.getAttribute("data-action");
                if (!action) return;
                if (action === "select") {
                    currentOptions.forEach(opt => selected.add(opt.value));
                } else if (action === "clear") {
                    selected.clear();
                }
                renderList(search.value);
                applyFilters();
            });
        }

        document.addEventListener("click", (event) => {
            if (!container.contains(event.target)) {
                container.classList.remove("open");
            }
        });

        renderList("");

        return {
            getSelected() {
                return Array.from(selected);
            },
            setOptions(newOptions) {
                const previous = new Set(selected);
                currentOptions = newOptions.slice();
                selected.clear();
                currentOptions.forEach(opt => {
                    if (previous.has(opt.value)) {
                        selected.add(opt.value);
                    }
                });
                renderList("");
            }
        };
    }

    const chatOptions = uniqueChats.map(chat => ({
        value: chat,
        label: chat
    }));
    const chatSelect = buildMultiSelect(chatFilter, chatOptions, "All chats", true);

    // Get unique senders
    const ownerNames = new Set(messages.filter(msg => msg.is_owner).map(msg => msg.sender));
    const uniqueSenders = [...new Set(messages.map(msg => msg.sender))]
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
    const senderOptions = uniqueSenders.map(sender => ({
        value: sender,
        label: ownerNames.has(sender) ? `${sender} (Owner)` : sender
    }));
    const senderSelect = buildMultiSelect(senderFilter, senderOptions, "All senders", false, true);

    const mediaOptions = [
        { value: "image", label: "Image" },
        { value: "video", label: "Video" },
        { value: "audio", label: "Audio" },
        { value: "pdf", label: "PDF" }
    ];
    const mediaSelect = buildMultiSelect(mediaFilter, mediaOptions, "All media");

    messages.forEach(msg => {
        msg.__msgKey = getMessageKey(msg);
    });
    loadTagState();
    const tagOptions = [...DEFAULT_TAGS]
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
        .map(tag => ({ value: tag, label: tag, color: TAG_COLOR_MAP[tag] || "#6b7280" }));
    const tagSelect = buildMultiSelect(tagFilter, tagOptions, "All tags", false, true);

    function parseTimestamp(timestamp) {
        if (!timestamp) return null;
        const text = timestamp.trim();

        // Android: "DD/MM/YYYY, HH:MM"
        let match = text.match(/^(\d{2})\/(\d{2})\/(\d{4}), (\d{2}):(\d{2})$/);
        if (match) {
            const [, dd, mm, yyyy, hh, min] = match;
            return new Date(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(min)).getTime();
        }

        // iOS: "DD.MM.YYYY, HH:MM"
        match = text.match(/^(\d{2})\.(\d{2})\.(\d{4}), (\d{2}):(\d{2})$/);
        if (match) {
            const [, dd, mm, yyyy, hh, min] = match;
            return new Date(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(min)).getTime();
        }

        // ISO 8601 without timezone: "YYYY-MM-DDTHH:MM:SS"
        match = text.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})$/);
        if (match) {
            const [, yyyy, mm, dd, hh, min, sec] = match;
            return new Date(
                Number(yyyy),
                Number(mm) - 1,
                Number(dd),
                Number(hh),
                Number(min),
                Number(sec || 0)
            ).getTime();
        }

        // ISO 8601 with timezone: "YYYY-MM-DDTHH:MM:SSZ" or "+/-HH:MM"
        match = text.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$/);
        if (match) {
            const parsed = Date.parse(text);
            return Number.isNaN(parsed) ? null : parsed;
        }

        return null;
    }

    function sortMessagesByTimestamp(inputMessages) {
        return inputMessages.slice().sort((a, b) => {
            const ta = parseTimestamp(a.timestamp);
            const tb = parseTimestamp(b.timestamp);
            if (ta === null && tb === null) return 0;
            if (ta === null) return 1;
            if (tb === null) return -1;
            return ta - tb;
        });
    }

    function getMediaCategory(msg) {
        if (!msg || !msg.media) return null;
        const mime = (msg.media_mime || "").toLowerCase();
        if (mime.startsWith("image/")) return "image";
        if (mime.startsWith("video/")) return "video";
        if (mime.startsWith("audio/")) return "audio";
        if (mime === "application/pdf") return "pdf";

        const ext = msg.media.includes(".") ? msg.media.split(".").pop().toLowerCase() : "";
        if (["jpg","jpeg","png","gif","webp"].includes(ext)) return "image";
        if (["mp4","mov","webm","3gp"].includes(ext)) return "video";
        if (["mp3","wav","m4a","aac","opus","ogg"].includes(ext)) return "audio";
        if (ext === "pdf") return "pdf";
        return null;
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function hashTag(tag) {
        let hash = 0;
        const text = String(tag || "");
        for (let i = 0; i < text.length; i++) {
            hash = ((hash << 5) - hash) + text.charCodeAt(i);
            hash |= 0;
        }
        return Math.abs(hash);
    }

    function getTagColor(tag) {
        if (TAG_COLOR_MAP[tag]) {
            return TAG_COLOR_MAP[tag];
        }
        const h = hashTag(tag) % 360;
        return `hsl(${h} 70% 45%)`;
    }

    function setTagOnMessage(msgKey, tag, enabled) {
        const current = new Set(tagAssignments.get(msgKey) || []);
        if (enabled) {
            current.add(tag);
        } else {
            current.delete(tag);
        }
        if (current.size === 0) {
            tagAssignments.delete(msgKey);
        } else {
            tagAssignments.set(msgKey, Array.from(current).sort((a, b) => a.localeCompare(b)));
        }
        saveTagState();
    }

    function applyFilters() {
    let filtered = messages.slice();

    // Filter by chat
    const chatValues = chatSelect.getSelected();
    if (chatValues.length > 0) {
        const chat = chatValues[0];
        filtered = filtered.filter(msg => (msg.chat || "Chat") === chat);
    }

    // Filter by sender (multi-select)
    const senderValues = senderSelect.getSelected();
    if (senderValues.length > 0) {
        filtered = filtered.filter(msg => senderValues.includes(msg.sender));
    }

    // Filter by media type (multi-select)
    const mediaTypes = mediaSelect.getSelected();
    if (mediaTypes.length > 0) {
        filtered = filtered.filter(msg => {
            if (!msg.media) return false;
            const category = getMediaCategory(msg);
            return category ? mediaTypes.includes(category) : false;
        });
    }

    // Filter by tags (multi-select, any selected tag matches)
    const selectedTags = tagSelect.getSelected();
    if (selectedTags.length > 0) {
        filtered = filtered.filter(msg => {
            const msgTags = getMessageTags(msg);
            return selectedTags.some(tag => msgTags.includes(tag));
        });
    }

    // Filter by time
    const preset = timePreset.value;
    const now = Date.now();
    let rangeStart = null;
    let rangeEnd = null;
    if (preset === "last24h") {
        rangeStart = now - 24 * 60 * 60 * 1000;
        rangeEnd = now;
    } else if (preset === "last30d") {
        rangeStart = now - 30 * 24 * 60 * 60 * 1000;
        rangeEnd = now;
    } else if (preset === "custom") {
        const fromValue = timeFrom.value ? new Date(timeFrom.value).getTime() : null;
        const toValue = timeTo.value ? new Date(timeTo.value).getTime() : null;
        rangeStart = fromValue;
        rangeEnd = toValue;
    }

    if (rangeStart !== null || rangeEnd !== null) {
        filtered = filtered.filter(msg => {
            const ts = parseTimestamp(msg.timestamp);
            if (ts === null) return false;
            if (rangeStart !== null && ts < rangeStart) return false;
            if (rangeEnd !== null && ts > rangeEnd) return false;
            return true;
        });
    }

    // Apply search too
    const query = searchInput.value.toLowerCase();
    if (query) {
        filtered = filtered.filter(msg =>
            msg.content.toLowerCase().includes(query) ||
            msg.sender.toLowerCase().includes(query) ||
            getMessageTags(msg).some(tag => tag.toLowerCase().includes(query))
        );
    }

        resetAndRender(sortMessagesByTimestamp(filtered));
    }

    searchInput.addEventListener("input", applyFilters);
    timePreset.addEventListener("change", () => {
        timeRange.style.display = timePreset.value === "custom" ? "inline-block" : "none";
        applyFilters();
    });
    timeFrom.addEventListener("change", applyFilters);
    timeTo.addEventListener("change", applyFilters);
    if (exportAnnotationsBtn) {
        exportAnnotationsBtn.addEventListener("click", () => {
            const payload = {
                version: 1,
                report_id: REPORT_ID,
                updated_at: new Date().toISOString(),
                assignments: Object.fromEntries(tagAssignments),
            };
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `bubbly_annotations_${REPORT_ID}.json`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(link.href);
            showAnnotationFeedback("Annotations exported.");
        });
    }
    if (importAnnotationsBtn && importAnnotationsInput) {
        importAnnotationsBtn.addEventListener("click", () => {
            importAnnotationsInput.value = "";
            importAnnotationsInput.click();
        });
        importAnnotationsInput.addEventListener("change", async () => {
            const file = importAnnotationsInput.files && importAnnotationsInput.files[0];
            if (!file) return;
            try {
                const raw = await file.text();
                const parsed = JSON.parse(raw);
                const mismatched = parsed && parsed.report_id && parsed.report_id !== REPORT_ID;
                if (mismatched) {
                    const proceed = window.confirm(
                        "This annotation file belongs to another report. Import anyway?"
                    );
                    if (!proceed) {
                        showAnnotationFeedback("Import canceled.");
                        return;
                    }
                }
                applyAnnotationPayload(parsed, mismatched);
                applyFilters();
                showAnnotationFeedback("Annotations imported.");
            } catch (error) {
                showAnnotationFeedback("Import failed.");
            }
        });
    }


    function renderMedia(msg) {
        const mediaFile = msg && msg.media ? msg.media : "";
        if (!mediaFile) return "";
        const mediaType = getMediaCategory(msg);
        const mime = (msg.media_mime || "").toLowerCase();

        const isMissing = mediaFile.startsWith("missing:");
        const displayName = isMissing ? mediaFile.replace(/^missing:/, "") : mediaFile;
        const missingNote = isMissing ? `<div class="media-missing">Missing media file</div>` : "";

        if (mediaType === "image") {
            // clickable image preview
            return `
            <div class="media">
                <a href="media/${displayName}" target="_blank">
                    <img src="media/${displayName}" alt="${displayName}">
                </a>
                ${missingNote}
            </div>`;
        } 
        else if (mediaType === "video") {
            return `
            <div class="media">
                <video class="chat-video" controls>
                    <source src="media/${displayName}" ${mime ? `type="${mime}"` : ""}>
                </video>
                ${missingNote}
            </div>`;
        } 
        else if (mediaType === "audio") {
            return `
            <div class="media">
                <audio controls>
                    <source src="media/${displayName}" ${mime ? `type="${mime}"` : ""}>
                </audio>
                ${missingNote}
            </div>`;
        } 
        else if (mediaType === "pdf") {
            return `<div class="media"><a href="media/${displayName}" target="_blank">${displayName}</a>${missingNote}</div>`;
        } 
        else {
            return `<div class="media"><a href="media/${displayName}" target="_blank">${displayName}</a>${missingNote}</div>`;
        }
    }

    // ----------------------
    // Render a batch of messages
    // ----------------------
    function renderNextBatch() {
        if (currentIndex >= filteredMessages.length) return;

        const endIndex = Math.min(currentIndex + MESSAGES_PER_BATCH, filteredMessages.length);

        const showChatTag = uniqueChats.length > 1;
        for (let i = currentIndex; i < endIndex; i++) {
            const msg = filteredMessages[i];
            const msgDiv = document.createElement("div");
            msgDiv.classList.add("bubble");


            let displayName = msg.sender;
            if (msg.is_owner) {
                displayName += " (Owner)";
            }
            // Bubble position
            if (msg.is_owner) {
                msgDiv.classList.add("right", "owner");
            } else {
                msgDiv.classList.add("left", "other");
            }




            // Message HTML
            const chatTag = showChatTag ? `<div class="chat-tag">${msg.chat || "Chat"}</div>` : "";
            const encodedKey = encodeURIComponent(msg.__msgKey || "");
            const currentTags = getMessageTags(msg);
            const tagsHtml = currentTags.length > 0
                ? `<div class="message-tags">${currentTags.map(tag => `<span class="message-tag" style="background:${getTagColor(tag)};color:#fff;">${escapeHtml(tag)}</span>`).join("")}</div>`
                : "";
            const tagOptionsHtml = [...DEFAULT_TAGS]
                .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
                .map(tag => {
                    const checked = currentTags.includes(tag) ? "checked" : "";
                    return `<label class="tag-option"><input type="checkbox" class="tag-checkbox" data-msg-key="${encodedKey}" data-tag="${escapeHtml(tag)}" ${checked}> <span class="tag-color-dot" style="background:${getTagColor(tag)};"></span><span>${escapeHtml(tag)}</span></label>`;
                })
                .join("");
            msgDiv.innerHTML = `
                ${chatTag}
                <p><strong>${displayName}</strong></p>
                <p>${msg.content.replace(/\n/g, "<br>")}</p>
                <span class="timestamp">${msg.timestamp}</span>
                ${renderMedia(msg)}
                ${tagsHtml}
                <div class="tag-editor">
                    <button type="button" class="tag-edit-btn" data-msg-key="${encodedKey}">Tags</button>
                    <div class="tag-panel hidden" data-msg-key="${encodedKey}">
                        ${tagOptionsHtml || '<div class="tag-option">No tags available</div>'}
                    </div>
                </div>
            `;

            container.appendChild(msgDiv);
        }

        currentIndex = endIndex;
    }

    container.addEventListener("click", (event) => {
        const button = event.target.closest(".tag-edit-btn");
        if (!button) return;
        const msgKey = button.getAttribute("data-msg-key");
        const panel = container.querySelector(`.tag-panel[data-msg-key="${msgKey}"]`);
        if (!panel) return;
        panel.classList.toggle("hidden");
    });

    container.addEventListener("change", (event) => {
        const checkbox = event.target.closest(".tag-checkbox");
        if (!checkbox) return;
        const msgKey = decodeURIComponent(checkbox.getAttribute("data-msg-key") || "");
        const tag = normalizeTagName(checkbox.getAttribute("data-tag") || "");
        if (!msgKey || !tag) return;
        setTagOnMessage(msgKey, tag, checkbox.checked);
        applyFilters();
    });

    document.addEventListener("click", (event) => {
        if (event.target.closest(".tag-editor")) return;
        container.querySelectorAll(".tag-panel").forEach(panel => panel.classList.add("hidden"));
    });

    // ----------------------
    // Reset & render (e.g., after search)
    // ----------------------
    function resetAndRender(newMessages) {
        container.innerHTML = "";
        filteredMessages = newMessages.slice();
        currentIndex = 0;
        updateMessageCount();
        renderNextBatch();
    }

    function updateMessageCount() {
        if (!messageCount) return;
        messageCount.textContent = `Showing ${filteredMessages.length} of ${messages.length} messages`;
    }

    // ----------------------
    // Lazy load on scroll
    // ----------------------
    container.addEventListener("scroll", () => {
        if (container.scrollTop + container.clientHeight >= container.scrollHeight - 10) {
            renderNextBatch();
        }
    });

    // ----------------------
    // Initial render
    // ----------------------
    resetAndRender(sortMessagesByTimestamp(filteredMessages));

});

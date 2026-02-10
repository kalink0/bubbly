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
        const padding = 180; // space from bottom

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
    const timePreset = document.getElementById("timePreset");
    const timeRange = document.getElementById("timeRange");
    const timeFrom = document.getElementById("timeFrom");
    const timeTo = document.getElementById("timeTo");
    const messageCount = document.getElementById("messageCount");

    const uniqueChats = [...new Set(messages.map(msg => msg.chat || "Chat"))]
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));

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
                    const textNode = document.createElement("span");
                    textNode.textContent = opt.label;
                    row.appendChild(checkbox);
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
                currentOptions = newOptions.slice();
                selected.clear();
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
            const ext = msg.media.split(".").pop().toLowerCase();
            if (mediaTypes.includes("image") && ["jpg","jpeg","png","gif","webp"].includes(ext)) return true;
            if (mediaTypes.includes("video") && ["mp4","mov","webm","3gp"].includes(ext)) return true;
            if (mediaTypes.includes("audio") && ["mp3","wav","m4a","aac","opus","ogg"].includes(ext)) return true;
            if (mediaTypes.includes("pdf") && ext === "pdf") return true;
            return false;
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
            msg.sender.toLowerCase().includes(query)
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


    function renderMedia(mediaFile) {
        if (!mediaFile) return "";
        const ext = mediaFile.split('.').pop().toLowerCase();

        const isMissing = mediaFile.startsWith("missing:");
        const displayName = isMissing ? mediaFile.replace(/^missing:/, "") : mediaFile;
        const missingNote = isMissing ? `<div class="media-missing">Missing media file</div>` : "";

        if (["jpg","jpeg","png","gif","webp"].includes(ext)) {
            // clickable image preview
            return `
            <div class="media">
                <a href="media/${displayName}" target="_blank">
                    <img src="media/${displayName}" alt="${displayName}">
                </a>
                ${missingNote}
            </div>`;
        } 
        else if (["mp4","mov","webm","3gp"].includes(ext)) {
            return `
            <div class="media">
                <video controls src="media/${displayName}" style="max-width:100%; border-radius:10px;"></video>
                ${missingNote}
            </div>`;
        } 
        else if (["mp3","wav","m4a","aac","opus","ogg"].includes(ext)) {
            return `
            <div class="media">
                <audio controls src="media/${displayName}"></audio>
                ${missingNote}
            </div>`;
        } 
        else if (ext === "pdf") {
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
            msgDiv.innerHTML = `
                ${chatTag}
                <p><strong>${displayName}</strong></p>
                <p>${msg.content.replace(/\n/g, "<br>")}</p>
                <span class="timestamp">${msg.timestamp}</span>
                ${renderMedia(msg.media)}
            `;

            container.appendChild(msgDiv);
        }

        currentIndex = endIndex;
    }

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

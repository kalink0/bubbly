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
        const padding = 140; // space from bottom

        const newHeight = windowHeight - headerHeight - searchHeight - padding;
        container.style.height = newHeight + "px";
    }

    // Initial resize
    resizeChatContainer();

    // Resize on window resize
    window.addEventListener("resize", resizeChatContainer);

    // Filtering stuff
    const senderFilter = document.getElementById("senderFilter");
    const mediaFilter = document.getElementById("mediaFilter");
    const timePreset = document.getElementById("timePreset");
    const timeRange = document.getElementById("timeRange");
    const timeFrom = document.getElementById("timeFrom");
    const timeTo = document.getElementById("timeTo");
    const messageCount = document.getElementById("messageCount");

    // Get unique senders
    const uniqueSenders = [...new Set(messages.map(msg => msg.sender))];
    uniqueSenders.forEach(sender => {
        const option = document.createElement("option");
        option.value = sender;
        option.textContent = sender;
        senderFilter.appendChild(option);
    });

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

        // Telegram JSON: "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD HH:MM:SS"
        match = text.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/);
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

        return null;
    }

    function applyFilters() {
    let filtered = messages.slice();

    // Filter by sender
    const sender = senderFilter.value;
    if (sender) {
        filtered = filtered.filter(msg => msg.sender === sender);
    }

    // Filter by media type
    const mediaType = mediaFilter.value;
    if (mediaType) {
        filtered = filtered.filter(msg => {
            if (!msg.media) return false;
            const ext = msg.media.split(".").pop().toLowerCase();
            if (mediaType === "image") return ["jpg","jpeg","png","gif","webp"].includes(ext);
            if (mediaType === "video") return ["mp4","mov","webm","3gp"].includes(ext);
            if (mediaType === "audio") return ["mp3","wav","m4a","aac","opus","ogg"].includes(ext);
            if (mediaType === "pdf") return ext === "pdf";
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

        resetAndRender(filtered);
    }

    searchInput.addEventListener("input", applyFilters);
    senderFilter.addEventListener("change", applyFilters);
    mediaFilter.addEventListener("change", applyFilters);
    timePreset.addEventListener("change", () => {
        timeRange.style.display = timePreset.value === "custom" ? "inline-block" : "none";
        applyFilters();
    });
    timeFrom.addEventListener("change", applyFilters);
    timeTo.addEventListener("change", applyFilters);


    function renderMedia(mediaFile) {
        if (!mediaFile) return "";
        const ext = mediaFile.split('.').pop().toLowerCase();

        if (["jpg","jpeg","png","gif","webp"].includes(ext)) {
            // clickable image preview
            return `
            <div class="media">
                <a href="media/${mediaFile}" target="_blank">
                    <img src="media/${mediaFile}" alt="${mediaFile}">
                </a>
            </div>`;
        } 
        else if (["mp4","mov","webm","3gp"].includes(ext)) {
            return `
            <div class="media">
                <video controls src="media/${mediaFile}" style="max-width:100%; border-radius:10px;"></video>
            </div>`;
        } 
        else if (["mp3","wav","m4a","aac","opus","ogg"].includes(ext)) {
            return `
            <div class="media">
                <audio controls src="media/${mediaFile}"></audio>
            </div>`;
        } 
        else if (ext === "pdf") {
            return `<div class="media"><a href="media/${mediaFile}" target="_blank">${mediaFile}</a></div>`;
        } 
        else {
            return `<div class="media"><a href="media/${mediaFile}" target="_blank">${mediaFile}</a></div>`;
        }
    }

    // ----------------------
    // Render a batch of messages
    // ----------------------
    function renderNextBatch() {
        if (currentIndex >= filteredMessages.length) return;

        const endIndex = Math.min(currentIndex + MESSAGES_PER_BATCH, filteredMessages.length);

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
            msgDiv.innerHTML = `
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
    resetAndRender(filteredMessages);

});

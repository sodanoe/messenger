const el = (id) => document.getElementById(id);
const v = (id) => el(id).value.trim();
const API_BASE = () => (location.protocol === 'file:' ? 'http://localhost:8000' : location.origin);

let token = null,
    me = null,
    isAdmin = false,
    ws = null;
let currentChat = null,
    contacts = [],
    chats = []; // все чаты юзера (DM + группы)
let heartbeatTimer = null,
    activeTab = 'dm',
    lastInvite = null;
let searchTimer = null,
    searchActive = false;
let pendingMediaId = null,
    pendingMediaUrl = null;

// ── Reply state ───────────────────────────────────────────
let replyTo = null;

// ── Reaction picker state ─────────────────────────────────
let pickerMsgId = null;

// ── Per-message data store (for action handlers) ──────────
const msgStore = {};

// ── Notifications ─────────────────────────────────────────
let notifGranted = false;
let titleBlinkTimer = null;
const PAGE_TITLE = document.title;

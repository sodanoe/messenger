import { create } from "zustand";

/**
 * @typedef {Object} CurrentChat
 * @property {'dm'|'group'} type
 * @property {number} id
 * @property {string} name
 * @property {boolean} [is_online]
 */

/**
 * @typedef {Object} AppStore
 * @property {string|null} token
 * @property {{id:number, username:string}|null} me
 * @property {boolean} isAdmin
 * @property {CurrentChat|null} currentChat
 * @property {Array} contacts
 * @property {Array} groups
 * @property {Array} messages
 * @property {'dm'|'groups'} activeTab
 * @property {string|null} lastInvite
 * @property {Object|null} replyTo
 * @property {Object} msgStore
 */

const useAppStore = create((set, get) => ({
  // ── Auth ──────────────────────────────────────────────
  token: localStorage.getItem("msng_token"),
  me: null,
  isAdmin: false,

  setToken: (token) => {
    localStorage.setItem("msng_token", token);
    set({ token });
  },

  setMe: (me) => set({ me }),
  setIsAdmin: (isAdmin) => set({ isAdmin }),

  logout: () => {
    localStorage.removeItem("msng_token");
    localStorage.removeItem("msng_chat");
    set({
      token: null,
      me: null,
      isAdmin: false,
      currentChat: null,
      contacts: [],
      groups: [],
      messages: [],
      lastInvite: null,
      replyTo: null,
      msgStore: {},
    });
  },

  // ── Chat ──────────────────────────────────────────────
  currentChat: (() => {
    try {
      return JSON.parse(localStorage.getItem("msng_chat"));
    } catch {
      return null;
    }
  })(),

  setCurrentChat: (chat) => {
    if (chat) localStorage.setItem("msng_chat", JSON.stringify(chat));
    else localStorage.removeItem("msng_chat");
    const prev = get().currentChat;
    const isSame = prev?.type === chat?.type && prev?.id === chat?.id;
    set({ currentChat: chat, ...(!isSame && { messages: [], msgStore: {} }) });
  },

  clearCurrentChat: () => {
    localStorage.removeItem("msng_chat");
    set({ currentChat: null, messages: [], msgStore: {} });
  },

  // ── Contacts ──────────────────────────────────────────
  contacts: [],
  setContacts: (contacts) => set({ contacts }),
  updateContactOnline: (userId, isOnline) =>
    set((state) => ({
      contacts: state.contacts.map((c) =>
        c.contact_user_id === userId ? { ...c, is_online: isOnline } : c,
      ),
    })),
  markContactRead: (userId) =>
    set((state) => ({
      contacts: state.contacts.map((c) =>
        c.contact_user_id === userId ? { ...c, has_unread: false } : c,
      ),
    })),
  markContactUnread: (userId) =>
    set((state) => ({
      contacts: state.contacts.map((c) =>
        c.contact_user_id === userId ? { ...c, has_unread: true } : c,
      ),
    })),
  updateContactLastMessage: (userId, content) =>
    set((state) => ({
      contacts: state.contacts.map((c) =>
        c.contact_user_id === userId ? { ...c, last_message: content } : c,
      ),
    })),

  // ── Groups ────────────────────────────────────────────
  groups: [],
  setGroups: (groups) => set({ groups }),

  // ── Messages ──────────────────────────────────────────
  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) =>
    set((state) => {
      if (msg.id && state.messages.some((m) => m.id === msg.id)) return state;
      return { messages: [...state.messages, msg] };
    }),
  removeMessage: (msgId) =>
    set((state) => ({
      messages: state.messages.filter((m) => m.id !== msgId),
    })),
  updateMessageReactions: (msgId, reactions) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === msgId ? { ...m, reactions } : m,
      ),
    })),

  // ── msgStore — данные для reply/actions ───────────────
  msgStore: {},
  addToMsgStore: (id, data) =>
    set((state) => ({ msgStore: { ...state.msgStore, [id]: data } })),

  // ── UI ────────────────────────────────────────────────
  activeTab: "dm",
  setActiveTab: (activeTab) => set({ activeTab }),

  lastInvite: null,
  setLastInvite: (lastInvite) => set({ lastInvite }),

  // ── Reply ─────────────────────────────────────────────
  replyTo: null,
  setReplyTo: (replyTo) => set({ replyTo }),
  clearReplyTo: () => set({ replyTo: null }),
}));

export default useAppStore;
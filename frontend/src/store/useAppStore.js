import { create } from 'zustand';

/**
 * @typedef {Object} CurrentChat
 * @property {'direct'|'group'} type
 * @property {number} id
 * @property {string} [name]
 * @property {boolean} [is_online]
 * @property {number} [other_user_id]
 */

/**
 * @typedef {Object} AppStore
 * @property {string|null} token
 * @property {{id:number, username:string}|null} me
 * @property {boolean} isAdmin
 * @property {CurrentChat|null} currentChat
 * @property {Array} chats
 * @property {Array} messages
 * @property {string} activeTab
 * @property {Object} msgStore
 */

const useAppStore = create((set, get) => ({
  // ── Auth ──────────────────────────────────────────────
  token: localStorage.getItem('msng_token'),
  me: null,
  isAdmin: false,

  setToken: (token) => {
    localStorage.setItem('msng_token', token);
    set({ token });
  },

  setMe: (me) => set({ me }),
  setIsAdmin: (isAdmin) => set({ isAdmin }),

  logout: () => {
    localStorage.removeItem('msng_token');
    localStorage.removeItem('msng_chat');
    set({
      token: null,
      me: null,
      isAdmin: false,
      currentChat: null,
      chats: [],
      messages: [],
      lastInvite: null,
      replyTo: null,
      msgStore: {},
    });
  },

  // ── Current Active Chat ───────────────────────────────
  currentChat: (() => {
    try {
      return JSON.parse(localStorage.getItem('msng_chat'));
    } catch {
      return null;
    }
  })(),

  setCurrentChat: (chat) => {
    if (chat) localStorage.setItem('msng_chat', JSON.stringify(chat));
    else localStorage.removeItem('msng_chat');
    const prev = get().currentChat;
    const isSame = prev?.type === chat?.type && prev?.id === chat?.id;
    set({ currentChat: chat, ...(!isSame && { messages: [], msgStore: {} }) });
  },

  clearCurrentChat: () => {
    localStorage.removeItem('msng_chat');
    set({ currentChat: null, messages: [], msgStore: {} });
  },

  // ── Unified Chats (Единая лента) ──────────────────────
  chats: [],
  setChats: (chats) => set({ chats }),

  updateChatOnline: (userId, isOnline) =>
    set((state) => ({
      chats: state.chats.map((c) =>
        c.other_user_id === userId ? { ...c, is_online: isOnline } : c,
      ),
    })),

  updateChatLastMessage: (
    chatId,
    content,
    updatedAt = new Date().toISOString(),
  ) =>
    set((state) => ({
      chats: state.chats
        .map((c) =>
          c.id === chatId
            ? { ...c, last_message: content, updated_at: updatedAt }
            : c,
        )
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
    })),

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

  // ── UI / Helpers ──────────────────────────────────────
  msgStore: {},
  addToMsgStore: (id, data) =>
    set((state) => ({ msgStore: { ...state.msgStore, [id]: data } })),

  activeTab: 'all',
  setActiveTab: (activeTab) => set({ activeTab }),

  lastInvite: null,
  setLastInvite: (lastInvite) => set({ lastInvite }),

  replyTo: null,
  setReplyTo: (replyTo) => set({ replyTo }),
  clearReplyTo: () => set({ replyTo: null }),
}));

export default useAppStore;

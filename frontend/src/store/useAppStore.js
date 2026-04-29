import { create } from 'zustand';

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
      contacts: [],
      messages: [],
      lastInvite: null,
      replyTo: null,
      msgStore: {},
      customEmojis: [],
      nextCursor: null,
      hasMore: false,
    });
  },

  // ── Current Active Chat ───────────────────────────────
  currentChat: null,

  setCurrentChat: (chat) => {
    if (chat) {
      localStorage.setItem('msng_chat', JSON.stringify(chat));
    } else {
      localStorage.removeItem('msng_chat');
    }
    const prev = get().currentChat;
    const isSame = prev?.type === chat?.type && prev?.id === chat?.id;
    set((state) => ({
      currentChat: chat,
      chats: state.chats.map((c) =>
        c.id === chat?.id ? { ...c, has_unread: false } : c
      ),
      ...(!isSame && { messages: [], msgStore: {}, nextCursor: null, hasMore: false }),
    }));
  },

  clearCurrentChat: () => {
    localStorage.removeItem('msng_chat');
    set({ currentChat: null, messages: [], msgStore: {}, nextCursor: null, hasMore: false });
  },

  // ── Chats ─────────────────────────────────────────────
  chats: [],
  setChats: (chats) => set({ chats }),

  setChatUnread: (chatId, value) =>
    set((state) => ({
      chats: state.chats.map((c) =>
        c.id === chatId ? { ...c, has_unread: value } : c
      ),
    })),

  updateChatOnline: (userId, isOnline) =>
    set((state) => ({
      chats: state.chats.map((c) =>
        c.other_user_id === userId ? { ...c, is_online: isOnline } : c
      ),
    })),

  updateChatLastMessage: (chatId, content, updatedAt = new Date().toISOString()) =>
    set((state) => ({
      chats: state.chats
        .map((c) =>
          c.id === chatId ? { ...c, last_message: content, updated_at: updatedAt } : c
        )
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
    })),

  // ── Contacts ──────────────────────────────────────────
  contacts: [],
  setContacts: (contacts) => set({ contacts }),

  // ── Messages ──────────────────────────────────────────
  messages: [],
  nextCursor: null,
  hasMore: false,

  setMessages: (messages, nextCursor = null) =>
    set({
      messages,
      nextCursor,
      hasMore: nextCursor !== null,
    }),

  prependMessages: (newMessages, nextCursor) =>
    set((state) => ({
      messages: [...newMessages, ...state.messages],
      nextCursor,
      hasMore: nextCursor !== null,
    })),

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
        m.id === msgId ? { ...m, reactions } : m
      ),
    })),

  // ── UI / Helpers ──────────────────────────────────────
  msgStore: {},
  addToMsgStore: (id, data) =>
    set((state) => ({
      msgStore: { ...state.msgStore, [id]: data },
    })),

  activeTab: 'all',
  setActiveTab: (activeTab) => set({ activeTab }),

  lastInvite: null,
  setLastInvite: (lastInvite) => set({ lastInvite }),

  replyTo: null,
  setReplyTo: (replyTo) => set({ replyTo }),
  clearReplyTo: () => set({ replyTo: null }),

  // ── Custom Emojis ─────────────────────────────────────
  customEmojis: [],
  setCustomEmojis: (customEmojis) => set({ customEmojis }),
}));

export default useAppStore;
import { create } from 'zustand';

/**
 * @typedef {Object} CurrentChat
 * @property {'direct'|'group'} type
 * @property {number} id
 * @property {string} [name]
 * @property {boolean} [is_online]
 * @property {number} [other_user_id]
 */

const useAppStore = create((set, get) => ({
  // ── Auth ──────────────────────────────────────────────
  token: localStorage.getItem('msng_token'),
  me: null,
  isAdmin: false,
  // token: localStorage.getItem('msng_token') || 'fake-token',
  // me: { id: 1, username: 'test' },
  // isAdmin: false,

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
    });
  },

  // ── Current Active Chat ───────────────────────────────
  currentChat: { type: 'direct', id: 1, name: 'test1', is_online: true },

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

  // ── Unified Chats ─────────────────────────────────────
  // chats: [
  //   {
  //     id: 1,
  //     type: 'direct',
  //     name: 'test1',
  //     other_user_id: 2,
  //     is_online: true,
  //     last_message: 'привет',
  //     updated_at: new Date().toISOString(),
  //   },
  //   {
  //     id: 2,
  //     type: 'direct',
  //     name: 'Алексей',
  //     other_user_id: 2,
  //     is_online: true,
  //     last_message: 'Привет! Как дела?',
  //     last_msg_media_id: null,
  //     has_unread: true,
  //     updated_at: new Date().toISOString(),
  //   },
  //   {
  //     id: 3,
  //     type: 'direct',
  //     name: 'Мария',
  //     other_user_id: 3,
  //     is_online: false,
  //     last_message: '',
  //     last_msg_media_id: 1,
  //     has_unread: false,
  //     updated_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
  //   },
  //   {
  //     id: 4,
  //     type: 'group',
  //     name: 'Работа',
  //     is_online: false,
  //     last_message: 'Завтра созвон в 10',
  //     last_msg_media_id: null,
  //     has_unread: true,
  //     updated_at: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
  //   },
  //   {
  //     id: 5,
  //     type: 'direct',
  //     name: 'Иван',
  //     other_user_id: 4,
  //     is_online: true,
  //     last_message: '',
  //     last_msg_media_id: null,
  //     has_unread: false,
  //     updated_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
  //   },
  //   {
  //     id: 6,
  //     type: 'direct',
  //     name: 'Длинное имя пользователя',
  //     other_user_id: 5,
  //     is_online: false,
  //     last_message:
  //       'Очень длинное сообщение чтобы проверить обрезание текста в интерфейсе',
  //     last_msg_media_id: null,
  //     has_unread: true,
  //     updated_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
  //   },
  // ],
  setChats: (chats) => set({ chats }),

  updateChatOnline: (userId, isOnline) =>
    set((state) => ({
      chats: (state.chats || []).map((c) =>
        c.other_user_id === userId ? { ...c, is_online: isOnline } : c,
      ),
    })),

  updateChatLastMessage: (
    chatId,
    content,
    updatedAt = new Date().toISOString(),
  ) =>
    set((state) => ({
      chats: (state.chats || [])
        .map((c) =>
          c.id === chatId
            ? { ...c, last_message: content, updated_at: updatedAt }
            : c,
        )
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)),
    })),

  // ── Contacts ──────────────────────────────────────────
  contacts: [],
  setContacts: (contacts) => set({ contacts }),

  // ── Messages ──────────────────────────────────────────
  messages: [
    {
      id: 1,
      sender_id: 1,
      content: 'Привет!',
      created_at: new Date().toISOString(),
      reactions: [{ emoji: '👍', user_id: 2 }],
      reply_to: null,
    },
    {
      id: 2,
      sender_id: 2,
      content: 'Как дела?',
      created_at: new Date().toISOString(),
      reactions: [],
      reply_to: null,
    },
  ],
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

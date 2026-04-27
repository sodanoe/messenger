import { useEffect, useRef } from 'react';
import { API_BASE } from '../config';
import { api } from '../services/api';
import useAppStore from '../store/useAppStore';
import { useNotifications } from './useNotifications';

export function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const heartbeatTimer = useRef(null);
  const reconnectDelay = useRef(3000);

  const { notifyUser } = useNotifications();
  const { token } = useAppStore();

  function wsClose() {
    clearInterval(heartbeatTimer.current);
    clearTimeout(reconnectTimer.current);
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }

  async function connectWS() {
    wsClose();

    let ticket;
    try {
      const data = await api('/auth/ws/ticket', 'POST');
      ticket = data.ticket;
    } catch {
      if (useAppStore.getState().token) {
        reconnectTimer.current = setTimeout(connectWS, reconnectDelay.current);
        reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 30000);
      }
      return;
    }

    const wsBase = API_BASE().replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/ws?ticket=${ticket}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = 3000;
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 20000);
    };

    ws.onmessage = ({ data }) => {
      let msg;
      try {
        msg = JSON.parse(data);
      } catch {
        return;
      }

      const store = useAppStore.getState();
      const chat = store.currentChat;
      const myId = store.me?.id;

      // ── Новое сообщение (DM или группа) ──────────────────
      if (msg.type === 'new_message') {
        const chatId = msg.chat_id;
        const senderId = msg.sender_id;
        const chatType = 'direct';

        if (chat?.type === chatType && chat?.id === chatId) {
          if (senderId !== myId) {
            store.addMessage({
              id: msg.id,
              content: msg.content || '',
              content_encrypted: null,
              sender_id: senderId,
              sender_username: msg.sender_username || null,
              created_at: msg.created_at,
              media_url: msg.media_url || null,
              reply_to: msg.reply_to || null,
              reactions: [],
            });
          }
        } else {
          if (senderId !== myId) {
            const targetChat = store.chats.find(c => c.id === chatId);
            notifyUser(targetChat?.name || 'Новое сообщение', msg.content || '');
          }
        }
        store.updateChatLastMessage(chatId, msg.content || 'Файл', msg.created_at);
      }

      // ── Новое сообщение в группе ──────────────────────────
      if (msg.type === 'new_group_message') {
        const chatId = msg.chat_id;
        const senderId = msg.sender_id;
        const chatType = 'group';

        if (chat?.type === chatType && chat?.id === chatId) {
          if (senderId !== myId) {
            store.addMessage({
              id: msg.id,
              content: msg.content || '',
              content_encrypted: null,
              sender_id: senderId,
              sender_username: msg.sender_username || null,
              created_at: msg.created_at,
              media_url: msg.media_url || null,
              reply_to: msg.reply_to || null,
              reactions: [],
            });
          }
        } else {
          if (senderId !== myId) {
            const targetChat = store.chats.find(c => c.id === chatId);
            notifyUser(`# ${targetChat?.name || 'Группа'}`, msg.content || '');
          }
        }
        store.updateChatLastMessage(chatId, msg.content || 'Файл', msg.created_at);
      }

      // ── Реакции ──────────────────────────────────────────
      if (msg.type === 'reaction_update' || msg.type === 'group_reaction_update') {
        store.updateMessageReactions(msg.message_id, msg.reactions);
      }

      // ── Удаление сообщения ───────────────────────────────
      if (msg.type === 'message_deleted' || msg.type === 'group_message_deleted') {
        store.removeMessage(msg.message_id);
      }

      // ── Удаление чата ────────────────────────────────────
      if (msg.type === 'chat_deleted') {
        store.setChats(store.chats.filter(c => c.id !== msg.chat_id));
        if (chat?.id === msg.chat_id) {
          store.clearCurrentChat();
        }
      }

      // ── Онлайн статус ────────────────────────────────────
      if (msg.type === 'user_online') store.updateChatOnline(msg.user_id, true);
      if (msg.type === 'user_offline') store.updateChatOnline(msg.user_id, false);
    };

    ws.onerror = () => {};

    ws.onclose = () => {
      clearInterval(heartbeatTimer.current);
      if (useAppStore.getState().token) {
        reconnectTimer.current = setTimeout(connectWS, reconnectDelay.current);
        reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 30000);
      }
    };
  }

  useEffect(() => {
    if (token) connectWS();
    return () => wsClose();
  }, [token]);

  return { wsRef };
}
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

      // ── Сообщения (DM и Группы) ──────────────────────────
      if (msg.type === 'new_message' || msg.type === 'new_group_message') {
        const isGroup = msg.type === 'new_group_message';
        const chatId = isGroup ? msg.group_id : msg.from;
        const chatType = isGroup ? 'group' : 'direct';

        // 1. Если чат открыт — добавляем сообщение в окно
        if (chat?.type === chatType && chat?.id === chatId) {
          if (msg.from !== myId) {
            store.addMessage({
              id: msg.id,
              content: msg.content || msg.content_encrypted || '',
              content_encrypted: msg.content_encrypted || null,
              sender_id: msg.from,
              sender_username: msg.sender_username || null,
              created_at: msg.created_at,
              media_url: msg.media_url || null,
              reply_to: msg.reply_to || null,
              reactions: [],
            });
            if (!isGroup)
              api(`/messages/${msg.from}/read`, 'POST').catch(() => {});
          }
        } else {
          // 2. Если чат закрыт — шлем пуш
          const targetChat = store.chats.find(
            (c) => c.id === chatId && c.type === chatType,
          );
          const senderName = isGroup
            ? `# ${targetChat?.name || 'Группа'}`
            : targetChat?.name || `#${msg.from}`;

          if (msg.from !== myId) {
            notifyUser(senderName, msg.content || 'Новое сообщение');
          }
        }

        // 3. Обновляем список чатов (текст и позицию в списке)
        store.updateChatLastMessage(
          chatId,
          msg.content || 'Файл',
          msg.created_at,
        );
      }

      // ── Реакции ────────────────────────────────────
      if (
        msg.type === 'reaction_update' ||
        msg.type === 'group_reaction_update'
      ) {
        store.updateMessageReactions(msg.message_id, msg.reactions);
      }

      // ── Удаление ───────────────────────────────────────
      if (
        msg.type === 'message_deleted' ||
        msg.type === 'group_message_deleted'
      ) {
        store.removeMessage(msg.message_id);
      }

      // ── Статус онлайн ──────────────────────────────────
      if (msg.type === 'user_online') store.updateChatOnline(msg.user_id, true);
      if (msg.type === 'user_offline')
        store.updateChatOnline(msg.user_id, false);
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

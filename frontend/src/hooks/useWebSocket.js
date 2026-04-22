import { useEffect, useRef } from "react";
import { API_BASE } from "../config";
import { api } from "../services/api";
import useAppStore from "../store/useAppStore";
import { useNotifications } from "./useNotifications";

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
      const data = await api("/auth/ws/ticket", "POST");
      ticket = data.ticket;
    } catch {
      if (useAppStore.getState().token) {
        reconnectTimer.current = setTimeout(connectWS, reconnectDelay.current);
        reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 30000);
      }
      return;
    }

    const wsBase = API_BASE().replace(/^http/, "ws");
    const ws = new WebSocket(`${wsBase}/ws?ticket=${ticket}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = 3000;
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
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

      // ── DM ──────────────────────────────────────────
      if (msg.type === "new_message") {
        // Своё сообщение уже добавлено из ответа API
        if (msg.from === myId) return;

        if (chat?.type === "dm" && chat?.id === msg.from) {
          store.addMessage({
            id: msg.id,
            content: msg.content || msg.content_encrypted || "",
            content_encrypted: msg.content_encrypted || null,
            sender_id: msg.from,
            created_at: msg.created_at,
            media_url: msg.media_url || null,
            reply_to: msg.reply_to || null,
            reactions: [],
          });
          api(`/messages/${msg.from}/read`, "POST").catch(() => {});
        } else {
          store.markContactUnread(msg.from);
          store.updateContactLastMessage(msg.from, msg.content || "");
          const sender = store.contacts.find(
            (c) => c.contact_user_id === msg.from,
          );
          notifyUser(sender?.username || `#${msg.from}`, msg.content || "");
        }
      }

      // ── Group ────────────────────────────────────────
      if (msg.type === "new_group_message") {
        // Своё сообщение уже добавлено из ответа API
        if (msg.from === myId) return;

        if (chat?.type === "group" && chat?.id === msg.group_id) {
          store.addMessage({
            id: msg.id,
            content: msg.content || msg.content_encrypted || "",
            content_encrypted: msg.content_encrypted || null,
            sender_id: msg.from,
            sender_username: msg.sender_username || null,
            created_at: msg.created_at,
            media_url: msg.media_url || null,
            reply_to: msg.reply_to || null,
            reactions: [],
          });
        } else {
          const g = store.groups.find((g) => g.id === msg.group_id);
          notifyUser(`# ${g?.name || msg.group_id}`, msg.content || "");
        }
      }

      // ── Reactions ────────────────────────────────────
      if (msg.type === "reaction_update") {
        store.updateMessageReactions(msg.message_id, msg.reactions);
      }
      if (
        msg.type === "group_reaction_update" &&
        chat?.type === "group" &&
        chat?.id === msg.group_id
      ) {
        store.updateMessageReactions(msg.message_id, msg.reactions);
      }

      // ── Delete ───────────────────────────────────────
      if (msg.type === "message_deleted") {
        store.removeMessage(msg.message_id);
      }
      if (
        msg.type === "group_message_deleted" &&
        chat?.type === "group" &&
        chat?.id === msg.group_id
      ) {
        store.removeMessage(msg.message_id);
      }

      // ── Online status ────────────────────────────────
      if (msg.type === "user_online")
        store.updateContactOnline(msg.user_id, true);
      if (msg.type === "user_offline")
        store.updateContactOnline(msg.user_id, false);
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

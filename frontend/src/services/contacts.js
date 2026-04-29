import { api } from './api';

export async function searchUsers(q) {
  return api(`/users/search?q=${encodeURIComponent(q)}`);
}

export async function getContacts() {
  const data = await api('/chats/');
  const chats = data.chats || [];
  return chats
    .filter((c) => c.type === 'direct')
    .map((c) => ({
      contact_user_id: c.other_user_id,
      username: c.other_username,
      chat_id: c.id,
      is_online: false,
      has_unread: false,
      last_message: null,
    }));
}

export async function addContact(userId) {
  return api('/chats/direct', 'POST', { user_id: userId });
}

export async function getMessages(chatId, cursor = null) {
  const url = cursor
    ? `/chats/${chatId}/messages?cursor=${cursor}`
    : `/chats/${chatId}/messages`;
  return api(url);
}

export async function markRead(chatId) {
  try {
    return await api(`/messages/${chatId}/read`, 'POST');
  } catch {
    return null;
  }
}

export async function sendDM(chatId, content, mediaId = null, replyToId = null) {
  return api(`/chats/${chatId}/messages`, 'POST', {
    content: content || '',
    media_id: mediaId,
    reply_to_id: replyToId,
  });
}

export async function deleteDM(chatId, msgId) {
  return api(`/chats/${chatId}/messages/${msgId}`, 'DELETE');
}

export async function reactDM(chatId, msgId, emoji) {
  return api(`/chats/${chatId}/messages/${msgId}/reactions`, 'POST', { emoji });
}
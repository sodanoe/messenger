import { api } from './api';

// Поиск пользователей
export async function searchUsers(q) {
  return api(`/users/search?q=${encodeURIComponent(q)}`);
}

// Получить список DM-контактов через /chats/
export async function getContacts() {
  const data = await api('/chats/');
  const chats = data.chats || [];
  return chats
    .filter((c) => c.type === 'direct')
    .map((c) => ({
      contact_user_id: c.other_user_id,
      username: c.other_username, // было c.name — неверно
      chat_id: c.id,
      is_online: false,
      has_unread: false,
      last_message: null,
    }));
}

// Создать DM
export async function addContact(userId) {
  return api('/chats/direct', 'POST', { user_id: userId });
}

// Получить сообщения DM
export async function getMessages(chatId) {
  return api(`/chats/${chatId}/messages`);
}

// Пометить прочитанным (если эндпоинт есть на бэке, иначе no-op)
export async function markRead(chatId) {
  try {
    return await api(`/messages/${chatId}/read`, 'POST');
  } catch {
    return null;
  }
}

// Отправить DM
export async function sendDM(
  chatId,
  content,
  mediaId = null,
  replyToId = null,
) {
  return api(`/chats/${chatId}/messages`, 'POST', {
    content: content || '',
    media_id: mediaId,
    reply_to_id: replyToId,
  });
}

// Удалить сообщение DM
export async function deleteDM(chatId, msgId) {
  return api(`/chats/${chatId}/messages/${msgId}`, 'DELETE');
}

// Реакция на DM сообщение
export async function reactDM(chatId, msgId, emoji) {
  return api(`/chats/${chatId}/messages/${msgId}/reactions`, 'POST', { emoji });
}

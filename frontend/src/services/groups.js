import { api } from './api'

// Получить список групп через /chats/
export async function getGroups() {
  const data = await api('/chats/')
  const chats = data.chats || []
  return chats
    .filter(c => c.type === 'group')
    .map(c => ({ id: c.id, name: c.name, created_by: null }))
}

// Создать группу
export async function createGroup(name, memberIds = []) {
  return api('/chats/group', 'POST', { name, member_ids: memberIds })
}

// Удалить группу (если эндпоинт есть)
export async function deleteGroup(groupId) {
  return api(`/groups/${groupId}`, 'DELETE')
}

// Получить сообщения группы
export async function getGroupMessages(groupId) {
  return api(`/chats/${groupId}/messages`)
}

// Отправить сообщение в группу
export async function sendGroupMessage(groupId, content, mediaId = null, replyToId = null) {
  return api(`/chats/${groupId}/messages`, 'POST', {
    content: content || '',
    media_id: mediaId,
    reply_to_id: replyToId,
  })
}

// Удалить сообщение группы
export async function deleteGroupMessage(groupId, msgId) {
  return api(`/chats/${groupId}/messages/${msgId}`, 'DELETE')
}

// Участники группы (если эндпоинт есть)
export async function getGroupMembers(groupId) {
  return api(`/groups/${groupId}/members`)
}

// Добавить участника
export async function inviteMember(groupId, userId) {
  return api(`/chats/${groupId}/members`, 'POST', { user_id: userId })
}

// Удалить участника
export async function removeMember(groupId, userId) {
  return api(`/chats/${groupId}/members/${userId}`, 'DELETE')
}

// Покинуть группу
export async function leaveGroup(groupId, myUserId) {
  return api(`/chats/${groupId}/members/${myUserId}`, 'DELETE')
}

// Реакция на сообщение группы
export async function reactGroup(groupId, msgId, emoji) {
  return api(`/chats/${groupId}/messages/${msgId}/reactions`, 'POST', { emoji })
}

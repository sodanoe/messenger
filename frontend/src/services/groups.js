import { api } from './api';

export async function getGroups() {
  const data = await api('/chats/');
  const chats = data.chats || [];
  return chats
    .filter((c) => c.type === 'group')
    .map((c) => ({ id: c.id, name: c.name, created_by: null }));
}

export async function createGroup(name, memberIds = []) {
  return api('/chats/group', 'POST', { name, member_ids: memberIds });
}

export async function deleteGroup(groupId) {
  return api(`/chats/${groupId}`, 'DELETE');
}

export async function getGroupMessages(groupId, cursor = null) {
  const url = cursor
    ? `/chats/${groupId}/messages?cursor=${cursor}`
    : `/chats/${groupId}/messages`;
  return api(url);
}

export async function sendGroupMessage(groupId, content, mediaId = null, replyToId = null) {
  return api(`/chats/${groupId}/messages`, 'POST', {
    content: content || '',
    media_id: mediaId,
    reply_to_id: replyToId,
  });
}

export async function deleteGroupMessage(groupId, msgId) {
  return api(`/chats/${groupId}/messages/${msgId}`, 'DELETE');
}

export async function getGroupMembers(groupId) {
  return api(`/chats/${groupId}/members`);
}

export async function inviteMember(groupId, userId) {
  return api(`/chats/${groupId}/members`, 'POST', { user_id: userId });
}

export async function removeMember(groupId, userId) {
  return api(`/chats/${groupId}/members/${userId}`, 'DELETE');
}

export async function leaveGroup(groupId, myUserId) {
  return api(`/chats/${groupId}/members/${myUserId}`, 'DELETE');
}

export async function reactGroup(groupId, msgId, emoji) {
  return api(`/chats/${groupId}/messages/${msgId}/reactions`, 'POST', { emoji });
}
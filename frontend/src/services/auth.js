import { api } from "./api";

export async function login(username, password) {
  return api("/auth/login", "POST", { username, password });
}

export async function register(username, password, invite_code) {
  return api("/auth/register", "POST", { username, password, invite_code });
}

export async function fetchMe() {
  return api("/users/me");
}

export async function checkAdmin() {
  try {
    await api("/admin/media-settings");
    return true;
  } catch {
    return false;
  }
}

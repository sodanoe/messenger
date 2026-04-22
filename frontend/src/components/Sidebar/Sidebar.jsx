import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import useAppStore from "../../store/useAppStore";
import { getContacts } from "../../services/contacts";
import { getGroups } from "../../services/groups";
import { api } from "../../services/api";
import SearchBar from "./SearchBar/SearchBar";
import ChatList from "./ChatList/ChatList";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  const navigate = useNavigate();
  const {
    me,
    isAdmin,
    activeTab,
    setActiveTab,
    contacts,
    setContacts,
    groups,
    setGroups,
    logout,
    lastInvite,
    setLastInvite,
  } = useAppStore();

  const [inviteHint, setInviteHint] = useState(
    "Создай код и отправь новому пользователю",
  );

  useEffect(() => {
    getContacts()
      .then(setContacts)
      .catch(() => {});
    getGroups()
      .then(setGroups)
      .catch(() => {});
  }, []);

  function doLogout() {
    logout();
    navigate("/login");
  }

  async function genInvite() {
    try {
      const r = await api("/auth/invite", "POST");
      setLastInvite(r.code);
      setInviteHint("Нажми на код чтобы скопировать");
    } catch {
      // silent
    }
  }

  function copyInvite() {
    if (!lastInvite) return;
    navigator.clipboard
      .writeText(lastInvite)
      .then(() => setInviteHint("✓ Скопировано"))
      .catch(() => prompt("Скопируй код:", lastInvite));
  }

  return (
    <aside className={`${styles.sidebar} sidebar`}>
      <div className={styles.header}>
        <div className={styles.logo}>// msg</div>
        <div className={styles.meBadge}>{me?.username}</div>
        {isAdmin && <span className={styles.adminBadge}>ADMIN</span>}
        <button className={styles.logoutBtn} onClick={doLogout} title="Выйти">
          ⏏
        </button>
      </div>

      <SearchBar />

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "dm" ? styles.active : ""}`}
          onClick={() => setActiveTab("dm")}
        >
          DMs
        </button>
        <button
          className={`${styles.tab} ${activeTab === "groups" ? styles.active : ""}`}
          onClick={() => setActiveTab("groups")}
        >
          Groups
        </button>
      </div>

      <ChatList />

      {isAdmin && (
        <div className={styles.adminPanel}>
          <div className={styles.adminTitle}>⚡ Инвайты</div>
          <div className={styles.inviteRow}>
            <div
              className={`${styles.inviteCode} ${!lastInvite ? styles.empty : ""}`}
              onClick={copyInvite}
              title="Нажми чтобы скопировать"
            >
              {lastInvite || "нет кода"}
            </div>
            <button className={styles.smallBtn} onClick={genInvite}>
              + Создать
            </button>
          </div>
          <div className={styles.inviteHint}>{inviteHint}</div>
        </div>
      )}
    </aside>
  );
}

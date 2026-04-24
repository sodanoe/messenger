import { useWebSocket } from '../../hooks/useWebSocket';
import Sidebar from '../../components/Sidebar/Sidebar';
import ChatWindow from '../../components/ChatWindow/ChatWindow';
import useAppStore from '../../store/useAppStore';
import styles from './ChatPage.module.css';

export default function ChatPage() {
  useWebSocket();

  const currentChat = useAppStore((s) => s.currentChat);

  return (
    <div className={`${styles.app} ${currentChat ? styles.chatOpen : ''}`}>
      <Sidebar />
      <ChatWindow />
    </div>
  );
}

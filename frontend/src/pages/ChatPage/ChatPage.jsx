import { useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import Sidebar from '../../components/Sidebar/Sidebar';
import ChatWindow from '../../components/ChatWindow/ChatWindow';
import ContactPanel from '../../components/RightPanel/ContactPanel/ContactPanel';
import useAppStore from '../../store/useAppStore';
import styles from './ChatPage.module.css';

export default function ChatPage() {
  useWebSocket();

  const currentChat = useAppStore((s) => s.currentChat);
  const [showContactPanel, setShowContactPanel] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <div className={`${styles.app} ${currentChat ? styles.chatOpen : ''}`}>
      <Sidebar />
      <ChatWindow
        showContactPanel={showContactPanel}
        setShowContactPanel={setShowContactPanel}
        searchOpen={searchOpen}
        setSearchOpen={setSearchOpen}
      />
      {showContactPanel && currentChat?.type === 'direct' && (
        <ContactPanel
          onClose={() => setShowContactPanel(false)}
          onOpenSearch={() => {
            setShowContactPanel(false);
            setSearchOpen(true);
          }}
        />
      )}
    </div>
  );
}
import { Toaster } from "react-hot-toast";
import { useEffect } from "react";
import LoginPage from "./pages/LoginPage/LoginPage";
import ChatPage from "./pages/ChatPage/ChatPage";
import useAppStore from "./store/useAppStore";
import { fetchMe } from "./services/auth";

export default function App() {
  const { token, setMe, logout } = useAppStore();

  useEffect(() => {
    if (!token) return;
    fetchMe()
      .then((me) => setMe(me))
      .catch(() => logout());
  }, [token]);

  return (
    <>
      <Toaster position="bottom-center" />
      {token ? <ChatPage /> : <LoginPage />}
    </>
  );
}
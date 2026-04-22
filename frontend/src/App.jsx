import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useEffect } from "react";
import LoginPage from "./pages/LoginPage/LoginPage";
import ChatPage from "./pages/ChatPage/ChatPage";
import GroupsPage from "./pages/GroupsPage/GroupsPage";
import ContactsPage from "./pages/ContactsPage/ContactsPage";
import useAppStore from "./store/useAppStore";
import { fetchMe } from "./services/auth";

function PrivateRoute({ children }) {
  const token = useAppStore((s) => s.token);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { token, setMe, logout } = useAppStore();

  useEffect(() => {
    if (!token) return;
    fetchMe()
      .then((me) => setMe(me))
      .catch(() => logout());
  }, [token]);

  return (
    <BrowserRouter>
      <Toaster position="bottom-center" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/chat"
          element={
            <PrivateRoute>
              <ChatPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/groups"
          element={
            <PrivateRoute>
              <GroupsPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/contacts"
          element={
            <PrivateRoute>
              <ContactsPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

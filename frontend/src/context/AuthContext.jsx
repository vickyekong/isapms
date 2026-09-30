import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("isapms_user");
    return stored ? JSON.parse(stored) : null;
  });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("isapms_access");
    if (!token) {
      setReady(true);
      return;
    }
    api
      .get("/auth/me/")
      .then((response) => {
        setUser(response.data);
        localStorage.setItem("isapms_user", JSON.stringify(response.data));
      })
      .catch(() => {
        localStorage.removeItem("isapms_access");
        localStorage.removeItem("isapms_refresh");
        localStorage.removeItem("isapms_user");
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      async login(identifier, password) {
        const response = await api.post("/auth/login/", { identifier, password });
        localStorage.setItem("isapms_access", response.data.access);
        localStorage.setItem("isapms_refresh", response.data.refresh);
        localStorage.setItem("isapms_user", JSON.stringify(response.data.user));
        setUser(response.data.user);
        return response.data.user;
      },
      async logout() {
        const refresh = localStorage.getItem("isapms_refresh");
        try {
          if (refresh) await api.post("/auth/logout/", { refresh });
        } catch {
          /* The local session is cleared even if the token is already expired. */
        }
        localStorage.removeItem("isapms_access");
        localStorage.removeItem("isapms_refresh");
        localStorage.removeItem("isapms_user");
        setUser(null);
      },
    }),
    [user, ready]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

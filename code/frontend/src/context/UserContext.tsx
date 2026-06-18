import { createContext, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type UserMe } from "../api/client";

type UserContextValue = {
  me: UserMe | null;
  loading: boolean;
  setMe: (me: UserMe | null) => void;
};

const UserContext = createContext<UserContextValue>({
  me: null,
  loading: true,
  setMe: () => {},
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [me, setMe] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<UserMe>("/api/v1/auth/me")
      .then(setMe)
      .catch(() => {
        setMe(null);
        navigate("/login", { replace: true });
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <UserContext.Provider value={{ me, loading, setMe }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

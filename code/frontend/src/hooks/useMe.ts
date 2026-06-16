import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type UserMe } from "../api/client";

export function useMe() {
  const navigate = useNavigate();
  const [me, setMe] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<UserMe>("/api/v1/auth/me")
      .then(setMe)
      .catch(() => navigate("/login", { replace: true }))
      .finally(() => setLoading(false));
  }, [navigate]);

  return { me, loading };
}

import { useUser } from "../context/UserContext";

/** 向后兼容各页面已有的 useMe() 调用 */
export function useMe() {
  const { me, loading } = useUser();
  return { me, loading };
}

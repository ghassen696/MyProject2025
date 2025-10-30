import { Navigate } from "react-router";
import { JSX } from "react/jsx-runtime";

interface ProtectedRouteProps {
  children: JSX.Element;
  allowedRoles: string[];
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const token = localStorage.getItem("token") || sessionStorage.getItem("token");
  const role = localStorage.getItem("role") || sessionStorage.getItem("role");

  if (!token) {
    return <Navigate to="/signin" replace />;
  }

  if (!allowedRoles.includes(role || "")) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}

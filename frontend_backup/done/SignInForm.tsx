import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Checkbox from "../form/input/Checkbox";

export default function SignInForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // ✅ Store token based on "Keep me logged in"
      if (isChecked) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("email", data.email);
        localStorage.setItem("username", data.username);
        localStorage.setItem("employee_id", data.employee_id);
      } else {
        sessionStorage.setItem("token", data.access_token);
        sessionStorage.setItem("role", data.role);
        sessionStorage.setItem("email", data.email);
        sessionStorage.setItem("username", data.username);
        sessionStorage.setItem("employee_id", data.employee_id);
      }

      // Navigate to dashboard
      navigate("/dashboard");
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          {/* Header */}
          <div className="mb-6 text-center sm:text-left">
            <h1 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
              Welcome Back
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Enter your email and password to access your account.
            </p>
          </div>

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Email */}
            <div>
              <Label>
                Email <span className="text-red-600">*</span>
              </Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 focus:border-red-600 focus:ring-2 focus:ring-red-500/40 transition"
                required
              />
            </div>

            {/* Password */}
            <div>
              <Label>
                Password <span className="text-red-600">*</span>
              </Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-700 focus:border-red-600 focus:ring-2 focus:ring-red-500/40 transition pr-10"
                  required
                />
                <span
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                >
                  {showPassword ? (
                    <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                  ) : (
                    <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                  )}
                </span>
              </div>
            </div>

            {/* Options */}
            {/* Error Message */}
            {error && (
              <p className="text-sm text-red-600 font-medium">{error}</p>
            )}

            {/* Submit */}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full px-6 py-3 text-sm font-semibold tracking-wide text-white rounded-lg bg-red-600 shadow-md hover:bg-red-700 hover:shadow-lg transition-all disabled:opacity-50"
              >
                {loading ? "Signing In..." : "Sign In"}
              </button>
            </div>
          </form>

      
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { useSearchParams, Link, useNavigate } from "react-router";
import { EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import axios from "axios";

export default function SignUpForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [searchParams] = useSearchParams();
  const token = searchParams.get("token"); // token from email link
  const emailFromUrl = searchParams.get("email"); // optional, from link
  const empIdFromUrl = searchParams.get("employee_id"); // optional, from link
  const navigate = useNavigate();

  useEffect(() => {
    if (emailFromUrl) setEmail(emailFromUrl);
    if (empIdFromUrl) setEmployeeId(empIdFromUrl);
  }, [emailFromUrl, empIdFromUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!token || !employeeId) {
      setError("Invalid or missing token or employee ID");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post("http://localhost:8000/api/set-password", {
        token,
        email,
        employee_id: employeeId,
        password,
        confirm_password: confirmPassword,
      });

      setSuccess(res.data.message);
      setTimeout(() => navigate("/"), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Something went wrong");
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
              Set Your Huawei Account Password
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Use the link sent to your email to set your password.
            </p>
          </div>

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Email */}
            <div>
              <Label>Email</Label>
              <Input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 focus:border-red-600 focus:ring-2 focus:ring-red-500/40 transition"
                required
              />
            </div>

            {/* Employee ID */}
            <div>
              <Label>Employee ID</Label>
              <Input
                type="text"
                placeholder="Enter your employee ID"
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 focus:border-red-600 focus:ring-2 focus:ring-red-500/40 transition"
                required
              />
            </div>

            {/* Password */}
            <div>
              <Label>Password</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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

            {/* Confirm Password */}
            <div>
              <Label>Confirm Password</Label>
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 focus:border-red-600 focus:ring-2 focus:ring-red-500/40 transition"
                required
              />
            </div>

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                className="flex items-center justify-center w-full px-6 py-3 text-sm font-semibold tracking-wide text-white rounded-lg bg-red-600 shadow-md hover:bg-red-700 hover:shadow-lg transition-all"
                disabled={loading}
              >
                {loading ? "Setting password..." : "Set Password"}
              </button>
            </div>

            {error && <p className="text-red-600 text-sm">{error}</p>}
            {success && <p className="text-green-600 text-sm">{success}</p>}
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-700 dark:text-gray-400">
              Already have an account?{" "}
              <Link
                to="/"
                className="font-medium text-red-600 hover:text-red-700"
              >
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

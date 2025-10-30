import React from "react";
import ThemeTogglerTwo from "../../components/common/ThemeTogglerTwo";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex items-center justify-center w-full h-screen bg-gradient-to-br from-red-600 via-red-700 to-gray-900 dark:from-gray-900 dark:via-gray-800 dark:to-black">
      {/* Content container */}
      <div className="flex w-full h-full max-w-6xl overflow-hidden rounded-2xl shadow-2xl lg:h-5/6">
        {/* Left side - Huawei brand section */}
        <div className="hidden lg:flex flex-col justify-center items-center w-1/2 bg-gradient-to-b from-red-700 to-red-900 text-white p-10">
          <img
            src="/ha1.svg"
            alt="Huawei Logo"
            className="w-40 mb-5"
          />
          <h1 className="text-4xl font-bold tracking-wide">Welcome to Huawei</h1>
          <p className="mt-4 text-lg text-red-100 text-center max-w-md">
            Empowering your productivity with secure and intelligent solutions.
          </p>
        </div>

        {/* Right side - Auth form */}
        <div className="flex flex-col items-center justify-center w-full p-8 bg-white dark:bg-gray-900 lg:w-1/2">
            {/* Glass effect wrapper for form */}
          <div className="rounded-2xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-md p-6 shadow-lg">
            {children}
          </div>
        </div>
      </div>

      {/* Theme toggler */}
      <div className="fixed z-50 bottom-6 right-6">
        <ThemeTogglerTwo />
      </div>
    </div>
  );
}

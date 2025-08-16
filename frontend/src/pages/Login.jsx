import { useContext, useState } from "react";
import { AuthContext } from "../context/AuthContext";
import { Form, Button, Container, Row, Col, Alert, Spinner } from "react-bootstrap";
import VerifyModal from "../components/VerificationModal";
import { Film, Eye, EyeOff, User, Lock, Loader2 } from 'lucide-react';
import Image from '../assets/himalayanhutwhite.png'

const LoginPage = () => {
  const authContext = useContext(AuthContext);

  if (!authContext) {
    throw new Error("AuthContext must be used within an AuthContextProvider");
  }
  const { loginInfo, updateLoginInfo, loginUser, LoginError, isLoginLoading} = authContext;
  const [showPassword, setShowPassword] = useState(false);


  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-purple-900 flex items-center justify-center p-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-purple-700/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-white/5 rounded-full blur-3xl"></div>
      </div>

      {/* Your VerifyModal component would go here */}
      <VerifyModal type={"login"}/>

      {/* Main Container - matching your Row/Col structure */}
      <div className="relative z-10 w-full max-w-md">
        {/* Glassmorphism Card */}
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
          {/* Header - keeping your exact text */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-700 rounded-2xl mb-4 shadow-lg shadow-purple-500/25">
              <img src={Image} alt="Himalayan Hut White" />
            </div>
            
            <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">
              Himalayan Hut
            </h1>
            <h3 className="text-xl font-semibold text-purple-300 mb-4">
              Login
            </h3>
          </div>

          {/* Form - using your exact onSubmit */}
          <div className="space-y-6">
            {/* Username Field - your exact controlId and logic */}
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-gray-300 flex items-center gap-2">
                <User className="w-4 h-4" />
                Username
              </label>
              <div className="relative">
                <input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={loginInfo.username}
                  onChange={(e) => updateLoginInfo({ ...loginInfo, username: e.target.value })}
                  required
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200 backdrop-blur-sm hover:bg-white/10"
                />
              </div>
            </div>

            {/* Password Field - your exact controlId and logic */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-gray-300 flex items-center gap-2">
                <Lock className="w-4 h-4" />
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={loginInfo.password}
                  onChange={(e) => updateLoginInfo({ ...loginInfo, password: e.target.value })}
                  required
                  className="w-full px-4 py-3 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200 backdrop-blur-sm hover:bg-white/10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors duration-200"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Login Button - your exact variant, type, disabled logic */}
            <button
              type="submit"
              onClick={loginUser}
              disabled={isLoginLoading}
              className="w-full bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 transform hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-black disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg shadow-purple-500/25"
            >
              {isLoginLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Signing in...</span>
                </div>
              ) : (
                "Sign in"
              )}
            </button>
          </div>

          {/* Register Link - your exact text and href */}
          <p className="text-center mt-6 text-gray-400">
            Not a member?{" "}
            <a 
              href="/register" 
              className="text-purple-400 hover:text-purple-300 font-medium transition-colors duration-200 hover:underline"
            >
              Register Here
            </a>
          </p>

          {/* Error Alert - your exact LoginError variable and structure */}
          {LoginError && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl backdrop-blur-sm">
              <p className="text-red-400 text-sm text-center font-medium">{LoginError}</p>
            </div>
          )}
        </div>

        {/* Bottom Accent */}
        {/* <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-2 text-xs text-gray-500">
            <div className="w-8 h-px bg-gradient-to-r from-transparent to-purple-500"></div>
            <span>Secure Login</span>
            <div className="w-8 h-px bg-gradient-to-l from-transparent to-purple-500"></div>
          </div>
        </div> */}
      </div>
    </div>
  );
};

export default LoginPage;

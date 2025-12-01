"use client"

import { useState } from "react"
import { X } from "lucide-react"
import { AuthAPI, User } from "@/lib/api"

interface AuthModalProps {
  open: boolean
  onClose: () => void
  onLoginSuccess: (user: User) => void
}

export function AuthModal({ open, onClose, onLoginSuccess }: AuthModalProps) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [username, setUsername] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (!open) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      if (isLogin) {
        const result = await AuthAPI.login({ email, password })
        localStorage.setItem("user", JSON.stringify(result.user))
        localStorage.setItem("user_id", result.user.id)
        onLoginSuccess(result.user)
        onClose()
      } else {
        const result = await AuthAPI.register({ email, password, username: username || undefined })
        localStorage.setItem("user", JSON.stringify(result.user))
        localStorage.setItem("user_id", result.user.id)
        onLoginSuccess(result.user)
        onClose()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  const switchMode = () => {
    setIsLogin(!isLogin)
    setError("")
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-2xl font-bold mb-6 text-center">
          {isLogin ? "Sign In" : "Create Account"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username (optional)
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Enter your username"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Enter your email"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Enter your password"
              required
              minLength={6}
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm text-center">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Loading..." : isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <button
            onClick={switchMode}
            className="text-primary hover:underline font-medium"
          >
            {isLogin ? "Sign Up" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  )
}

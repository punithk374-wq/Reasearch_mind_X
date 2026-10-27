import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";
import { useAuth } from "../AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(fullName, email, password);
      navigate("/");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 400) {
        setError("That email is already registered");
      } else if (isAxiosError(err) && err.response?.status === 422) {
        setError("Check your details: password must be at least 8 characters");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-slate-800 p-8 rounded-xl shadow-lg space-y-4"
      >
        <h1 className="text-2xl font-bold text-emerald-400">ResearchMind X</h1>
        <p className="text-slate-400 text-sm">Create your account</p>

        {error && (
          <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded">{error}</div>
        )}

        <input
          type="text"
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          minLength={2}
          className="w-full p-3 rounded bg-slate-700 text-white placeholder-slate-400 outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full p-3 rounded bg-slate-700 text-white placeholder-slate-400 outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <input
          type="password"
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          maxLength={72}
          className="w-full p-3 rounded bg-slate-700 text-white placeholder-slate-400 outline-none focus:ring-2 focus:ring-emerald-500"
        />

        <button
          type="submit"
          disabled={submitting}
          className="w-full p-3 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold"
        >
          {submitting ? "Creating account..." : "Register"}
        </button>

        <p className="text-slate-400 text-sm text-center">
          Already have an account?{" "}
          <Link to="/login" className="text-emerald-400 hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}
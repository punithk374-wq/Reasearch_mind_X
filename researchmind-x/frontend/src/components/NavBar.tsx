import { NavLink } from "react-router-dom";
import { useAuth } from "../AuthContext";

const LINKS = [
  { to: "/", label: "My papers", end: true },
  { to: "/discover", label: "Discover" },
  { to: "/search", label: "Search" },
  { to: "/ask", label: "Ask" },
  { to: "/compare", label: "Compare" },
  { to: "/gaps", label: "Gaps" },
  { to: "/research", label: "Research" },
];

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
      <h1 className="text-xl font-bold text-emerald-400">ResearchMind X</h1>
      <div className="flex items-center gap-2">
        {LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) =>
              `text-sm px-3 py-1.5 rounded ${
                isActive
                  ? "bg-emerald-500/20 text-emerald-300"
                  : "bg-slate-800 hover:bg-slate-700"
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
        <span className="text-slate-300 text-sm ml-2">{user?.full_name}</span>
        <button
          onClick={logout}
          className="text-sm px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
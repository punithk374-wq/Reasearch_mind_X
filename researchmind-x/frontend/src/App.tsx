import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Search from "./pages/Search";
import Ask from "./pages/Ask";
import Compare from "./pages/Compare";
import Gaps from "./pages/Gaps";
import Research from "./pages/Research";
import Discover from "./pages/Discover";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      <Route
        path="/discover"
        element={
          <ProtectedRoute>
            <Discover />
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <Search />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ask"
        element={
          <ProtectedRoute>
            <Ask />
          </ProtectedRoute>
        }
      />
      <Route
        path="/compare"
        element={
          <ProtectedRoute>
            <Compare />
          </ProtectedRoute>
        }
      />
      <Route
        path="/gaps"
        element={
          <ProtectedRoute>
            <Gaps />
          </ProtectedRoute>
        }
      />
      <Route
        path="/research"
        element={
          <ProtectedRoute>
            <Research />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
import { useState } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Landing from "./components/Landing";
import AgentChat from "./components/AgentChat";
import Catalog from "./components/Catalog";
import Cart from "./components/Cart";
import AuditLog from "./components/AuditLog";

function Navbar() {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  if (isLanding) return null;

  return (
    <header className="fixed top-0 left-0 right-0 z-40 mt-4">
      <nav className="nav-pill mx-auto w-[calc(100%-2rem)] max-w-5xl flex items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2.5 no-underline">
          <img
            src="/Green_and_Natural_Green_Logo_Main.png"
            alt="MoneyOS"
            className="h-7 w-auto"
          />
          <span className="font-display text-base font-semibold text-near-black tracking-tight">
            MoneyOS
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {[
            { to: "/", label: "Catalog" },
            { to: "/cart", label: "Cart" },
            { to: "/agent", label: "Agent" },
            { to: "/audit", label: "Audit" },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`px-4 py-2 rounded-full font-body text-sm transition-all duration-400 spring ${
                location.pathname === item.to
                  ? "bg-emerald text-white font-medium"
                  : "text-slate-mid hover:text-near-black hover:bg-forest-100"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}

export default function App() {
  const [cart, setCart] = useState<Map<string, number>>(new Map());

  function addToCart(item_id: string) {
    setCart((prev) => {
      const next = new Map(prev);
      next.set(item_id, (next.get(item_id) ?? 0) + 1);
      return next;
    });
  }

  function clearCart() {
    setCart(new Map());
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/catalog" element={<div className="grain-overlay mesh-bg min-h-[100dvh] pt-28 pb-16 max-w-6xl mx-auto px-5 md:px-8"><Navbar /><Catalog onAddToCart={addToCart} /></div>} />
        <Route path="/cart" element={<div className="grain-overlay mesh-bg min-h-[100dvh] pt-28 pb-16 max-w-6xl mx-auto px-5 md:px-8"><Navbar /><Cart cart={cart} onClearCart={clearCart} /></div>} />
        <Route path="/agent" element={<div className="grain-overlay mesh-bg min-h-[100dvh] pt-28 pb-16 max-w-6xl mx-auto px-5 md:px-8"><Navbar /><AgentChat /></div>} />
        <Route path="/audit" element={<div className="grain-overlay mesh-bg min-h-[100dvh] pt-28 pb-16 max-w-6xl mx-auto px-5 md:px-8"><Navbar /><AuditLog /></div>} />
      </Routes>
    </BrowserRouter>
  );
}

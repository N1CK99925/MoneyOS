import { useState } from "react";
import {
  createCheckoutSession,
  completeCheckout,
  cancelCheckout,
  fetchRazorpayKey,
} from "../api/client";
import type { CheckoutSession, CartItem } from "../types";

interface Props {
  cart: Map<string, number>;
  onClearCart: () => void;
}

export default function Cart({ cart, onClearCart }: Props) {
  const [session, setSession] = useState<CheckoutSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const items: CartItem[] = Array.from(cart.entries()).map(([item_id, quantity]) => ({
    item_id,
    quantity,
  }));

  async function handleCheckout() {
    if (items.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const s = await createCheckoutSession(items);
      setSession(s);

      const { key_id } = await fetchRazorpayKey();
      const rzp = new Razorpay({
        key: key_id,
        amount: s.total_paise,
        currency: s.currency,
        name: "MoneyOS",
        order_id: s.razorpay_order_id,
        handler: async () => {
          try {
            const result = await completeCheckout(s.session_id);
            setSession(result as CheckoutSession);
            onClearCart();
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Payment verification failed");
          }
        },
        theme: { color: "#009060" },
      });
      rzp.open();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel() {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      await cancelCheckout(session.session_id);
      setSession(null);
      onClearCart();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setLoading(false);
    }
  }

  if (cart.size === 0 && !session)
    return (
      <div className="card-bezel max-w-md mx-auto">
        <div className="card-bezel-inner text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-forest-100 flex items-center justify-center mx-auto mb-5">
            <svg className="w-7 h-7 text-forest-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
            </svg>
          </div>
          <h3 className="font-display text-lg font-semibold text-near-black mb-2">
            Your cart is empty
          </h3>
          <p className="font-body text-sm text-slate-mid">
            Browse the catalog to add items.
          </p>
        </div>
      </div>
    );

  return (
    <section>
      {/* Header */}
      <div className="mb-12">
        <span className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 bg-forest-100 border border-forest-200/60 mb-5">
          <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-dark-emerald font-medium">
            Checkout
          </span>
        </span>
        <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-near-black tracking-tight">
          Your Cart
        </h1>
      </div>

      {!session ? (
        <div className="card-bezel max-w-2xl">
          <div className="card-bezel-inner space-y-4">
            {/* Cart Items */}
            <div className="space-y-3">
              {Array.from(cart.entries()).map(([id, qty]) => (
                <div
                  key={id}
                  className="flex items-center justify-between py-3 px-4 bg-forest-50 rounded-xl border border-forest-100"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center border border-forest-100">
                      <svg className="w-5 h-5 text-forest-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                      </svg>
                    </div>
                    <div>
                      <p className="font-body text-sm font-medium text-near-black">{id}</p>
                      <p className="font-body text-xs text-slate-light">Qty: {qty}</p>
                    </div>
                  </div>
                  <span className="font-display text-sm font-semibold text-emerald">
                    ×{qty}
                  </span>
                </div>
              ))}
            </div>

            <div className="pt-2">
              <button
                onClick={handleCheckout}
                disabled={loading || items.length === 0}
                className="w-full btn-primary justify-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating session…
                  </>
                ) : (
                  <>
                    Proceed to Checkout
                    <span className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center text-sm transition-all duration-500 spring">
                      ↗
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="card-bezel max-w-2xl">
          <div className="card-bezel-inner space-y-6">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                session.status === "completed"
                  ? "bg-emerald/10"
                  : "bg-forest-100"
              }`}>
                {session.status === "completed" ? (
                  <svg className="w-6 h-6 text-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 text-forest-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                  </svg>
                )}
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-near-black">
                  {session.status === "completed" ? "Payment Confirmed" : "Session Active"}
                </h3>
                <p className="font-body text-sm text-slate-mid">
                  {session.session_id}
                </p>
              </div>
            </div>

            <div className="bg-forest-50 rounded-2xl p-5 border border-forest-100 space-y-3">
              <div className="flex justify-between">
                <span className="font-body text-sm text-slate-mid">Status</span>
                <span className={`font-body text-sm font-medium ${
                  session.status === "completed" ? "text-emerald" : "text-dark-emerald"
                }`}>
                  {session.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="font-body text-sm text-slate-mid">Total</span>
                <span className="font-display text-lg font-bold text-near-black">
                  ₹{(session.total_paise / 100).toFixed(2)}
                </span>
              </div>
            </div>

            {session.status === "ready_for_payment" && (
              <button
                onClick={handleCancel}
                disabled={loading}
                className="w-full btn-secondary justify-center"
              >
                {loading ? "Cancelling…" : "Cancel Order"}
              </button>
            )}

            {session.status === "completed" && (
              <div className="text-center py-4">
                <p className="font-body text-sm text-emerald font-medium">
                  Your payment has been confirmed. Thank you!
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 card-bezel max-w-2xl">
          <div className="card-bezel-inner flex items-center gap-3 py-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <p className="font-body text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}
    </section>
  );
}

import { useEffect, useState } from "react";
import { fetchCatalog } from "../api/client";
import type { Product } from "../types";

interface Props {
  onAddToCart: (item_id: string) => void;
}

export default function Catalog({ onAddToCart }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [merchant, setMerchant] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCatalog()
      .then((data) => {
        setProducts(data.products);
        setMerchant(data.merchant);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="flex items-center justify-center py-32">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-forest-200 border-t-emerald rounded-full animate-spin" />
          <p className="font-body text-sm text-slate-mid">Loading catalog…</p>
        </div>
      </div>
    );

  if (error)
    return (
      <div className="card-bezel max-w-md mx-auto">
        <div className="card-bezel-inner text-center py-12">
          <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="font-body text-sm text-slate-mid">{error}</p>
        </div>
      </div>
    );

  return (
    <section>
      {/* Header */}
      <div className="mb-12">
        <span className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 bg-forest-100 border border-forest-200/60 mb-5">
          <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-dark-emerald font-medium">
            Catalog
          </span>
        </span>
        <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold text-near-black tracking-tight">
          {merchant}
        </h1>
      </div>

      {/* Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {products.map((p) => (
          <div key={p.id} className="card-bezel group">
            <div className="card-bezel-inner h-full flex flex-col">
              {/* Placeholder Image Area */}
              <div className="bg-gradient-to-br from-forest-50 to-forest-100 rounded-2xl h-40 mb-5 flex items-center justify-center border border-forest-100">
                <svg className="w-10 h-10 text-forest-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
              </div>

              <h3 className="font-display text-base font-semibold text-near-black mb-1.5">
                {p.name}
              </h3>
              <p className="font-body text-sm text-slate-mid leading-relaxed mb-5 flex-1">
                {p.description}
              </p>

              <div className="flex items-center justify-between mt-auto">
                <p className="font-display text-xl font-bold text-emerald">
                  ₹{(p.price_paise / 100).toFixed(2)}
                </p>
                <button
                  onClick={() => onAddToCart(p.id)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald text-white font-body text-sm font-medium rounded-full transition-all duration-500 spring hover:bg-deep-forest hover:shadow-lg hover:shadow-emerald/20 hover:-translate-y-0.5 active:scale-[0.97]"
                >
                  Add to Cart
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

import { useState, useRef, useEffect } from "react";
import { runAgent } from "../api/client";
import type { AgentEvent } from "../types";

interface Message {
  role: "user" | "agent" | "tool" | "error";
  content: string;
  name?: string;
}

export default function AgentChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<{ abort: () => void } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const goal = input.trim();
    if (!goal || running) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: goal }]);
    setRunning(true);

    const abortRefCurrent: Message[] = [];
    let currentTool = "";

    abortRef.current = runAgent(goal, (event: AgentEvent) => {
      switch (event.type) {
        case "model_switch":
          setMessages((prev) => [
            ...prev,
            { role: "agent", content: `Using model: ${event.model}` },
          ]);
          break;

        case "tool_call":
          currentTool = event.name;
          abortRefCurrent.push({
            role: "tool",
            content: `Calling ${event.name}...`,
            name: event.name,
          });
          setMessages((prev) => [...prev, abortRefCurrent[abortRefCurrent.length - 1]]);
          break;

        case "tool_result": {
          let shortResult = event.result;
          try {
            const parsed = JSON.parse(event.result);
            if (parsed.matches) {
              shortResult = `Found ${parsed.matches.length} items`;
              if (parsed.matches.length > 0) {
                shortResult += ": " + parsed.matches
                  .slice(0, 3)
                  .map((m: { name: string; price_paise: number }) =>
                    `${m.name} (₹${(m.price_paise / 100).toFixed(0)})`
                  )
                  .join(", ");
              }
            } else if (parsed.session_id) {
              shortResult = `Session ${parsed.session_id} - ₹${((parsed.total_paise || 0) / 100).toFixed(0)} - ${parsed.status}`;
            } else if (parsed.status) {
              shortResult = `Status: ${parsed.status}`;
            } else if (parsed.error) {
              shortResult = `Error: ${parsed.error}`;
            }
          } catch {
            // keep raw
          }
          setMessages((prev) => {
            const next = [...prev];
            for (let i = next.length - 1; i >= 0; i--) {
              if (next[i].role === "tool" && next[i].name === currentTool && next[i].content.endsWith("...")) {
                next[i] = { ...next[i], content: shortResult };
                break;
              }
            }
            return next;
          });
          break;
        }

        case "summary":
          setMessages((prev) => [...prev, { role: "agent", content: event.message }]);
          setRunning(false);
          break;

        case "error":
          setMessages((prev) => [...prev, { role: "error", content: event.message }]);
          setRunning(false);
          break;
      }
    });
  }

  function handleStop() {
    abortRef.current?.abort();
    setRunning(false);
    setMessages((prev) => [...prev, { role: "error", content: "Stopped." }]);
  }

  return (
    <section className="flex flex-col" style={{ height: "calc(100dvh - 10rem)" }}>
      {/* Header */}
      <div className="mb-6">
        <span className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 bg-forest-100 border border-forest-200/60 mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-mint-accent animate-pulse" />
          <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-dark-emerald font-medium">
            AI Agent
          </span>
        </span>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-near-black tracking-tight">
          Buyer Agent
        </h1>
        <p className="font-body text-sm text-slate-mid mt-2">
          Tell the agent what to buy. It will search, negotiate, and complete checkout.
        </p>
      </div>

      {/* Messages */}
      <div className="card-bezel flex-1 min-h-0">
        <div className="card-bezel-inner h-full flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 p-1">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-16">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald/10 to-mint-accent/10 flex items-center justify-center mb-5">
                  <svg className="w-7 h-7 text-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                </div>
                <h3 className="font-display text-base font-semibold text-near-black mb-1">
                  How can I help?
                </h3>
                <p className="font-body text-sm text-slate-mid max-w-xs">
                  Try: "buy chicken biriyani under ₹500" or "find the cheapest office supplies"
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex flex-col gap-1 ${
                  msg.role === "user" ? "items-end" : "items-start"
                }`}
              >
                {msg.role !== "user" && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-slate-light font-medium px-1">
                    {msg.role === "agent" ? "Agent" : msg.role === "tool" ? msg.name : "Error"}
                  </span>
                )}
                <div
                  className={`max-w-[80%] px-4 py-2.5 rounded-2xl font-body text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-emerald text-white rounded-br-md"
                      : msg.role === "error"
                      ? "bg-red-50 text-red-700 border border-red-100 rounded-bl-md"
                      : msg.role === "tool"
                      ? "bg-forest-50 text-slate-dark border border-forest-100 rounded-bl-md font-mono text-xs"
                      : "bg-warm-white text-slate-dark border border-forest-100 rounded-bl-md"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-4">
        <div className="card-bezel">
          <div className="card-bezel-inner flex items-center gap-3 !p-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='e.g. "buy chicken biriyani under ₹500"'
              disabled={running}
              className="flex-1 bg-transparent px-4 py-2.5 font-body text-sm text-near-black placeholder:text-slate-light focus:outline-none"
            />
            {running ? (
              <button
                type="button"
                onClick={handleStop}
                className="px-5 py-2.5 bg-red-50 text-red-600 font-body text-sm font-medium rounded-full border border-red-100 transition-all duration-500 spring hover:bg-red-100 active:scale-[0.97]"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="w-10 h-10 rounded-full bg-emerald flex items-center justify-center transition-all duration-500 spring hover:bg-deep-forest hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}

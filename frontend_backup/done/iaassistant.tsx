import React, { useState, useRef, useEffect } from "react";
import { Bot, Send, Sparkles, Database, Zap, FileText, Loader2 } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export default function App() {
  const [chatHistory, setChatHistory] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const getTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const handleSend = async () => {
    if (!userInput.trim()) return;

    const message = { role: "user" as const, content: userInput.trim(), timestamp: getTimestamp() };
    setChatHistory((prev) => [...prev, message]);
    setUserInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ai/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: message.content }),
      });

      const data = await response.json();

      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, timestamp: getTimestamp() },
      ]);
    } catch (err) {
      console.error(err);
      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Could not reach assistant.", timestamp: getTimestamp() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatHistory, loading]);

  const quickActions = [
    { icon: Database, text: "Database Setup", query: "How do I set up a database on Huawei Cloud?" },
    { icon: Zap, text: "Performance Tips", query: "What are the best practices for optimizing performance?" },
    { icon: FileText, text: "Troubleshooting", query: "Help me troubleshoot deployment issues" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-lg p-2 shadow-sm">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Huawei Cloud Assistant</h1>
              <p className="text-xs text-gray-500">Powered by RAG & Ollama</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Online</span>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Quick Actions - Only show when empty */}
        {chatHistory.length === 0 && (
          <div className="mb-6 space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold text-gray-900">How can I help you today?</h2>
              <p className="text-gray-500">Ask me anything about Huawei Cloud services and best practices</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setUserInput(action.query);
                  }}
                  className="flex flex-col items-start space-y-2 p-4 bg-white hover:bg-gray-50 rounded-xl border border-gray-200 hover:border-gray-300 transition-all duration-200 text-left group"
                >
                  <div className="bg-gray-100 group-hover:bg-red-50 rounded-lg p-2 transition-colors">
                    <action.icon className="w-5 h-5 text-gray-700 group-hover:text-red-600" />
                  </div>
                  <div className="space-y-1">
                    <div className="font-medium text-gray-900 text-sm">{action.text}</div>
                    <div className="text-xs text-gray-500 line-clamp-2">{action.query}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Container */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Chat Messages */}
          <div className="h-[500px] overflow-y-auto p-6 space-y-6">
            {chatHistory.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <div className="bg-gray-100 rounded-full p-6">
                  <Sparkles className="w-10 h-10 text-gray-400" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-gray-900">Ready to assist</h3>
                  <p className="text-sm text-gray-500 max-w-md">
                    I'll search through the Huawei Cloud knowledge base to provide accurate answers to your questions.
                  </p>
                </div>
              </div>
            )}

            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`flex items-start space-x-3 max-w-[80%] ${
                    msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""
                  }`}
                >
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    msg.role === "assistant"
                      ? "bg-gradient-to-br from-red-500 to-red-600"
                      : "bg-gray-300"
                  }`}>
                    {msg.role === "assistant" ? (
                      <Bot className="w-5 h-5 text-white" />
                    ) : (
                      <span className="text-xs font-medium text-gray-700">U</span>
                    )}
                  </div>
                  <div className="space-y-1">
                    <div
                      className={`px-4 py-3 rounded-2xl ${
                        msg.role === "user"
                          ? "bg-gray-900 text-white"
                          : "bg-gray-100 text-gray-900"
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    <p className={`text-xs px-2 ${
                      msg.role === "user" ? "text-right text-gray-400" : "text-gray-500"
                    }`}>
                      {msg.timestamp}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-3 max-w-[80%]">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-red-500 to-red-600">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="space-y-1">
                    <div className="px-4 py-3 rounded-2xl bg-gray-100">
                      <div className="flex items-center space-x-2">
                        <Loader2 className="w-4 h-4 text-gray-600 animate-spin" />
                        <span className="text-sm text-gray-600">Searching knowledge base...</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Section */}
          <div className="border-t border-gray-200 p-4 bg-gray-50">
            <div className="flex items-end space-x-3">
              <div className="flex-1">
                <textarea
                  className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none transition-all duration-200"
                  placeholder="Ask about Huawei Cloud..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={loading}
                  rows={1}
                  style={{ minHeight: "44px", maxHeight: "120px" }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "44px";
                    target.style.height = Math.min(target.scrollHeight, 120) + "px";
                  }}
                />
              </div>
              <button
                onClick={handleSend}
                disabled={loading || !userInput.trim()}
                className={`px-4 py-3 rounded-xl font-medium flex items-center justify-center transition-all duration-200 ${
                  loading || !userInput.trim()
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-gradient-to-br from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-sm hover:shadow"
                }`}
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="mt-3 text-center text-xs text-gray-400">
              Powered by Ollama + Elasticsearch + Huawei Cloud Knowledge Base
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

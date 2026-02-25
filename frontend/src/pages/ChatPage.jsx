/**
 * ChatPage.jsx — Natural Language Chat Interface
 *
 * A real-time conversational UI where users ask questions about
 * their data in plain English and receive AI-powered answers.
 *
 * Features:
 *  - Message bubbles with user/assistant roles
 *  - Markdown rendering in responses
 *  - Typing indicator during AI processing
 *  - Contextual question suggestions
 *  - File selector for different datasets
 *  - Tool call visibility (transparency into agent actions)
 *  - Auto-scroll to latest message
 *  - Keyboard shortcuts (Enter to send)
 */

import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  ChevronDown,
  ChevronUp,
  Database,
  Lightbulb,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  User,
  Wrench
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { askQuestion, getChatSuggestions, runAnalysis } from "../services/api";

/* ─── Markdown-lite renderer ───────────────────────────────────── */

function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements = [];
  let inCodeBlock = false;
  let codeLines = [];
  let codeLang = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="bg-gray-900 text-green-300 rounded-lg p-4 my-2 text-sm overflow-x-auto font-mono">
            {codeLang && <div className="text-gray-500 text-xs mb-1">{codeLang}</div>}
            <code>{codeLines.join("\n")}</code>
          </pre>
        );
        codeLines = [];
        codeLang = "";
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLang = line.trim().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Headers
    if (line.startsWith("### ")) {
      elements.push(<h3 key={i} className="text-sm font-bold mt-3 mb-1 text-gray-800">{formatInline(line.slice(4))}</h3>);
    } else if (line.startsWith("## ")) {
      elements.push(<h2 key={i} className="text-base font-bold mt-3 mb-1 text-gray-900">{formatInline(line.slice(3))}</h2>);
    } else if (line.startsWith("# ")) {
      elements.push(<h1 key={i} className="text-lg font-bold mt-4 mb-2 text-gray-900">{formatInline(line.slice(2))}</h1>);
    }
    // Bullet lists
    else if (line.match(/^\s*[-*]\s/)) {
      const indent = line.search(/\S/);
      const content = line.replace(/^\s*[-*]\s/, "");
      elements.push(
        <div key={i} className="flex gap-2 my-0.5" style={{ marginLeft: Math.min(indent, 4) * 8 }}>
          <span className="text-indigo-400 font-bold mt-0.5 shrink-0">•</span>
          <span className="text-gray-700 text-sm">{formatInline(content)}</span>
        </div>
      );
    }
    // Numbered lists
    else if (line.match(/^\s*\d+\.\s/)) {
      const match = line.match(/^(\s*)(\d+)\.\s(.*)/);
      if (match) {
        elements.push(
          <div key={i} className="flex gap-2 my-0.5" style={{ marginLeft: Math.min(match[1].length, 4) * 8 }}>
            <span className="text-indigo-500 font-semibold shrink-0 text-sm">{match[2]}.</span>
            <span className="text-gray-700 text-sm">{formatInline(match[3])}</span>
          </div>
        );
      }
    }
    // Horizontal rules
    else if (line.match(/^---+$/)) {
      elements.push(<hr key={i} className="border-gray-200 my-3" />);
    }
    // Empty lines
    else if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
    }
    // Normal paragraphs
    else {
      elements.push(<p key={i} className="text-sm text-gray-700 my-0.5 leading-relaxed">{formatInline(line)}</p>);
    }
  }

  return elements;
}

function formatInline(text) {
  // Bold + italic
  const parts = [];
  const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2]) {
      parts.push(<strong key={match.index} className="italic">{match[2]}</strong>);
    } else if (match[3]) {
      parts.push(<strong key={match.index} className="text-gray-900">{match[3]}</strong>);
    } else if (match[4]) {
      parts.push(<em key={match.index}>{match[4]}</em>);
    } else if (match[5]) {
      parts.push(
        <code key={match.index} className="bg-gray-100 text-indigo-600 px-1.5 py-0.5 rounded text-xs font-mono">
          {match[5]}
        </code>
      );
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

/* ─── Typing Indicator ─────────────────────────────────────────── */

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-indigo-600" />
      </div>
      <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

/* ─── Tool Call Badge ──────────────────────────────────────────── */

function ToolCallBadge({ tools }) {
  const [expanded, setExpanded] = useState(false);
  if (!tools || tools.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition"
      >
        <Wrench className="w-3 h-3" />
        {tools.length} tool{tools.length > 1 ? "s" : ""} used
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {expanded && (
        <div className="mt-1.5 space-y-1">
          {tools.map((t, i) => (
            <div key={i} className="bg-gray-50 rounded px-2 py-1 text-xs font-mono text-gray-500">
              <span className="text-indigo-500">{t.tool}</span>
              {t.args && Object.keys(t.args).length > 0 && (
                <span className="text-gray-400 ml-1">({Object.entries(t.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Message Bubble ───────────────────────────────────────────── */

function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-start gap-3 px-4 py-2 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${isUser ? "bg-blue-100" : message.error ? "bg-red-100" : "bg-indigo-100"
        }`}>
        {isUser ? (
          <User className="w-4 h-4 text-blue-600" />
        ) : (
          <Bot className={`w-4 h-4 ${message.error ? "text-red-600" : "text-indigo-600"}`} />
        )}
      </div>

      {/* Content */}
      <div className={`max-w-[75%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-3 shadow-sm ${isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : message.error
                ? "bg-red-50 border border-red-200 rounded-tl-sm"
                : "bg-white border rounded-tl-sm"
            }`}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="prose-sm">{renderMarkdown(message.content)}</div>
          )}
        </div>
        {!isUser && <ToolCallBadge tools={message.tools} />}
        <p className="text-[10px] text-gray-400 mt-1 px-1">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

/* ─── Suggestion Chips ─────────────────────────────────────────── */

function SuggestionChips({ suggestions, onSelect, disabled }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
        <span className="text-xs font-medium text-gray-500">Suggested questions</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s)}
            disabled={disabled}
            className="text-xs bg-white border border-gray-200 rounded-full px-3 py-1.5 text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── Welcome Screen ───────────────────────────────────────────── */

function WelcomeScreen({ suggestions, onSelect, disabled }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-8 py-12 text-center">
      <div className="w-16 h-16 rounded-2xl bg-indigo-100 flex items-center justify-center mb-4">
        <Sparkles className="w-8 h-8 text-indigo-500" />
      </div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">Ask anything about your data</h3>
      <p className="text-sm text-gray-500 max-w-md mb-8">
        I can analyze trends, find anomalies, explain correlations, generate summaries,
        and answer business questions — all in plain English.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {(suggestions || [
          "What are the key insights from this dataset?",
          "Are there any anomalies or outliers?",
          "Summarize the main trends.",
          "Which columns are most correlated?",
        ]).map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            disabled={disabled}
            className="text-left border rounded-xl px-4 py-3 text-sm text-gray-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition disabled:opacity-50 group"
          >
            <Lightbulb className="w-4 h-4 text-amber-400 group-hover:text-amber-500 mb-1" />
            <span>{q}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════════════ */

function ChatPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fileId = searchParams.get("file_id");

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [analysisReady, setAnalysisReady] = useState(null); // null=unknown, true/false
  const [preparingAnalysis, setPreparingAnalysis] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Load suggestions when file is available
  useEffect(() => {
    if (!fileId) return;
    getChatSuggestions(fileId)
      .then((res) => setSuggestions(res.suggestions || []))
      .catch(() => { });
  }, [fileId]);

  // Check if analysis is ready by trying suggestions endpoint
  useEffect(() => {
    if (!fileId) return;
    setAnalysisReady(null);
    getChatSuggestions(fileId)
      .then((res) => {
        // If we got data-specific suggestions (more than 3), analysis is cached
        setAnalysisReady(res.suggestions && res.suggestions.length > 3);
      })
      .catch(() => setAnalysisReady(false));
  }, [fileId]);

  const handlePrepareAnalysis = async () => {
    if (!fileId) return;
    setPreparingAnalysis(true);
    try {
      await runAnalysis(fileId);
      setAnalysisReady(true);
      // Reload suggestions
      const res = await getChatSuggestions(fileId);
      setSuggestions(res.suggestions || []);
    } catch (err) {
      console.error(err);
      setAnalysisReady(false);
    } finally {
      setPreparingAnalysis(false);
    }
  };

  const sendMessage = async (text) => {
    const question = (text || input).trim();
    if (!question || loading || !fileId) return;

    const userMsg = {
      id: Date.now(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await askQuestion(fileId, question, history);

      const assistantMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: res.answer,
        tools: res.tool_calls || [],
        error: res.error || false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      if (res.session_id) setSessionId(res.session_id);
      if (res.suggestions && res.suggestions.length > 0) setSuggestions(res.suggestions);
    } catch (err) {
      console.error(err);
      const errorMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: `Sorry, something went wrong: ${err.response?.data?.detail || err.message}`,
        error: true,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
  };

  /* ─── No file selected ──────────────────────────────── */
  if (!fileId) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Chat with Your Data</h2>
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <MessageSquare className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-500">No Dataset Selected</h3>
          <p className="text-gray-400 mt-2">Upload and analyze a file first, then come here to chat.</p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Go to Upload
          </button>
        </div>
      </div>
    );
  }

  /* ─── Main Chat UI ──────────────────────────────────── */
  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
            <Bot className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">AutoBI Chat</h2>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Database className="w-3 h-3" />
              <span>Dataset: {fileId}</span>
              {sessionId && <span className="text-gray-300">|</span>}
              {sessionId && <span>Session active</span>}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
              title="Clear conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => navigate("/")}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
            title="Back to upload"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Analysis readiness banner */}
      {analysisReady === false && !preparingAnalysis && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mt-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-amber-700">Analysis not yet run for this dataset.</span>
          </div>
          <button
            onClick={handlePrepareAnalysis}
            className="text-sm bg-amber-500 text-white px-3 py-1 rounded-lg hover:bg-amber-600 transition"
          >
            Run Analysis
          </button>
        </div>
      )}
      {preparingAnalysis && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mt-3 flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
          <span className="text-sm text-indigo-700">Running analysis pipeline... This may take a moment.</span>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto mt-3 -mx-4 scrollbar-thin">
        {messages.length === 0 ? (
          <WelcomeScreen
            suggestions={suggestions}
            onSelect={(q) => sendMessage(q)}
            disabled={loading || analysisReady === false}
          />
        ) : (
          <div className="space-y-1 py-2">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Suggestion chips (after first response) */}
      {messages.length > 0 && !loading && suggestions.length > 0 && (
        <SuggestionChips
          suggestions={suggestions}
          onSelect={(q) => sendMessage(q)}
          disabled={loading}
        />
      )}

      {/* Input Area */}
      <div className="border-t pt-3 mt-auto">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                analysisReady === false
                  ? "Run analysis first to enable chat..."
                  : "Ask a question about your data..."
              }
              disabled={loading || analysisReady === false}
              rows={1}
              className="w-full resize-none rounded-xl border border-gray-300 px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 placeholder-gray-400"
              style={{ minHeight: "46px", maxHeight: "120px" }}
              onInput={(e) => {
                e.target.style.height = "46px";
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
              }}
            />
          </div>
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim() || analysisReady === false}
            className="h-[46px] w-[46px] rounded-xl bg-indigo-600 text-white flex items-center justify-center hover:bg-indigo-700 transition disabled:bg-gray-300 disabled:cursor-not-allowed shrink-0"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-gray-400 mt-1.5 text-center">
          Press Enter to send, Shift+Enter for new line. AI responses may be inaccurate.
        </p>
      </div>
    </div>
  );
}

export default ChatPage;

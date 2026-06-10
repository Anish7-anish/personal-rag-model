import { useState } from "react";
import { queryDocuments } from "../services/api";

const QueryPanel = () => {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setError("Ask a question first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setQuestion("");

    const userMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const result = await queryDocuments({ query: trimmed });
      const assistantMessage = {
        role: "assistant",
        content: result.answer || "I don't know.",
        sources: result.sources || [],
        traceId: result.trace_id || "",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || "Query failed.";
      setError(detail);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I don't know." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask anything about your uploaded documents.</p>
            <p>The assistant will only answer from that context.</p>
          </div>
        )}
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
            <p>{message.content}</p>
            {message.traceId && <p className="trace-id">Trace ID: {message.traceId}</p>}
            {message.role === "assistant" && message.sources?.length > 0 && (
              <div className="sources">
                <h4>Sources</h4>
                <ul>
                  {message.sources.map((source, sourceIndex) => (
                    <li key={`${source?.document_id || sourceIndex}-${sourceIndex}`}>
                      {source?.filename || "Unknown file"}
                      {typeof source?.chunk_index === "number" ? `, chunk ${source.chunk_index + 1}` : ""}
                      {typeof source?.score === "number" ? `, score ${source.score}` : ""}
                      {source?.preview ? ` — ${source.preview}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        {isLoading && <div className="chat-bubble assistant">Thinking...</div>}
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Ask a question..."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
      {error && <p className="status error">{error}</p>}
    </div>
  );
};

export default QueryPanel;

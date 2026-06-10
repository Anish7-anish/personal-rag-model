import { useEffect, useState } from "react";
import { fetchDocuments } from "../services/api";

const DocumentLibrary = ({ refreshKey = 0 }) => {
  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const loadDocuments = async () => {
    setIsLoading(true);
    setError("");
    try {
      const result = await fetchDocuments();
      setDocuments(result.documents || []);
      setTotalChunks(result.total_chunks || 0);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load documents.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [refreshKey]);

  return (
    <div className="library-panel">
      <div className="library-toolbar">
        <h2>2. Indexed Corpus</h2>
        <button type="button" onClick={loadDocuments} disabled={isLoading}>
          {isLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && <p className="status error">{error}</p>}

      {documents.length > 0 && (
        <p className="status corpus-summary">
          {documents.length} documents indexed, {totalChunks} total chunks. Chunk previews are logged in the backend console during indexing.
        </p>
      )}

      {documents.length === 0 && !isLoading ? (
        <p className="status">No indexed documents yet.</p>
      ) : (
        <div className="document-list">
          {documents.map((document) => (
            <article key={document.id} className="document-row">
              <strong>{document.filename}</strong>
              <span>{document.chunk_count} chunks</span>
              <span>{new Date(document.updated_at).toLocaleString()}</span>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentLibrary;

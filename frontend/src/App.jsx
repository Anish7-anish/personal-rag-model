import { useState } from "react";
import DocumentLibrary from "./components/DocumentLibrary";
import FileUpload from "./components/FileUpload";
import QueryPanel from "./components/QueryPanel";

const App = () => {
  const [lastUploadMessage, setLastUploadMessage] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = (message) => {
    setLastUploadMessage(message);
    setRefreshKey((current) => current + 1);
  };

  return (
    <div className="app-shell">
      <header>
        <h1>Personal RAG Explorer</h1>
        <p>Upload personal documents and ask questions powered by the backend API.</p>
      </header>

      <main>
        <section className="card">
          <h2>1. Upload Documents</h2>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          {lastUploadMessage && <p className="status success">{lastUploadMessage}</p>}
        </section>

        <section className="card">
          <DocumentLibrary refreshKey={refreshKey} />
        </section>

        <section className="card card-wide">
          <h2>3. Chat with Your Docs</h2>
          <QueryPanel />
        </section>
      </main>

      <footer>
        <small>Backend base URL: {import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"}</small>
      </footer>
    </div>
  );
};

export default App;

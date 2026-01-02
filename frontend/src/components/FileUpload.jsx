import { useState } from "react";
import { uploadDocument } from "../services/api";

const FileUpload = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setError("Select a file first.");
      return;
    }

    setIsUploading(true);
    setError("");

    try {
      const result = await uploadDocument(file);
      onUploadSuccess(result.message || "Uploaded successfully.");
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Upload failed.");
    } finally {
      setIsUploading(false);
      setFile(null);
    }
  };

  return (
    <form className="upload-form" onSubmit={handleSubmit}>
      <label className="file-input">
        <input
          type="file"
          accept=".pdf,.txt,.doc,.docx"
          onChange={(event) => setFile(event.target.files[0] || null)}
          disabled={isUploading}
        />
      </label>
      <button type="submit" disabled={isUploading}>
        {isUploading ? "Uploading..." : "Upload"}
      </button>
      {error && <p className="status error">{error}</p>}
    </form>
  );
};

export default FileUpload;

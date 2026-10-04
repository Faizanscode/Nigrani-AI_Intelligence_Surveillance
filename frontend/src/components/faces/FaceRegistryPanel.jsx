import React, { useState, useEffect } from 'react';
import { UserPlus, Trash2, Camera, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';

const FaceRegistryPanel = () => {
  const [faces, setFaces] = useState([]);
  const [name, setName] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchFaces = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/faces`);
      if (res.ok) {
        const data = await res.json();
        setFaces(data);
      }
    } catch (err) {
      console.error("Error fetching faces:", err);
    }
  };

  useEffect(() => {
    fetchFaces();
  }, []);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(selected);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!name || !file) {
      setError("Please provide both name and image.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE_URL}/faces`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        setName('');
        setFile(null);
        setPreview(null);
        fetchFaces();
      } else {
        const errData = await res.json();
        setError(errData.detail || "Failed to upload face.");
      }
    } catch (err) {
      setError("Network error. Could not connect to API.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this face?")) return;
    
    try {
      const res = await fetch(`${API_BASE_URL}/faces/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchFaces();
      }
    } catch (err) {
      console.error("Error deleting face:", err);
    }
  };

  return (
    <div className="bg-gray-800/60 backdrop-blur-md rounded-2xl border border-gray-700/50 shadow-2xl p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-100 flex items-center gap-2">
          <Camera className="w-5 h-5 text-indigo-400" />
          Face Recognition Registry
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form */}
        <div className="lg:col-span-1 bg-gray-900/50 rounded-xl border border-gray-700/50 p-5">
          <h3 className="text-md font-medium text-gray-200 mb-4">Add New Person</h3>
          
          {error && (
            <div className="mb-4 bg-red-900/30 border border-red-800/50 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <p className="text-sm text-red-200">{error}</p>
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Name / ID</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-indigo-500"
                placeholder="John Doe"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Reference Image</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-500/20 file:text-indigo-400 hover:file:bg-indigo-500/30"
              />
              <p className="text-xs text-gray-500 mt-2">Clear, front-facing photo with good lighting.</p>
            </div>
            
            {preview && (
              <div className="mt-4 rounded-lg overflow-hidden border border-gray-700 bg-black flex justify-center h-40">
                <img src={preview} alt="Preview" className="h-full object-contain" />
              </div>
            )}
            
            <button
              type="submit"
              disabled={loading || !name || !file}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg px-4 py-2 font-medium transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-200 border-t-white"></div>
              ) : (
                <UserPlus className="w-4 h-4" />
              )}
              {loading ? 'Processing...' : 'Enroll Face'}
            </button>
          </form>
        </div>

        {/* Faces List */}
        <div className="lg:col-span-2">
          <div className="bg-gray-900/50 rounded-xl border border-gray-700/50 overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-800/80 border-b border-gray-700">
                  <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Name</th>
                  <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase tracking-wider">ID</th>
                  <th className="py-3 px-4 text-xs font-medium text-gray-400 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {faces.length === 0 ? (
                  <tr>
                    <td colSpan="3" className="py-8 text-center text-gray-500 text-sm">
                      No faces enrolled in the registry.
                    </td>
                  </tr>
                ) : (
                  faces.map((face) => (
                    <tr key={face.id} className="hover:bg-gray-800/30 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-medium text-gray-200">{face.name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-xs text-gray-500 font-mono">{face.id}</div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleDelete(face.id)}
                          className="p-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                          title="Delete Face"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FaceRegistryPanel;

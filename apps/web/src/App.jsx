import { Navigate, Route, Routes } from "react-router-dom";
import Landing from "./Landing.jsx";
import Monitor from "./Monitor.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/monitor" element={<Monitor />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

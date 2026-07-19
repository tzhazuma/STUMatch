import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Legal from '@/pages/Legal';
import Discovery from '@/pages/Discovery';
import UserDetail from '@/pages/UserDetail';
import Profile from '@/pages/Profile';
import Questionnaire from '@/pages/Questionnaire';
import Friends from '@/pages/Friends';
import Chat from '@/pages/Chat';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/legal/:doc" element={<Legal />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/discovery/:section?" element={<Discovery />} />
        <Route path="/discovery/:section/:userId" element={<UserDetail />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/questionnaire/:slug" element={<Questionnaire />} />
        <Route path="/friends" element={<Friends />} />
        <Route path="/chat/:conversationId" element={<Chat />} />
        <Route path="/app" element={<Navigate to="/discovery/academic" replace />} />
      </Route>
    </Routes>
  );
}

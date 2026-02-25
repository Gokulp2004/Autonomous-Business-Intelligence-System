/**
 * App.jsx — Root Application Component
 *
 * Sets up React Router for page navigation.
 * Think of this as the "main layout" of the app.
 */

import { BarChart3, LayoutDashboard, MessageSquare, PieChart, Upload } from 'lucide-react';
import { Link, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import AnalysisPage from './pages/AnalysisPage';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import HomePage from './pages/HomePage';

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-gray-50">
                {/* ── Navigation Bar ──────────────────────────────────── */}
                <nav className="bg-white border-b border-gray-200 shadow-sm">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="flex justify-between h-16 items-center">
                            {/* Logo */}
                            <Link to="/" className="flex items-center gap-2">
                                <BarChart3 className="h-8 w-8 text-blue-600" />
                                <span className="text-xl font-bold text-gray-900">
                                    AutoBI
                                </span>
                            </Link>

                            {/* Nav Links */}
                            <div className="flex items-center gap-6">
                                <Link
                                    to="/"
                                    className="flex items-center gap-1 text-gray-600 hover:text-blue-600 transition-colors"
                                >
                                    <Upload className="h-4 w-4" />
                                    Upload
                                </Link>
                                <Link
                                    to="/analysis"
                                    className="flex items-center gap-1 text-gray-600 hover:text-blue-600 transition-colors"
                                >
                                    <LayoutDashboard className="h-4 w-4" />
                                    Analysis
                                </Link>
                                <Link
                                    to="/dashboard"
                                    className="flex items-center gap-1 text-gray-600 hover:text-blue-600 transition-colors"
                                >
                                    <PieChart className="h-4 w-4" />
                                    Dashboard
                                </Link>
                                <Link
                                    to="/chat"
                                    className="flex items-center gap-1 text-gray-600 hover:text-blue-600 transition-colors"
                                >
                                    <MessageSquare className="h-4 w-4" />
                                    Chat
                                </Link>
                            </div>
                        </div>
                    </div>
                </nav>

                {/* ── Page Content ────────────────────────────────────── */}
                <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <Routes>
                        <Route path="/" element={<HomePage />} />
                        <Route path="/analysis" element={<AnalysisPage />} />
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/chat" element={<ChatPage />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}

export default App;

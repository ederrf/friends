import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import DashboardPage from "./pages/DashboardPage";
import FriendsPage from "./pages/FriendsPage";
import FriendDetailPage from "./pages/FriendDetailPage";
import GroupsPage from "./pages/GroupsPage";
import GroupDetailPage from "./pages/GroupDetailPage";
import InterestsPage from "./pages/InterestsPage";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
            <Link to="/" className="font-semibold">
              Friends
            </Link>
            <Link to="/friends" className="text-sm text-slate-600 hover:text-slate-900">
              Amigos
            </Link>
            <Link to="/groups" className="text-sm text-slate-600 hover:text-slate-900">
              Grupos
            </Link>
            <Link to="/interests" className="text-sm text-slate-600 hover:text-slate-900">
              Interesses
            </Link>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/friends" element={<FriendsPage />} />
            <Route path="/friends/:friendId" element={<FriendDetailPage />} />
            <Route path="/groups" element={<GroupsPage />} />
            <Route path="/groups/:groupId" element={<GroupDetailPage />} />
            <Route path="/interests" element={<InterestsPage />} />
          </Routes>
        </main>
        <Toaster position="bottom-right" />
      </div>
    </BrowserRouter>
  );
}

export default App;

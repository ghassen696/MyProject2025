import { useState, useEffect } from "react";
import axios from "axios";

interface User {
  username: string;
  email: string;
  role: "admin" | "user";
  employee_id: string;
  status: "active" | "pending";
}

export default function AdminPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [inviteData, setInviteData] = useState({ email: "", role: "user", employee_id: "" });
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [stats, setStats] = useState({ total: 0, active: 0, pending: 0, admins: 0 });
  const pageSize = 5;

  // --- Fetch users from backend ---
  const fetchUsers = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/users", {
        params: { search, page, page_size: pageSize },
      });
      setUsers(res.data.users);
      setStats({
        total: res.data.total,
        active: res.data.active,
        pending: res.data.pending,
        admins: res.data.admins,
      });
      return res.data;
    } catch (err) {
      console.error("Failed to fetch users", err);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [search, page]);

  // --- Handlers ---
  // --- Delete user ---
const handleDelete = async (user: User) => {
  try {
    // Optimistically update UI
    setUsers((prev) => prev.filter((u) => u.employee_id !== user.employee_id));
    setStats((prev) => ({
      ...prev,
      total: prev.total - 1,
      active: user.status === "active" ? prev.active - 1 : prev.active,
      pending: user.status === "pending" ? prev.pending - 1 : prev.pending,
      admins: user.role === "admin" ? prev.admins - 1 : prev.admins,
    }));

    await axios.delete(`http://localhost:8000/api/users/${user.employee_id}`);

    // Optional: ensure backend sync
    await fetchUsers();
  } catch (err) {
    console.error("Failed to delete user", err);
  }
};

// --- Update user ---
const handleUpdate = async (user: User) => {
  if (!editingUser) return;
  try {
    await axios.put(`http://localhost:8000/api/users/${user.employee_id}`, editingUser);

    // Optimistically update UI
    setUsers((prev) =>
      prev.map((u) =>
        u.employee_id === user.employee_id
          ? { ...u, email: editingUser.email, role: editingUser.role }
          : u
      )
    );

    // Update stats if role changed
    if (user.role !== editingUser.role) {
      setStats((prev) => ({
        ...prev,
        admins: prev.admins + (editingUser.role === "admin" ? 1 : -1),
      }));
    }

    setEditingUser(null);
  } catch (err) {
    console.error("Failed to update user", err);
  }
};

// --- Activate user ---
const handleActivate = async (user: User) => {
  try {
    await axios.put(`http://localhost:8000/api/users/${user.employee_id}`, { status: "active" });

    // Optimistically update UI
    setUsers((prev) =>
      prev.map((u) =>
        u.employee_id === user.employee_id ? { ...u, status: "active" } : u
      )
    );

    setStats((prev) => ({
      ...prev,
      active: prev.active + 1,
      pending: prev.pending - 1,
    }));
  } catch (err) {
    console.error("Failed to activate user", err);
  }
};

// --- Invite user ---
const handleInvite = async (e: React.FormEvent) => {
  e.preventDefault();
  try {
    const res = await axios.post("http://localhost:8000/api/create-user", inviteData);
    alert(`Invite sent! Token: ${res.data.token}`);

    // Optimistically add to UI
    setUsers((prev) => [
      ...prev,
      {
        username: inviteData.email.split("@")[0],
        email: inviteData.email,
        role: inviteData.role as "admin" | "user",
        employee_id: inviteData.employee_id,
        status: "pending",
      },
    ]);

    setStats((prev) => ({
      ...prev,
      total: prev.total + 1,
      pending: prev.pending + 1,
      admins: inviteData.role === "admin" ? prev.admins + 1 : prev.admins,
    }));

    setInviteData({ email: "", role: "user", employee_id: "" });
  } catch (err) {
    console.error("Failed to invite user", err);
  }
};

  const totalPages = Math.ceil(stats.total / pageSize);

  // --- Stats ---
  const statsData = [
    { label: "Total Users", value: stats.total },
    { label: "Active Users", value: stats.active },
    { label: "Pending Users", value: stats.pending },
    { label: "Admins", value: stats.admins },
  ];

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">🔧 Admin Panel</h1>
        <p className="text-gray-600 dark:text-gray-400">Manage users, roles, and permissions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statsData.map((s, i) => (
          <div key={i} className="bg-white dark:bg-boxdark rounded-lg p-4 shadow-sm">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="flex justify-between items-center">
        <input
          type="text"
          placeholder="Search users..."
          className="w-full md:w-1/3 px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* User List */}
      <div>
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">👥 User Management</h2>
        <div className="space-y-4">
          {users.map((user) => (
            <div key={user.employee_id} className="bg-white dark:bg-boxdark p-4 rounded-lg shadow-sm">
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white">{user.username}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                  <span
                    className={`inline-block mt-2 px-2 py-1 rounded text-xs ${
                      user.status === "active"
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {user.status}
                  </span>
                </div>
                <div className="space-x-2">
                  <button
                    className="px-3 py-1 text-sm rounded bg-blue-500 text-white hover:bg-blue-600"
                    onClick={() => setEditingUser(user)}
                  >
                    Edit
                  </button>
                  <button
                    className="px-3 py-1 text-sm rounded bg-red-500 text-white hover:bg-red-600"
                    onClick={() => handleDelete(user)}
                  >
                    Delete
                  </button>
                  {user.status === "pending" && (
                    <button
                      className="px-3 py-1 text-sm rounded bg-green-500 text-white hover:bg-green-600"
                      onClick={() => handleActivate(user)}
                    >
                      Activate
                    </button>
                  )}
                </div>
              </div>

              {/* Edit Form */}
              {editingUser?.employee_id === user.employee_id && (
                <div className="mt-4 border-t pt-4">
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Edit User</h4>
                  <input
                    type="text"
                    placeholder="Employee ID"
                    disabled
                    className="w-full mb-2 px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
                    value={editingUser.employee_id}
                  />
                  <input
                    type="email"
                    placeholder="Email"
                    className="w-full mb-2 px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
                    value={editingUser.email}
                    onChange={(e) => setEditingUser({ ...editingUser, email: e.target.value })}
                  />
                  <select
                    className="w-full mb-2 px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
                    value={editingUser.role}
                    onChange={(e) =>
                      setEditingUser({ ...editingUser, role: e.target.value as "admin" | "user" })
                    }
                  >
                    <option value="admin">Admin</option>
                    <option value="user">User</option>
                  </select>
                  <div className="flex space-x-2">
                    <button
                      className="px-4 py-2 rounded bg-green-500 text-white"
                      onClick={() => handleUpdate(user)}
                    >
                      Save
                    </button>
                    <button
                      className="px-4 py-2 rounded bg-gray-300 dark:bg-meta-4"
                      onClick={() => setEditingUser(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center pt-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, stats.total)} of {stats.total}
        </p>
        <div className="space-x-2">
          <button
            disabled={page === 1}
            className="px-3 py-1 rounded bg-gray-200 dark:bg-meta-4 disabled:opacity-50"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Prev
          </button>
          <button
            disabled={page === totalPages}
            className="px-3 py-1 rounded bg-gray-200 dark:bg-meta-4 disabled:opacity-50"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      </div>

      {/* Invite Form */}
      <div>
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">➕ Invite User</h2>
        <form
          onSubmit={handleInvite}
          className="bg-white dark:bg-boxdark p-4 rounded-lg shadow-sm space-y-3"
        >
          <input
            type="email"
            placeholder="Email"
            className="w-full px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
            value={inviteData.email}
            onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
            required
          />
          <select
            className="w-full px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
            value={inviteData.role}
            onChange={(e) => setInviteData({ ...inviteData, role: e.target.value })}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          <input
            type="text"
            placeholder="Employee ID"
            className="w-full px-3 py-2 border rounded bg-gray-50 dark:bg-meta-4"
            value={inviteData.employee_id}
            onChange={(e) => setInviteData({ ...inviteData, employee_id: e.target.value })}
          />
          <button
            type="submit"
            className="w-full px-4 py-2 rounded bg-blue-500 text-white hover:bg-blue-600"
          >
            Send Invite
          </button>
        </form>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { Users, Shield, CheckCircle, XCircle, Loader, Search } from 'lucide-react';

interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
  created_at: string;
}

const AVAILABLE_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Full access to all features', color: 'text-red-600' },
  { value: 'reviewer', label: 'Reviewer', description: 'Can review public documents', color: 'text-blue-600' },
  { value: 'teacher', label: 'Teacher', description: 'Can review public and private documents', color: 'text-green-600' },
];

export const UserRoleManagement: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await axios.get('/api/users', {
        headers: { Authorization: `Bearer ${accessToken}` },
        params: { per_page: 100 }
      });

      setUsers(response.data.users);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleEditRoles = (user: User) => {
    setEditingUserId(user.id);
    setSelectedRoles([...user.roles]);
    setError(null);
    setSuccess(null);
  };

  const handleCancelEdit = () => {
    setEditingUserId(null);
    setSelectedRoles([]);
  };

  const toggleRole = (role: string) => {
    if (selectedRoles.includes(role)) {
      setSelectedRoles(selectedRoles.filter(r => r !== role));
    } else {
      setSelectedRoles([...selectedRoles, role]);
    }
  };

  const handleSaveRoles = async (userId: string) => {
    if (selectedRoles.length === 0) {
      setError('User must have at least one role');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      await axios.post(
        `/api/users/${userId}/roles`,
        { roles: selectedRoles },
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );

      setSuccess('Roles updated successfully');
      setEditingUserId(null);
      await fetchUsers();

      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update roles');
    } finally {
      setSaving(false);
    }
  };

  const filteredUsers = users.filter(user =>
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader size={40} className="animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Users className="w-6 h-6 text-purple-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">User Role Management</h1>
        </div>
        <p className="text-gray-600">Manage user roles and permissions</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-800">
          <XCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-800">
          <CheckCircle size={20} />
          <span>{success}</span>
        </div>
      )}

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search users by email or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Role Legend */}
      <div className="mb-6 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <Shield size={18} />
          Available Roles
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {AVAILABLE_ROLES.map(role => (
            <div key={role.value} className="bg-white rounded-lg p-3 border border-gray-200">
              <div className={`font-semibold ${role.color}`}>{role.label}</div>
              <div className="text-sm text-gray-600">{role.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gradient-to-r from-purple-50 to-blue-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Roles
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    No users found
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{user.name || 'N/A'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-gray-600">{user.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      {editingUserId === user.id ? (
                        <div className="space-y-2">
                          {AVAILABLE_ROLES.map(role => (
                            <label key={role.value} className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={selectedRoles.includes(role.value)}
                                onChange={() => toggleRole(role.value)}
                                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                              />
                              <span className={`text-sm font-medium ${role.color}`}>
                                {role.label}
                              </span>
                            </label>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {user.roles.length === 0 ? (
                            <span className="text-gray-400 text-sm">No roles</span>
                          ) : (
                            user.roles.map((role) => {
                              const roleInfo = AVAILABLE_ROLES.find(r => r.value === role);
                              return (
                                <span
                                  key={role}
                                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                                    role === 'admin'
                                      ? 'bg-red-100 text-red-700 border border-red-300'
                                      : role === 'reviewer'
                                      ? 'bg-blue-100 text-blue-700 border border-blue-300'
                                      : 'bg-green-100 text-green-700 border border-green-300'
                                  }`}
                                >
                                  {roleInfo?.label || role}
                                </span>
                              );
                            })
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {editingUserId === user.id ? (
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={handleCancelEdit}
                            disabled={saving}
                            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleSaveRoles(user.id)}
                            disabled={saving || selectedRoles.length === 0}
                            className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                          >
                            {saving ? (
                              <>
                                <Loader size={14} className="animate-spin" />
                                Saving...
                              </>
                            ) : (
                              'Save'
                            )}
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleEditRoles(user)}
                          className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                        >
                          Edit Roles
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stats */}
      <div className="mt-6 flex items-center justify-between text-sm text-gray-600">
        <span>Total users: {filteredUsers.length}</span>
        {searchTerm && (
          <span>Showing {filteredUsers.length} of {users.length} users</span>
        )}
      </div>
    </div>
  );
};

export default UserRoleManagement;

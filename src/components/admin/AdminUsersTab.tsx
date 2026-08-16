import React from 'react';

interface UserItem {
  id: number;
  name: string;
  email: string;
  role: string;
  is_admin: boolean;
}

interface AdminUsersTabProps {
  users: UserItem[];
}

export const AdminUsersTab: React.FC<AdminUsersTabProps> = ({ users }) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Matriz de Usuarios y Asignación de Perfiles RBAC</h3>
      </div>

      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-dark-base border-b border-dark-border text-gray-400 uppercase">
            <tr>
              <th className="px-4 py-3">Usuario</th>
              <th className="px-4 py-3">Correo</th>
              <th className="px-4 py-3">Rol RBAC Asignado</th>
              <th className="px-4 py-3">Es Admin</th>
              <th className="px-4 py-3">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border text-gray-200">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-dark-card/50">
                <td className="px-4 py-3 font-medium">{u.name}</td>
                <td className="px-4 py-3 text-gray-400">{u.email}</td>
                <td className="px-4 py-3">
                  <span className="bg-brand-500/10 text-brand-400 border border-brand-500/20 px-2 py-0.5 rounded">
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">{u.is_admin ? 'Sí' : 'No'}</td>
                <td className="px-4 py-3">
                  <button className="text-purple-400 hover:text-purple-300 font-medium">Editar Perfil</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

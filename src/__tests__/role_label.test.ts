import { describe, it, expect } from 'vitest';
import { resolveRoleLabel, getRoleBadgeStyle, CORPORATE_ROLES } from '../constants';

describe('resolveRoleLabel: el rol que se muestra sale del catalogo o se declara ausente', () => {
  it('con rol lo devuelve tal cual, sin reescribirlo', () => {
    expect(resolveRoleLabel({ role_name: 'Analista de Datos & BI', is_admin: false })).toBe('Analista de Datos & BI');
    expect(resolveRoleLabel({ role_name: 'Administrador de Plataforma', is_admin: true })).toBe('Administrador de Plataforma');
  });

  it('admin sin rol es el rol de plataforma: is_admin son privilegios reales', () => {
    // El nombre es el del catalogo, no "Super Administrador" ni "Administrador":
    // esos dos no existen en CORPORATE_ROLES y el usuario leeria un rol que
    // nadie le asigno.
    expect(resolveRoleLabel({ role_name: null, is_admin: true })).toBe('Administrador de Plataforma');
  });

  it('sin rol y sin admin dice que no hay rol, en vez de inventar "Usuario"', () => {
    expect(resolveRoleLabel({ role_name: null, is_admin: false })).toBe('Sin rol asignado');
    expect(resolveRoleLabel({ role_name: undefined, is_admin: false })).toBe('Sin rol asignado');
  });

  it('el rol mandatorio manda sobre is_admin', () => {
    expect(resolveRoleLabel({ role_name: 'Oficial de Cumplimiento & Seguridad', is_admin: true })).toBe(
      'Oficial de Cumplimiento & Seguridad'
    );
  });

  it('aguanta ausencia de user (sesion sin cargar) sin inventar nada', () => {
    expect(resolveRoleLabel(undefined)).toBe('Sin rol asignado');
    expect(resolveRoleLabel(null)).toBe('Sin rol asignado');
  });

  it('sin rol nunca devuelve un nombre inventado', () => {
    // Falla si alguien reintroduce un literal en el camino "no hay rol": lo que
    // sale tiene que ser un rol del catalogo o el estado explicito. Un
    // role_name que el servidor si manda se devuelve verbatim, sin validarlo
    // aqui (si el backend se equivoca al escribir el rol, que lo diga el).
    const catalogNames = CORPORATE_ROLES.map((r) => r.name);
    for (const role of [null, undefined, '']) {
      for (const is_admin of [true, false]) {
        const label = resolveRoleLabel({ role_name: role, is_admin });
        expect(catalogNames.includes(label) || label === 'Sin rol asignado').toBe(true);
      }
    }
  });
});

describe('getRoleBadgeStyle: "Sin rol asignado" se ve como advertencia', () => {
  it('el estado sin rol no cae en el gris de rol desconocido', () => {
    expect(getRoleBadgeStyle('Sin rol asignado')).not.toBe(getRoleBadgeStyle('Rol Inventado'));
    expect(getRoleBadgeStyle('Sin rol asignado')).toContain('amber');
  });

  it('cada rol del catalogo conserva su color', () => {
    for (const r of CORPORATE_ROLES) {
      expect(getRoleBadgeStyle(r.name)).toBe(r.badgeColor);
    }
  });
});
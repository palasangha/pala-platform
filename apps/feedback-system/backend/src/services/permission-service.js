/**
 * Centralized Permission Service
 * Handles all role-based access control logic
 */

class PermissionService {
  /**
   * Check if user can view feedback from a specific department
   */
  static canViewFeedback(user, feedbackDepartment) {
    if (!user || !user.role) {
      return false;
    }

    // Super admin can view everything
    if (user.role === 'super_admin') {
      return true;
    }

    // Department admin can only view their department
    if (user.role === 'dept_admin' || user.role === 'department_admin') {
      return user.department_code === feedbackDepartment;
    }

    return false;
  }

  /**
   * Get MongoDB query filter based on user role
   * Returns query object to filter feedback/reports by department
   */
  static getFeedbackQuery(user) {
    if (!user || !user.role) {
      throw new Error('Unauthorized: No user or role');
    }

    // Super admin sees everything - no filter
    if (user.role === 'super_admin') {
      return {};
    }

    // Department admin sees only their department
    if (user.role === 'dept_admin' || user.role === 'department_admin') {
      if (!user.department_code) {
        throw new Error('Department admin missing department_code');
      }
      return { department_code: user.department_code };
    }

    throw new Error('Unauthorized: Invalid role');
  }

  /**
   * Check if user can generate reports for a department
   */
  static canGenerateReport(user, departmentCode) {
    if (!user || !user.role) {
      return false;
    }

    // Super admin can generate for any department
    if (user.role === 'super_admin') {
      return true;
    }

    // Department admin can only generate for their department
    if (user.role === 'dept_admin' || user.role === 'department_admin') {
      return user.department_code === departmentCode;
    }

    return false;
  }

  /**
   * Get list of departments user can access
   */
  static getAccessibleDepartments(user, allDepartments) {
    if (!user || !user.role) {
      return [];
    }

    // Super admin can access all departments
    if (user.role === 'super_admin') {
      return allDepartments;
    }

    // Department admin can only access their department
    if (user.role === 'dept_admin' || user.role === 'department_admin') {
      return allDepartments.filter(
        dept => dept.code === user.department_code
      );
    }

    return [];
  }

  /**
   * Check if user can perform admin actions
   */
  static isAdmin(user) {
    if (!user || !user.role) {
      return false;
    }
    return ['super_admin', 'dept_admin', 'department_admin'].includes(user.role);
  }

  /**
   * Check if user is super admin
   */
  static isSuperAdmin(user) {
    return user && user.role === 'super_admin';
  }

  /**
   * Validate user has access to perform action on resource
   */
  static validateAccess(user, resource, action = 'read') {
    if (!this.isAdmin(user)) {
      throw new Error('Unauthorized: Admin access required');
    }

    if (resource.department_code && !this.canViewFeedback(user, resource.department_code)) {
      throw new Error('Forbidden: Access denied to this department');
    }

    return true;
  }
}

module.exports = PermissionService;

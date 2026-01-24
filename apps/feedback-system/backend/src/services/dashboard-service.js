const { Feedback } = require('../models');

/**
 * Optimized Dashboard Service
 * Uses MongoDB aggregation pipelines for performance
 */

class DashboardService {
  /**
   * Get dashboard data with optimized aggregation
   * @param {Object} user - Authenticated user
   * @param {Object} filters - Optional filters (date range, department)
   */
  static async getDashboardData(user, filters = {}) {
    const baseQuery = this._buildBaseQuery(user, filters);

    // Run aggregations in parallel for better performance
    const [feedbackList, summary, departmentStats] = await Promise.all([
      this._getFeedbackList(baseQuery, filters),
      this._getSummaryStats(baseQuery),
      this._getDepartmentStats(baseQuery, user)
    ]);

    return {
      feedbacks: feedbackList.feedbacks,
      pagination: feedbackList.pagination,
      summary,
      departmentStats,
      filters: {
        startDate: filters.startDate,
        endDate: filters.endDate,
        department: filters.department
      }
    };
  }

  /**
   * Build base query based on user role and filters
   */
  static _buildBaseQuery(user, filters) {
    const query = {};

    // Role-based filtering
    if (user.role === 'dept_admin' || user.role === 'department_admin') {
      query.department_code = user.department_code;
    } else if (filters.department) {
      query.department_code = filters.department;
    }

    // Date range filtering
    if (filters.startDate || filters.endDate) {
      query.created_at = {};
      if (filters.startDate) {
        query.created_at.$gte = new Date(filters.startDate);
      }
      if (filters.endDate) {
        query.created_at.$lte = new Date(filters.endDate);
      }
    }

    return query;
  }

  /**
   * Get paginated feedback list
   */
  static async _getFeedbackList(baseQuery, filters) {
    const page = parseInt(filters.page) || 1;
    const limit = parseInt(filters.limit) || 50;
    const skip = (page - 1) * limit;

    const [feedbacks, total] = await Promise.all([
      Feedback.find(baseQuery)
        .select('department_code user_name user_email is_anonymous ratings comment created_at')
        .sort({ created_at: -1 })
        .skip(skip)
        .limit(limit)
        .lean(),
      Feedback.countDocuments(baseQuery)
    ]);

    return {
      feedbacks,
      pagination: {
        total,
        page,
        limit,
        pages: Math.ceil(total / limit)
      }
    };
  }

  /**
   * Get summary statistics using aggregation
   */
  static async _getSummaryStats(baseQuery) {
    const stats = await Feedback.aggregate([
      { $match: baseQuery },
      {
        $facet: {
          overall: [
            {
              $group: {
                _id: null,
                total_feedback: { $sum: 1 },
                anonymous_count: {
                  $sum: { $cond: ['$is_anonymous', 1, 0] }
                },
                with_comments: {
                  $sum: {
                    $cond: [
                      { $and: [{ $ne: ['$comment', null] }, { $ne: ['$comment', ''] }] },
                      1,
                      0
                    ]
                  }
                },
                avg_rating: {
                  $avg: {
                    $avg: { $objectToArray: '$ratings' }
                  }
                }
              }
            }
          ],
          ratingDistribution: [
            {
              $project: {
                ratings_array: { $objectToArray: '$ratings' }
              }
            },
            { $unwind: '$ratings_array' },
            {
              $group: {
                _id: '$ratings_array.k',
                avg: { $avg: '$ratings_array.v' },
                count: { $sum: 1 }
              }
            },
            { $sort: { _id: 1 } }
          ]
        }
      }
    ]);

    const overall = stats[0]?.overall[0] || {
      total_feedback: 0,
      anonymous_count: 0,
      with_comments: 0,
      avg_rating: 0
    };

    const ratingDistribution = stats[0]?.ratingDistribution || [];

    return {
      ...overall,
      rating_distribution: ratingDistribution
    };
  }

  /**
   * Get department-wise statistics
   */
  static async _getDepartmentStats(baseQuery, user) {
    // Only super admin gets department breakdown
    if (user.role !== 'super_admin') {
      return [];
    }

    const deptStats = await Feedback.aggregate([
      { $match: baseQuery },
      {
        $group: {
          _id: '$department_code',
          total: { $sum: 1 },
          anonymous: {
            $sum: { $cond: ['$is_anonymous', 1, 0] }
          },
          avg_rating: {
            $avg: {
              $avg: { $map: {
                input: { $objectToArray: '$ratings' },
                in: '$$this.v'
              }}
            }
          },
          with_comments: {
            $sum: {
              $cond: [
                { $and: [{ $ne: ['$comment', null] }, { $ne: ['$comment', ''] }] },
                1,
                0
              ]
            }
          }
        }
      },
      {
        $lookup: {
          from: 'departments',
          localField: '_id',
          foreignField: 'code',
          as: 'dept_info'
        }
      },
      {
        $project: {
          department_code: '$_id',
          department_name: { $arrayElemAt: ['$dept_info.name', 0] },
          total_feedback: '$total',
          anonymous_count: '$anonymous',
          avg_rating: { $round: ['$avg_rating', 2] },
          with_comments: '$with_comments'
        }
      },
      { $sort: { total_feedback: -1 } }
    ]);

    return deptStats;
  }

  /**
   * Get feedback trends over time
   */
  static async getFeedbackTrends(user, period = 'week') {
    const baseQuery = this._buildBaseQuery(user, {});
    
    // Calculate date grouping based on period
    const groupBy = period === 'week' 
      ? { $dayOfWeek: '$created_at' }
      : period === 'month'
      ? { $dayOfMonth: '$created_at' }
      : { $month: '$created_at' };

    const trends = await Feedback.aggregate([
      { $match: baseQuery },
      {
        $group: {
          _id: groupBy,
          count: { $sum: 1 },
          avg_rating: {
            $avg: {
              $avg: { $map: {
                input: { $objectToArray: '$ratings' },
                in: '$$this.v'
              }}
            }
          }
        }
      },
      { $sort: { _id: 1 } }
    ]);

    return trends;
  }
}

module.exports = DashboardService;

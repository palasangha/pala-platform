// @ts-check
const { test, expect } = require('@playwright/test');

const API_BASE_URL = 'http://localhost:3001/api';

test.describe('Dhammalaya API Acceptance Tests', () => {
  
  test('GET /api/departments should return Dhammalaya', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/departments`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data.departments).toBeDefined();
    
    // Find Dhammalaya department
    const dhammalaya = data.data.departments.find(d => d.code === 'dhamma_lane');
    expect(dhammalaya).toBeDefined();
    expect(dhammalaya.name).toBe('Dhammalaya');
    expect(dhammalaya.description).toBe('Meditation walkway and peaceful environment');
    
    console.log('✓ Dhammalaya department found in API:', dhammalaya.name);
  });

  test('GET /api/departments/:code should return Dhammalaya details', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/departments/dhamma_lane`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data.department).toBeDefined();
    
    const dept = data.data.department;
    expect(dept.code).toBe('dhamma_lane');
    expect(dept.name).toBe('Dhammalaya');
    expect(dept.tablet_config).toBeDefined();
    expect(dept.tablet_config.welcome_message).toBe('Welcome to Dhammalaya!');
    expect(dept.tablet_config.primary_color).toBe('#27ae60');
    
    console.log('✓ Dhammalaya department details:', {
      name: dept.name,
      welcome: dept.tablet_config.welcome_message,
      color: dept.tablet_config.primary_color
    });
  });

  test('Dhammalaya department should have 5 questions', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/departments/dhamma_lane`);
    const data = await response.json();
    
    const dept = data.data.department;
    expect(dept.questions).toBeDefined();
    expect(dept.questions.length).toBe(5);
    
    console.log('✓ Dhammalaya has', dept.questions.length, 'questions');
  });

  test('POST /api/feedback should accept Dhammalaya feedback', async ({ request }) => {
    const feedbackData = {
      department_code: 'dhamma_lane',
      ratings: {
        'How would you rate the cleanliness?': 5,
        'How would you rate the ambiance?': 5,
        'How was your overall experience?': 4,
        'Would you recommend this to others?': 5,
        'How satisfied are you with the service?': 4
      },
      comments: 'Wonderful meditation environment at Dhammalaya! Very peaceful and well-maintained.',
      name: 'Test User',
      email: 'test@example.com'
    };

    const response = await request.post(`${API_BASE_URL}/feedback`, {
      data: feedbackData,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data.feedback).toBeDefined();
    expect(data.data.feedback.department_code).toBe('dhamma_lane');
    
    console.log('✓ Feedback submitted successfully for Dhammalaya');
    console.log('  Feedback ID:', data.data.feedback._id);
  });

  test('GET /api/feedback should return Dhammalaya feedback', async ({ request }) => {
    // First submit feedback
    const feedbackData = {
      department_code: 'dhamma_lane',
      ratings: {
        'cleanliness': 5,
        'ambiance': 5,
        'experience': 5
      },
      comments: 'Great experience at Dhammalaya!',
      name: 'API Test User'
    };

    await request.post(`${API_BASE_URL}/feedback`, {
      data: feedbackData,
      headers: { 'Content-Type': 'application/json' }
    });

    // Then retrieve feedback with filter
    const response = await request.get(`${API_BASE_URL}/feedback?department_code=dhamma_lane&limit=5`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data.feedbacks).toBeDefined();
    
    // Should have at least one feedback for Dhammalaya
    const dhammalayaFeedback = data.data.feedbacks.filter(f => f.department_code === 'dhamma_lane');
    expect(dhammalayaFeedback.length).toBeGreaterThan(0);
    
    console.log('✓ Found', dhammalayaFeedback.length, 'feedback(s) for Dhammalaya');
  });

  test('Admin user for Dhammalaya exists with correct name', async ({ request }) => {
    // Login with Dhammalaya admin credentials
    const loginData = {
      email: 'dhammalane@globalpagoda.org',
      password: 'DhammaLane@2026!'
    };

    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: loginData,
      headers: { 'Content-Type': 'application/json' }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.data.user).toBeDefined();
    expect(data.data.user.full_name).toBe('Dhammalaya Administrator');
    expect(data.data.user.department_code).toBe('dhamma_lane');
    expect(data.data.user.role).toBe('dept_admin');
    
    console.log('✓ Dhammalaya admin login successful');
    console.log('  Admin name:', data.data.user.full_name);
    console.log('  Department:', data.data.user.department_code);
  });
});

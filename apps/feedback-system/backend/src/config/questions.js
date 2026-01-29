const { QUESTION_TYPES } = require('./constants');

// Questions configuration by department
const QUESTIONS_BY_DEPARTMENT = {
  global_pagoda: [
    {
      id: 'cleanliness',
      text: 'How would you rate the cleanliness of the premises?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'meditation_hall',
      text: 'Rate your experience in the meditation hall',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'staff_behavior',
      text: 'How helpful and courteous was our staff?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'facilities',
      text: 'Rate the overall facilities (washrooms, drinking water, seating)',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'spiritual_atmosphere',
      text: 'On a scale of 1-10, how peaceful was the spiritual atmosphere?',
      type: QUESTION_TYPES.NUMERIC,
      required: true
    },
    {
      id: 'guidance',
      text: 'Were you satisfied with the guidance/instructions provided?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'overall_experience',
      text: 'Overall, how likely are you to recommend this place? (NPS)',
      type: QUESTION_TYPES.NUMERIC,
      required: true
    }
  ],

  souvenir_store: [
    {
      id: 'product_variety',
      text: 'How satisfied are you with the variety of products?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'product_quality',
      text: 'Rate the quality of items purchased',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'staff_assistance',
      text: 'How helpful was the staff in assisting you?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'pricing',
      text: 'Do you find the pricing fair and reasonable?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'store_ambiance',
      text: 'Rate the store ambiance and layout',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'checkout_speed',
      text: 'Was the checkout process quick and smooth?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    }
  ],

  dpvc: [
    {
      id: 'course_quality',
      text: 'Rate the overall quality of the Vipassana course',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'teacher_guidance',
      text: 'How satisfied were you with teacher guidance?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'accommodation',
      text: 'Rate your accommodation (room, bedding, cleanliness)',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'food_quality',
      text: 'How was the food quality and variety?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'meditation_hall_dpvc',
      text: 'Rate the meditation hall facilities',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'noble_silence',
      text: 'Was the environment conducive to maintaining noble silence?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'would_recommend',
      text: 'How likely are you to recommend this course? (0-10)',
      type: QUESTION_TYPES.NUMERIC,
      required: true
    }
  ],

  dhammalaya: [
    {
      id: 'facility_cleanliness',
      text: 'Rate the cleanliness of Dhammalaya facilities',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'meditation_area',
      text: 'How peaceful was the meditation area?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'accessibility',
      text: 'Was it easy to navigate and access the facilities?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'ambiance',
      text: 'Rate the overall spiritual ambiance',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'signage',
      text: 'Were directions and signage clear and helpful?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'overall_experience',
      text: 'Overall experience rating',
      type: QUESTION_TYPES.STAR,
      required: true
    }
  ],

  food_court: [
    {
      id: 'food_quality',
      text: 'How would you rate the food quality?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'food_variety',
      text: 'Rate the variety of food options',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'hygiene',
      text: 'Rate the hygiene and cleanliness',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'service_speed',
      text: 'Was the service quick and efficient?',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'staff_behavior',
      text: 'How courteous and helpful was the staff?',
      type: QUESTION_TYPES.STAR,
      required: true
    },
    {
      id: 'value_for_money',
      text: 'Rate value for money',
      type: QUESTION_TYPES.EMOJI,
      required: true
    },
    {
      id: 'seating_comfort',
      text: 'Rate the seating and dining comfort',
      type: QUESTION_TYPES.STAR,
      required: true
    }
  ]
};

// Get questions for a specific department
const getQuestionsByDepartment = (departmentCode) => {
  return QUESTIONS_BY_DEPARTMENT[departmentCode] || [];
};

// Validate ratings based on question type
const validateRating = (questionType, rating) => {
  switch (questionType) {
    case QUESTION_TYPES.STAR:
    case 'star':
      return rating >= 1 && rating <= 5;
    case QUESTION_TYPES.EMOJI:
    case 'emoji':
    case 'smiley_5':
      return rating >= 1 && rating <= 5;
    case QUESTION_TYPES.NUMERIC:
    case 'numeric':
    case 'rating_10':
      return rating >= 1 && rating <= 5;  // Changed from 0-10 to 1-5
    case 'binary_yes_no':
      return rating === 0 || rating === 1;
    default:
      return false;
  }
};

module.exports = {
  QUESTIONS_BY_DEPARTMENT,
  getQuestionsByDepartment,
  validateRating
};

const { createCanvas } = require('canvas');
const { Chart } = require('chart.js/auto');

class ChartService {
  // Generate rating distribution bar chart
  async generateRatingDistributionChart(questionData, width = 600, height = 400) {
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    const labels = Object.keys(questionData.distribution);
    const data = Object.values(questionData.distribution);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Number of Responses',
          data,
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: false,
        plugins: {
          title: {
            display: true,
            text: questionData.text,
            font: { size: 16 }
          },
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1 }
          }
        }
      }
    });

    return canvas.toBuffer('image/png');
  }

  // Generate trend line chart
  async generateTrendChart(trendData, width = 600, height = 400) {
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: trendData.labels,
        datasets: [{
          label: 'Average Rating',
          data: trendData.values,
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.2)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: false,
        plugins: {
          title: {
            display: true,
            text: 'Rating Trend Over Time',
            font: { size: 16 }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 10
          }
        }
      }
    });

    return canvas.toBuffer('image/png');
  }

  // Generate pie chart for response distribution
  async generatePieChart(data, title, width = 400, height = 400) {
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          backgroundColor: [
            'rgba(255, 99, 132, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(153, 102, 255, 0.6)'
          ],
          borderColor: [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)'
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: false,
        plugins: {
          title: {
            display: true,
            text: title,
            font: { size: 16 }
          },
          legend: {
            position: 'bottom'
          }
        }
      }
    });

    return canvas.toBuffer('image/png');
  }
}

module.exports = new ChartService();
